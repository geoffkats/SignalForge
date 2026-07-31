"""
extract_smiles.py
-----------------
Merge canonical SMILES from LINCS pert_info files (gse70138 + gse92742)
into a single lookup CSV: pert_id -> canonical_smiles.

Output: data/processed/lincs_smiles.csv
  Columns: pert_id, canonical_smiles, pert_iname

Used by features.py to obtain Morgan FPs for any LINCS compound at
inference and training time without needing a hand-curated SMILES table.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)

_PERT_FILES = [
    "data/raw/lincs_level5/gse70138/GSE70138_Broad_LINCS_pert_info.txt.gz",
    "data/raw/lincs_level5/gse92742/GSE92742_Broad_LINCS_pert_info.txt.gz",
]

_OUT = "data/processed/lincs_smiles.csv"


def extract_lincs_smiles(
    pert_files: list[str] | None = None,
    out_path: str = _OUT,
) -> pd.DataFrame:
    """
    Read pert_info files, keep only compound entries with valid SMILES,
    deduplicate by pert_id, write to CSV, and return the DataFrame.
    """
    if pert_files is None:
        pert_files = _PERT_FILES

    frames: list[pd.DataFrame] = []
    for p in pert_files:
        path = Path(p)
        if not path.exists():
            log.warning("pert_info not found, skipping: %s", path)
            continue
        df = pd.read_csv(path, sep="\t", usecols=["pert_id", "canonical_smiles", "pert_iname", "pert_type"])
        before = len(df)
        # Keep compound (trt_cp) entries only
        df = df[df["pert_type"] == "trt_cp"].copy()
        # Drop missing or placeholder SMILES
        df = df[df["canonical_smiles"].notna()]
        df = df[~df["canonical_smiles"].isin(["-666", "restricted", "NA", ""])]
        log.info("%s: %d/%d compound entries with valid SMILES", path.name, len(df), before)
        frames.append(df[["pert_id", "canonical_smiles", "pert_iname"]])

    if not frames:
        raise RuntimeError("No pert_info files found. Check paths.")

    combined = pd.concat(frames, ignore_index=True)
    # Keep first occurrence per pert_id (both files share the same compound registry)
    combined = combined.drop_duplicates(subset="pert_id", keep="first")
    log.info("Total unique compounds with SMILES: %d", len(combined))

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(out, index=False)
    log.info("Wrote SMILES lookup to %s", out)
    return combined


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s",
                        datefmt="%H:%M:%S")
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else _OUT
    df = extract_lincs_smiles(out_path=out)
    print(f"\nExtracted {len(df)} compounds with SMILES -> {out}")
    print(df.head())
