"""An isolated S3 HTTP boundary for exercising the real AWS CLI."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit
from xml.sax.saxutils import escape


@dataclass(slots=True)
class Bucket:
    """Mutable fixture state models stored bytes and transport failures."""

    source: Path
    endpoint: str = ""
    objects: dict[str, bytes] = field(
        default_factory=lambda: {"airbroke/current": b"prior-release\n"}
    )
    corrupt_download: bool = False
    reject_upload: bool = False
    reject_live_index: bool = False
    corrupt_live_asset: bool = False
    cache_controls: dict[str, str] = field(default_factory=dict)

    def publish(self) -> subprocess.CompletedProcess[str]:
        """Run the real publisher and AWS executable against this fixture."""
        environment = os.environ | {
            "AWS_ACCESS_KEY_ID": "fixture-access",
            "AWS_SECRET_ACCESS_KEY": "fixture-secret",
            "AWS_DEFAULT_REGION": "us-east-1",
            "AWS_SHARED_CREDENTIALS_FILE": "/dev/null",
        }
        environment.pop("AWS_PROFILE", None)
        return subprocess.run(
            [
                sys.executable,
                str(Path(__file__).parents[1] / "publish-site.py"),
                str(self.source),
                "sample-bucket",
                self.endpoint,
            ],
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=90,
        )

    def rejects(self, key: str) -> bool:
        """Inject selected write failures at the HTTP storage boundary."""
        return (self.reject_upload and key != "airbroke/current") or (
            self.reject_live_index and key == "airbroke/live/index.html"
        )

    def head(self, key: str) -> tuple[int, int]:
        """Return stored object metadata, including the missing-object status."""
        return (200, len(self.objects[key])) if key in self.objects else (404, 0)

    def handler_type(self) -> type[BaseHTTPRequestHandler]:
        """Bind the HTTP handler to this isolated bucket."""
        bucket = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def respond(self, code: int, body: bytes, content_type: str) -> None:
                self.send_response(code)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Content-Type", content_type)
                self.send_header("ETag", '"fixture"')
                self.send_header("Last-Modified", "Thu, 01 Jan 2026 00:00:00 GMT")
                self.end_headers()
                self.wfile.write(body)

            def do_PUT(self) -> None:
                key = unquote(urlsplit(self.path).path.removeprefix("/sample-bucket/"))
                body = self.rfile.read(int(self.headers["Content-Length"]))
                if bucket.rejects(key):
                    self.respond(
                        403,
                        b"<Error><Code>AccessDenied</Code></Error>",
                        "application/xml",
                    )
                    return
                bucket.objects[key] = body
                bucket.cache_controls[key] = self.headers.get("Cache-Control", "")
                self.send_response(200)
                self.send_header(
                    "ETag",
                    '"' + hashlib.md5(body, usedforsecurity=False).hexdigest() + '"',
                )
                self.send_header("Content-Length", "0")
                self.end_headers()

            def do_HEAD(self) -> None:
                key = unquote(urlsplit(self.path).path.removeprefix("/sample-bucket/"))
                code, size = bucket.head(key)
                self.send_response(code)
                self.send_header("Content-Length", str(size))
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Last-Modified", "Thu, 01 Jan 2026 00:00:00 GMT")
                self.send_header("ETag", '"fixture"')
                self.end_headers()

            def do_GET(self) -> None:
                parsed = urlsplit(self.path)
                if parsed.path.rstrip("/") == "/sample-bucket":
                    prefix = parse_qs(parsed.query).get("prefix", [""])[0]
                    rows = "".join(
                        f"<Contents><Key>{escape(key)}</Key><LastModified>2026-01-01T00:00:00Z</LastModified>"
                        f"<ETag>&quot;fixture&quot;</ETag><Size>{len(body)}</Size><StorageClass>STANDARD</StorageClass></Contents>"
                        for key, body in sorted(bucket.objects.items())
                        if key.startswith(prefix)
                    )
                    self.respond(
                        200,
                        (
                            '<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
                            f"<Name>sample-bucket</Name><Prefix>{escape(prefix)}</Prefix><IsTruncated>false</IsTruncated>"
                            f"{rows}</ListBucketResult>"
                        ).encode(),
                        "application/xml",
                    )
                    return
                key = unquote(parsed.path.removeprefix("/sample-bucket/"))
                if key not in bucket.objects:
                    self.respond(
                        404, b"<Error><Code>NoSuchKey</Code></Error>", "application/xml"
                    )
                    return
                body = bucket.objects[key]
                if (bucket.corrupt_download and key.endswith("index.html")) or (
                    bucket.corrupt_live_asset
                    and key == "airbroke/live/asset with spaces.css"
                ):
                    body = b"x" * len(body)
                self.respond(200, body, "application/octet-stream")

            def log_message(self, message_format: str, *args: str) -> None:
                """Keep fixture HTTP access logs out of assertion output."""

        return Handler

    def server(self) -> ThreadingHTTPServer:
        """Serve S3 operations and deliberate transport faults."""
        return ThreadingHTTPServer(("127.0.0.1", 0), self.handler_type())
