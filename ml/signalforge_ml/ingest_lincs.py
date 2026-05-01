from __future__ import annotations

from pathlib import Path

import pandas as pd

from signalforge_ml.security import verify_checksum


def ingest_lincs_csv(
    input_path: str | Path,
    expected_columns: list[str],
    checksum_sha256: str = "",
    optional_columns: list[str] | None = None,
) -> pd.DataFrame:
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Dataset not found: {input_path}")

    verify_checksum(input_path, checksum_sha256)
    frame = pd.read_csv(input_path)
    missing = [column for column in expected_columns if column not in frame.columns]
    if missing:
        raise ValueError(f"Dataset missing required columns: {missing}")

    keep = list(expected_columns)
    for col in (optional_columns or []):
        if col in frame.columns:
            keep.append(col)

    return frame[keep].copy()