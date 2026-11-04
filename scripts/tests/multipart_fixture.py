"""Multipart S3 protocol extension with an ambiguous accepted-part failure."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler
from threading import Lock
from urllib.parse import parse_qs, unquote, urlsplit
from uuid import uuid4

from s3_fixture import Bucket


@dataclass(slots=True)
class Upload:
    """Mutable multipart session retains received parts until complete or abort."""

    key: str
    cache_control: str
    parts: dict[int, bytes] = field(default_factory=dict)


@dataclass(slots=True)
class MultipartBucket(Bucket):
    """Track real requests and optionally lose a successful part acknowledgement."""

    ambiguous_part: bool = False
    uploads: dict[str, Upload] = field(default_factory=dict)
    requests: dict[tuple[str, int], int] = field(default_factory=dict)
    completed_shapes: list[list[int]] = field(default_factory=list)
    aborted: list[str] = field(default_factory=list)
    active: int = 0
    peak: int = 0
    lock: Lock = field(default_factory=Lock)

    def accept_part(self, upload_id: str, number: int, body: bytes) -> int:
        with self.lock:
            request = (upload_id, number)
            self.requests[request] = self.requests.get(request, 0) + 1
            self.active += 1
            self.peak = max(self.peak, self.active)
            repeated = number in self.uploads[upload_id].parts
            self.uploads[upload_id].parts.setdefault(number, body)
        try:
            # Keep requests overlapping long enough to observe actual client bounds.
            time.sleep(0.15)
            if repeated:
                return 400
            return 500 if self.ambiguous_part and number == 1 else 200
        finally:
            with self.lock:
                self.active -= 1

    def handler_type(self) -> type[BaseHTTPRequestHandler]:
        bucket = self
        base_handler = super(MultipartBucket, self).handler_type()

        class Handler(base_handler):
            def do_POST(self) -> None:  # noqa: N802 - standard HTTP handler API
                parsed = urlsplit(self.path)
                query = parse_qs(parsed.query, keep_blank_values=True)
                key = unquote(parsed.path.removeprefix("/sample-bucket/"))
                _ = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                if "uploads" in query:
                    upload_id = str(uuid4())
                    bucket.uploads[upload_id] = Upload(
                        key, self.headers.get("Cache-Control", "")
                    )
                    body = (
                        "<InitiateMultipartUploadResult><Bucket>sample-bucket</Bucket>"
                        f"<Key>{key}</Key><UploadId>{upload_id}</UploadId>"
                        "</InitiateMultipartUploadResult>"
                    ).encode()
                else:
                    upload = bucket.uploads.pop(query["uploadId"][0])
                    parts = [part for _, part in sorted(upload.parts.items())]
                    bucket.objects[key] = b"".join(parts)
                    bucket.cache_controls[key] = upload.cache_control
                    bucket.completed_shapes.append([len(part) for part in parts])
                    body = (
                        "<CompleteMultipartUploadResult><Bucket>sample-bucket</Bucket>"
                        f'<Key>{key}</Key><ETag>"fixture-{len(parts)}"</ETag>'
                        "</CompleteMultipartUploadResult>"
                    ).encode()
                self.respond(200, body, "application/xml")

            def do_PUT(self) -> None:  # noqa: N802 - standard HTTP handler API
                query = parse_qs(urlsplit(self.path).query)
                if "uploadId" not in query:
                    super().do_PUT()
                    return
                body = self.rfile.read(int(self.headers["Content-Length"]))
                code = bucket.accept_part(
                    query["uploadId"][0], int(query["partNumber"][0]), body
                )
                self.send_response(code)
                self.send_header("Content-Length", "0")
                self.send_header(
                    "ETag",
                    '"' + hashlib.md5(body, usedforsecurity=False).hexdigest() + '"',
                )
                self.end_headers()

            def do_DELETE(self) -> None:  # noqa: N802 - standard HTTP handler API
                upload_id = parse_qs(urlsplit(self.path).query)["uploadId"][0]
                bucket.aborted.append(upload_id)
                del bucket.uploads[upload_id]
                self.respond(204, b"", "application/xml")

            def do_GET(self) -> None:  # noqa: N802 - standard HTTP handler API
                requested_range = self.headers.get("Range")
                if not requested_range:
                    super().do_GET()
                    return
                key = unquote(urlsplit(self.path).path.removeprefix("/sample-bucket/"))
                complete = bucket.objects[key]
                first, last = requested_range.removeprefix("bytes=").split("-", 1)
                start = int(first)
                end = min(int(last) if last else len(complete) - 1, len(complete) - 1)
                body = complete[start : end + 1]
                self.send_response(206)
                self.send_header("Content-Length", str(len(body)))
                self.send_header(
                    "Content-Range", f"bytes {start}-{end}/{len(complete)}"
                )
                self.send_header("ETag", '"fixture"')
                self.send_header("Last-Modified", "Thu, 01 Jan 2026 00:00:00 GMT")
                self.end_headers()
                _ = self.wfile.write(body)

        return Handler
