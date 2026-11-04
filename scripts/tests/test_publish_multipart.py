"""Exercise actual AWS multipart retry and concurrency behavior through publication."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from pathlib import Path
from threading import Thread

import pytest
from multipart_fixture import MultipartBucket


@pytest.fixture
def multipart(tmp_path: Path) -> Iterator[MultipartBucket]:
    source = tmp_path / "out"
    source.mkdir()
    (source / "index.html").write_bytes(b"new html")
    (source / "404.html").write_bytes(b"missing")
    with (source / "large.bin").open("wb") as stream:
        for number in range(41):
            stream.write(bytes([number]) * (1024 * 1024))
    bucket = MultipartBucket(source)
    bucket.objects["airbroke/live/index.html"] = b"old html"
    with bucket.server() as server:
        bucket.endpoint = f"http://127.0.0.1:{server.server_port}"
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield bucket
        finally:
            server.shutdown()
            thread.join(timeout=5)


def test_accepted_part_with_lost_ack_is_never_retried(
    multipart: MultipartBucket,
) -> None:
    multipart.ambiguous_part = True

    result = multipart.publish()

    assert result.returncode != 0
    assert multipart.requests, result.stderr
    assert max(multipart.requests.values()) == 1, multipart.requests
    assert len(multipart.aborted) == 1
    assert multipart.uploads == {}
    assert multipart.objects["airbroke/live/index.html"] == b"old html"
    assert multipart.objects["airbroke/current"] == b"prior-release\n"


def test_multipart_roundtrip_preserves_bytes_and_bounds_parts(
    multipart: MultipartBucket,
) -> None:
    with (multipart.source / "large.bin").open("rb") as stream:
        expected = hashlib.file_digest(stream, "sha256").hexdigest()

    result = multipart.publish()

    assert result.returncode == 0, result.stderr
    actual = hashlib.sha256(multipart.objects["airbroke/live/large.bin"]).hexdigest()
    assert actual == expected
    assert multipart.completed_shapes == [[8 * 1024 * 1024] * 5 + [1024 * 1024]] * 2
    assert multipart.peak <= 4, multipart.peak
    assert max(multipart.requests.values()) == 1
    assert multipart.objects["airbroke/live/index.html"] == b"new html"
