from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_checksum(path: str | Path, expected_checksum: str) -> None:
    if not expected_checksum:
        return

    actual_checksum = sha256_file(path)
    if actual_checksum != expected_checksum:
        raise ValueError("Dataset checksum mismatch. Refusing to train on unverified biotech data.")