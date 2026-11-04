# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Imported by publish-site.py after immutable archive verification.
"""Publish support files before the single HTML entrypoint of a static site."""

from __future__ import annotations

import hashlib
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


class LivePublicationError(RuntimeError):
    """Unverified support files cannot authorize replacing the HTML entrypoint."""


def publish_live(snapshot: Path, remote: str, run: Callable[[list[str]], None]) -> None:
    """Retain old assets and verify every support file before uploading index.html."""
    with tempfile.TemporaryDirectory(prefix="site-live-readback-") as temporary:
        retrieved = Path(temporary)

        def transfer(path: Path) -> None:
            name = path.relative_to(snapshot).as_posix()
            cache = (
                "public,max-age=31536000,immutable"
                if name.startswith("_next/static/")
                else "no-cache"
            )
            run(
                [
                    "s3",
                    "cp",
                    str(path),
                    remote + name,
                    "--cache-control",
                    cache,
                    "--only-show-errors",
                ]
            )
            readback = retrieved / name
            readback.parent.mkdir(parents=True, exist_ok=True)
            run(["s3", "cp", remote + name, str(readback), "--only-show-errors"])
            with path.open("rb") as source, readback.open("rb") as downloaded:
                if (
                    hashlib.file_digest(source, "sha256").digest()
                    != hashlib.file_digest(downloaded, "sha256").digest()
                ):
                    raise LivePublicationError(
                        f"live support file verification failed: {name!r}"
                    )

        support = [
            path
            for path in sorted(snapshot.rglob("*"))
            if path.is_file() and path.relative_to(snapshot).as_posix() != "index.html"
        ]
        with ThreadPoolExecutor(max_workers=4) as workers:
            for _ in workers.map(transfer, support):
                pass
        run(
            [
                "s3",
                "cp",
                str(snapshot / "index.html"),
                remote + "index.html",
                "--cache-control",
                "no-cache",
                "--content-type",
                "text/html",
                "--only-show-errors",
            ]
        )
