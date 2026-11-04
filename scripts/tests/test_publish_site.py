#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pytest==9.0.2"]
# ///
# How to run: uv run --with pytest python -m pytest scripts/tests -q
"""Verify publication authority through the actual publisher and AWS CLI."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from pathlib import Path
from threading import Thread

import pytest
from s3_fixture import Bucket


@pytest.fixture
def bucket(tmp_path: Path) -> Iterator[Bucket]:
    source = tmp_path / "out"
    source.mkdir()
    (source / "index.html").write_text("<title>release</title>", encoding="utf-8")
    (source / "404.html").write_text("<title>missing</title>", encoding="utf-8")
    (source / "asset with spaces.css").write_text("body{color:navy}", encoding="utf-8")
    state = Bucket(source)
    with state.server() as server:
        state.endpoint = f"http://127.0.0.1:{server.server_port}"
        worker = Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            yield state
        finally:
            server.shutdown()
            worker.join(timeout=5)


def test_pointer_names_the_complete_independently_verified_release(
    bucket: Bucket,
) -> None:
    expected_manifest = "".join(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n"
        for path in sorted(bucket.source.iterdir())
    ).encode()
    expected_release = hashlib.sha256(expected_manifest).hexdigest()

    result = bucket.publish()

    assert result.returncode == 0, result.stderr
    assert bucket.objects["airbroke/current"] == (expected_release + "\n").encode()
    prefix = f"airbroke/releases/{expected_release}/"
    expected = {
        prefix + path.name: path.read_bytes() for path in bucket.source.iterdir()
    }
    expected[prefix + "manifest.sha256"] = expected_manifest
    expected.update(
        {
            "airbroke/live/" + path.name: path.read_bytes()
            for path in bucket.source.iterdir()
        }
    )
    expected["airbroke/live/manifest.sha256"] = expected_manifest
    assert {
        key: body for key, body in bucket.objects.items() if key != "airbroke/current"
    } == expected


def test_corrupt_download_never_replaces_the_active_pointer(bucket: Bucket) -> None:
    bucket.corrupt_download = True

    result = bucket.publish()

    assert result.returncode != 0
    assert "remote release differs" in result.stderr
    assert bucket.objects["airbroke/current"] == b"prior-release\n"


def test_failed_upload_never_replaces_the_active_pointer(bucket: Bucket) -> None:
    bucket.reject_upload = True

    result = bucket.publish()

    assert result.returncode != 0
    assert bucket.objects == {"airbroke/current": b"prior-release\n"}


@pytest.mark.parametrize("unsafe", ["symlink", "control", "manifest", "missing-page"])
def test_invalid_export_is_rejected_before_remote_mutation(
    bucket: Bucket, unsafe: str
) -> None:
    match unsafe:
        case "symlink":
            (bucket.source / "escape").symlink_to(bucket.source / "index.html")
        case "control":
            (bucket.source / "bad\nname").write_text("bad", encoding="utf-8")
        case "manifest":
            (bucket.source / "manifest.sha256").write_text("bad", encoding="utf-8")
        case "missing-page":
            (bucket.source / "404.html").unlink()
        case unexpected:
            raise AssertionError(unexpected)

    result = bucket.publish()

    assert result.returncode != 0
    assert bucket.objects == {"airbroke/current": b"prior-release\n"}


@pytest.mark.parametrize("failure", ["index-upload", "asset-readback"])
def test_live_failure_keeps_the_previous_html_entrypoint(
    bucket: Bucket, failure: str
) -> None:
    bucket.objects["airbroke/live/index.html"] = b"old html"
    bucket.reject_live_index = failure == "index-upload"
    bucket.corrupt_live_asset = failure == "asset-readback"

    result = bucket.publish()

    assert result.returncode != 0
    assert bucket.objects["airbroke/live/index.html"] == b"old html"
    assert bucket.objects["airbroke/current"] == b"prior-release\n"


def test_live_publication_retains_old_hashed_assets_for_cached_html(
    bucket: Bucket,
) -> None:
    old_key = "airbroke/live/_next/static/old-hash.js"
    bucket.objects[old_key] = b"old cached html still needs this"
    asset = bucket.source / "_next/static/new-hash.js"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"new immutable content")

    result = bucket.publish()

    assert result.returncode == 0, result.stderr
    assert bucket.objects[old_key] == b"old cached html still needs this"
    assert (
        bucket.objects["airbroke/live/index.html"]
        == (bucket.source / "index.html").read_bytes()
    )
    assert (
        bucket.objects["airbroke/live/_next/static/new-hash.js"] == asset.read_bytes()
    )
    assert (
        bucket.cache_controls["airbroke/live/_next/static/new-hash.js"]
        == "public,max-age=31536000,immutable"
    )
    assert bucket.cache_controls["airbroke/live/index.html"] == "no-cache"
    assert bucket.cache_controls["airbroke/live/404.html"] == "no-cache"
