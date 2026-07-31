"""
download_lincs_level5.py
------------------------
Downloads LINCS Level 5 GCTx files and metadata from NCBI GEO.

Usage:
    python scripts/download_lincs_level5.py --out-dir data/raw/lincs_level5
    python scripts/download_lincs_level5.py --out-dir data/raw/lincs_level5 --dataset gse70138
    python scripts/download_lincs_level5.py --out-dir data/raw/lincs_level5 --skip-existing

Files downloaded per dataset:
    GSE92742  ~12 GB gctx  (Phase 1 LINCS, 2013-2015)
    GSE70138  ~3  GB gctx  (Phase 2 LINCS, 2016)

Both are needed for full compound coverage. GSE70138 alone is enough
for a first multi-cell pass and is much faster to download.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import time
from pathlib import Path
from typing import NamedTuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


# ---------------------------------------------------------------------------
# File manifest
# ---------------------------------------------------------------------------

class RemoteFile(NamedTuple):
    dataset: str
    filename: str
    url: str
    sha256: str          # empty string = skip checksum (large files)
    size_hint_gb: float  # informational only


# GEO FTP base paths
_GEO92 = "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE92nnn/GSE92742/suppl"
_GEO70 = "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE70nnn/GSE70138/suppl"

MANIFEST: list[RemoteFile] = [
    # --- GSE92742 (Phase 1) ---
    RemoteFile(
        dataset="gse92742",
        filename="GSE92742_Broad_LINCS_Level5_COMPZ.MODZ_n473647x12328.gctx.gz",
        url=f"{_GEO92}/GSE92742_Broad_LINCS_Level5_COMPZ.MODZ_n473647x12328.gctx.gz",
        sha256="",  # ~12 GB, checksum skipped
        size_hint_gb=12.1,
    ),
    RemoteFile(
        dataset="gse92742",
        filename="GSE92742_Broad_LINCS_sig_info.txt.gz",
        url=f"{_GEO92}/GSE92742_Broad_LINCS_sig_info.txt.gz",
        sha256="",
        size_hint_gb=0.02,
    ),
    RemoteFile(
        dataset="gse92742",
        filename="GSE92742_Broad_LINCS_pert_info.txt.gz",
        url=f"{_GEO92}/GSE92742_Broad_LINCS_pert_info.txt.gz",
        sha256="",
        size_hint_gb=0.01,
    ),
    RemoteFile(
        dataset="gse92742",
        filename="GSE92742_Broad_LINCS_gene_info.txt.gz",
        url=f"{_GEO92}/GSE92742_Broad_LINCS_gene_info.txt.gz",
        sha256="",
        size_hint_gb=0.001,
    ),
    # --- GSE70138 (Phase 2 — smaller, good starting point) ---
    RemoteFile(
        dataset="gse70138",
        filename="GSE70138_Broad_LINCS_Level5_COMPZ_n118050x12328_2017-03-06.gctx.gz",
        url=f"{_GEO70}/GSE70138_Broad_LINCS_Level5_COMPZ_n118050x12328_2017-03-06.gctx.gz",
        sha256="",
        size_hint_gb=3.2,
    ),
    RemoteFile(
        dataset="gse70138",
        filename="GSE70138_Broad_LINCS_sig_info_2017-03-06.txt.gz",
        url=f"{_GEO70}/GSE70138_Broad_LINCS_sig_info_2017-03-06.txt.gz",
        sha256="",
        size_hint_gb=0.005,
    ),
    RemoteFile(
        dataset="gse70138",
        filename="GSE70138_Broad_LINCS_pert_info.txt.gz",
        url=f"{_GEO70}/GSE70138_Broad_LINCS_pert_info.txt.gz",
        sha256="",
        size_hint_gb=0.003,
    ),
    RemoteFile(
        dataset="gse70138",
        filename="GSE70138_Broad_LINCS_gene_info.txt.gz",
        url=f"{_GEO70}/GSE70138_Broad_LINCS_gene_info.txt.gz",
        sha256="",
        size_hint_gb=0.001,
    ),
]


# ---------------------------------------------------------------------------
# Download helpers
# ---------------------------------------------------------------------------

CHUNK = 1024 * 1024  # 1 MB chunks (more stable on constrained environments)


def _format_bytes(n: int) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def _download_file(url: str, dest: Path, skip_existing: bool) -> bool:
    """
    Stream-download url to dest. Returns True if file was downloaded,
    False if skipped. Raises on network or HTTP errors.
    """
    if skip_existing and dest.exists():
        print(f"  [skip] {dest.name} already exists")
        return False

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")

    req = Request(url, headers={"User-Agent": "signalforge-downloader/1.0"})
    try:
        with urlopen(req, timeout=60) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            start = time.time()

            with open(tmp, "wb") as fh:
                while True:
                    chunk = resp.read(CHUNK)
                    if not chunk:
                        break
                    fh.write(chunk)
                    downloaded += len(chunk)
                    elapsed = time.time() - start
                    rate = downloaded / max(elapsed, 1e-6)
                    pct = (downloaded / total * 100) if total else 0
                    print(
                        f"\r  {_format_bytes(downloaded)}"
                        + (f" / {_format_bytes(total)} ({pct:.0f}%)" if total else "")
                        + f"  {_format_bytes(int(rate))}/s",
                        end="",
                        flush=True,
                    )

        print()  # newline after progress
        tmp.rename(dest)
        return True

    except (URLError, HTTPError, OSError, MemoryError) as exc:
        if tmp.exists():
            tmp.unlink()
        raise RuntimeError(f"Download failed for {url}: {exc}") from exc


def _verify_sha256(path: Path, expected: str) -> bool:
    if not expected:
        return True
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest() == expected


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Download LINCS Level 5 GCTx files and metadata from NCBI GEO."
    )
    p.add_argument(
        "--out-dir",
        default="data/raw/lincs_level5",
        help="Directory to write downloaded files (default: data/raw/lincs_level5)",
    )
    p.add_argument(
        "--dataset",
        choices=["gse92742", "gse70138", "both"],
        default="gse70138",
        help=(
            "Which GEO dataset to download. "
            "gse70138 is ~3 GB and a good first pass. "
            "gse92742 is ~12 GB. "
            "both downloads everything. (default: gse70138)"
        ),
    )
    p.add_argument(
        "--skip-existing",
        action="store_true",
        default=True,
        help="Skip files that already exist at the destination (default: True)",
    )
    p.add_argument(
        "--no-skip-existing",
        action="store_false",
        dest="skip_existing",
        help="Re-download files even if they already exist",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)

    datasets = {"gse92742", "gse70138"} if args.dataset == "both" else {args.dataset}

    files = [f for f in MANIFEST if f.dataset in datasets]
    total_hint = sum(f.size_hint_gb for f in files)

    print("SignalForge - LINCS Level 5 downloader")
    print(f"  Output dir : {out_dir.resolve()}")
    print(f"  Datasets   : {', '.join(sorted(datasets))}")
    print(f"  Files      : {len(files)}")
    print(f"  Size hint  : ~{total_hint:.1f} GB (compressed)")
    print()

    errors: list[str] = []

    for i, remote in enumerate(files, 1):
        dest = out_dir / remote.dataset / remote.filename
        print(f"[{i}/{len(files)}] {remote.filename}")
        print(f"  Dest : {dest}")
        print(f"  Size : ~{remote.size_hint_gb:.2f} GB")

        try:
            downloaded = _download_file(remote.url, dest, args.skip_existing)
        except RuntimeError as exc:
            print(f"  [ERROR] {exc}")
            errors.append(str(exc))
            continue

        if downloaded and remote.sha256:
            print("  Verifying checksum...", end=" ")
            if _verify_sha256(dest, remote.sha256):
                print("OK")
            else:
                msg = f"Checksum mismatch for {dest.name}"
                print(f"FAIL - {msg}")
                errors.append(msg)

        print()

    if errors:
        print(f"Completed with {len(errors)} error(s):")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print("All files downloaded successfully.")
        print()
        print("Next step:")
        print(
            f"  python -m signalforge_ml.ingest_lincs_level5 "
            f"--lincs-dir {out_dir} --out data/processed/lincs_multicell.parquet"
        )


if __name__ == "__main__":
    main()
