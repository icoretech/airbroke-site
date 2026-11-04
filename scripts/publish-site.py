#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# How to run: python3 scripts/publish-site.py out BUCKET ENDPOINT
"""Publish a verified archive, then support files, then the live HTML entrypoint."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Final
from urllib.parse import urlsplit

from live_site import LivePublicationError, publish_live

MAX_FILES: Final = 10_000
MAX_BYTES: Final = 512 * 1024 * 1024
MAX_PATH_BYTES: Final = 1024
ASCII_CONTROL_BOUNDARY: Final = 32
ASCII_DELETE: Final = 127
MANIFEST: Final = "manifest.sha256"
ARGUMENT_COUNT: Final = 4


class PublicationError(RuntimeError):
    """Reject an invalid tree or an unverified remote release."""


@dataclass(frozen=True, slots=True)
class Destination:
    """An explicit bucket and S3 API endpoint, never inferred from credentials."""

    bucket: str
    endpoint: str

    def __post_init__(self) -> None:
        """Reject credentials, ambiguous bucket names and unsafe HTTP destinations."""
        parsed = urlsplit(self.endpoint)
        if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", self.bucket):
            raise PublicationError("invalid destination bucket")
        if parsed.scheme not in {"https", "http"} or not parsed.netloc:
            raise PublicationError("invalid destination endpoint")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise PublicationError(
                "endpoint must not contain credentials or query data"
            )
        if parsed.scheme == "http" and parsed.hostname not in {
            "127.0.0.1",
            "localhost",
        }:
            raise PublicationError(
                "unencrypted endpoints are restricted to local qualification"
            )


def tree_manifest(root: Path) -> bytes:
    """Reject unsafe entries and hash the exact bounded regular-file tree."""
    rows: list[str] = []
    total = 0
    for path in sorted(root.rglob("*")):
        mode = path.lstat().st_mode
        name = path.relative_to(root).as_posix()
        if stat.S_ISLNK(mode) or not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
            raise PublicationError(f"unsupported entry: {name!r}")
        if "\\" in name or any(
            ord(char) < ASCII_CONTROL_BOUNDARY or ord(char) == ASCII_DELETE
            for char in name
        ):
            raise PublicationError(f"unsafe path: {name!r}")
        if len(name.encode("utf-8")) > MAX_PATH_BYTES or name == MANIFEST:
            raise PublicationError(f"reserved or oversized path: {name!r}")
        if stat.S_ISDIR(mode):
            continue
        total += path.stat().st_size
        if total > MAX_BYTES or len(rows) >= MAX_FILES:
            raise PublicationError("release exceeds publication bounds")
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        rows.append(f"{digest}  {name}\n")
    for name in ("index.html", "404.html"):
        if not (root / name).is_file() or (root / name).stat().st_size == 0:
            raise PublicationError(f"required page missing or empty: {name}")
    return "".join(rows).encode("utf-8")


def publish(source: Path, destination: Destination) -> str:
    """Upload and independently retrieve the release before publishing its pointer."""
    if source.is_symlink() or not source.is_dir():
        raise PublicationError("source must be a real directory")
    # Refuse oversized input before snapshotting; CI mounts the export read-only.
    _ = tree_manifest(source)
    with tempfile.TemporaryDirectory(prefix="site-publication-") as temporary:
        root = Path(temporary)
        snapshot = root / "snapshot"
        _ = shutil.copytree(source, snapshot, symlinks=True)
        manifest = tree_manifest(snapshot)
        release = hashlib.sha256(manifest).hexdigest()
        _ = (snapshot / MANIFEST).write_bytes(manifest)
        config = root / "aws-config"
        _ = config.write_text(
            """[default]
s3 =
    addressing_style = path
    signature_version = s3v4
    preferred_transfer_client = classic
    max_concurrent_requests = 4
    multipart_threshold = 8MB
    multipart_chunksize = 8MB
""",
            encoding="utf-8",
        )
        environment = os.environ | {
            "AWS_CONFIG_FILE": str(config),
            "AWS_REQUEST_CHECKSUM_CALCULATION": "when_required",
            "AWS_RESPONSE_CHECKSUM_VALIDATION": "when_required",
            "AWS_DEFAULT_REGION": os.environ.get(
                "AWS_DEFAULT_REGION", "eu-luxembourg-1"
            ),
            "AWS_MAX_ATTEMPTS": "1",
            "AWS_EC2_METADATA_DISABLED": "true",
        }
        command = [
            "aws",
            "--endpoint-url",
            destination.endpoint,
            "--no-cli-pager",
            "--cli-connect-timeout",
            "10",
            "--cli-read-timeout",
            "60",
        ]
        remote = f"s3://{destination.bucket}/airbroke/releases/{release}/"
        for arguments in (
            ["s3", "sync", str(snapshot), remote, "--only-show-errors"],
            ["s3", "sync", remote, str(root / "retrieved"), "--only-show-errors"],
        ):
            _ = subprocess.run(
                [*command, *arguments], env=environment, check=True, timeout=900
            )
        retrieved = root / "retrieved"
        downloaded_manifest = (retrieved / MANIFEST).read_bytes()
        if downloaded_manifest != manifest:
            raise PublicationError(
                "remote manifest differs from the published snapshot"
            )
        (retrieved / MANIFEST).unlink()
        if tree_manifest(retrieved) != manifest:
            raise PublicationError("remote release differs from the published snapshot")

        def run_live(arguments: list[str]) -> None:
            _ = subprocess.run(
                [*command, *arguments],
                env=environment,
                check=True,
                timeout=120,
                stdout=subprocess.DEVNULL,
            )

        publish_live(snapshot, f"s3://{destination.bucket}/airbroke/live/", run_live)
        pointer = root / "current"
        _ = pointer.write_text(release + "\n", encoding="ascii")
        _ = subprocess.run(
            [
                *command,
                "s3api",
                "put-object",
                "--bucket",
                destination.bucket,
                "--key",
                "airbroke/current",
                "--body",
                str(pointer),
                "--content-type",
                "text/plain",
                "--cache-control",
                "no-store",
            ],
            env=environment,
            check=True,
            timeout=120,
            stdout=subprocess.DEVNULL,
        )
        return release


def main() -> int:
    """Parse the operator's explicit source/destination and report publication once."""
    if len(sys.argv) != ARGUMENT_COUNT:
        print("usage: publish-site.py SOURCE BUCKET ENDPOINT", file=sys.stderr)
        return 2
    source, bucket, endpoint = sys.argv[1:]
    try:
        release = publish(Path(source), Destination(bucket, endpoint))
    except (
        PublicationError,
        LivePublicationError,
        OSError,
        UnicodeError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
    ) as error:
        print(f"site publication failed: {error}", file=sys.stderr)
        return 1
    print(f"site publication completed release={release}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
