"""
ingest_lincs_level5.py
----------------------
Ingests LINCS Level 5 GCTx signatures into a clean parquet training table.

Supports GSE92742 and GSE70138. Filters to target cell lines, applies
z-score thresholding to produce discrete up/down labels, and stores an
intermediate parquet that downstream feature builders consume.

Usage (CLI):
    python -m signalforge_ml.ingest_lincs_level5 \
        --lincs-dir data/raw/lincs_level5 \
        --out data/processed/lincs_multicell.parquet \
        --cell-lines LNCAP MCF7 PC3 \
        --zscore-thresh 2.0 \
        --datasets gse70138

Usage (library):
    from signalforge_ml.ingest_lincs_level5 import ingest_level5
    frame = ingest_level5(lincs_dir="data/raw/lincs_level5", ...)
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Iterable

import pandas as pd

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Cell line names as they appear in LINCS sig_info cell_id column.
# Variants and aliases are normalised in _normalise_cell_id().
CELL_LINE_ALIASES: dict[str, str] = {
    "LNCAP": "LNCAP",
    "LNCaP": "LNCAP",
    "lncap": "LNCAP",
    "MCF7": "MCF7",
    "mcf7": "MCF7",
    "PC3": "PC3",
    "pc3": "PC3",
    "PC-3": "PC3",
}

# Perturbation types to keep. trt_cp = small-molecule compound treatment.
KEEP_PERT_TYPES = {"trt_cp"}

# Minimum number of replicates a signature must have to be included.
# Level 5 MODZ already collapses replicates, but distil_nsample records
# how many went in. Low values indicate unreliable signatures.
MIN_REPLICATES = 2

# Metadata columns to carry through to the output parquet.
SIG_META_COLS = [
    "sig_id",
    "pert_id",
    "pert_iname",       # human-readable compound name
    "cell_id",
    "pert_idose",       # dose string
    "pert_itime",       # timepoint string
    "pert_type",
    "distil_nsample",   # replicate count
]

# Landmark gene count in L1000
N_LANDMARK_GENES = 978


# ---------------------------------------------------------------------------
# Dataset file layouts
# ---------------------------------------------------------------------------

# Each dataset entry maps to the expected filenames within its subdirectory.
DATASET_FILES: dict[str, dict[str, str]] = {
    "gse92742": {
        "gctx": (
            "GSE92742_Broad_LINCS_Level5_COMPZ.MODZ_n473647x12328.gctx.gz"
        ),
        "sig_info": "GSE92742_Broad_LINCS_sig_info.txt.gz",
        "pert_info": "GSE92742_Broad_LINCS_pert_info.txt.gz",
        "gene_info": "GSE92742_Broad_LINCS_gene_info.txt.gz",
    },
    "gse70138": {
        "gctx": (
            "GSE70138_Broad_LINCS_Level5_COMPZ_n118050x12328_2017-03-06.gctx.gz"
        ),
        "sig_info": "GSE70138_Broad_LINCS_sig_info_2017-03-06.txt.gz",
        "pert_info": "GSE70138_Broad_LINCS_pert_info.txt.gz",
        "gene_info": "GSE70138_Broad_LINCS_gene_info_2017-03-06.txt.gz",
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _check_cmappy() -> None:
    try:
        import cmapPy  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "cmapPy is required for LINCS Level 5 ingestion.\n"
            "Install it with:  pip install cmapPy"
        ) from exc


def _normalise_cell_id(cell_id: str) -> str:
    return CELL_LINE_ALIASES.get(cell_id, cell_id.upper())


def _load_sig_info(path: Path, cell_lines: set[str]) -> pd.DataFrame:
    """Load and filter sig_info to target cell lines and compound treatments."""
    log.info("Loading sig_info from %s", path)
    df = pd.read_csv(path, sep="\t", low_memory=False)

    df["cell_id_norm"] = df["cell_id"].map(_normalise_cell_id)
    df = df[
        df["cell_id_norm"].isin(cell_lines)
        & df["pert_type"].isin(KEEP_PERT_TYPES)
    ].copy()

    if "distil_nsample" in df.columns:
        df = df[df["distil_nsample"] >= MIN_REPLICATES]

    log.info("  %d signatures after cell-line + pert_type filter", len(df))
    return df


def _load_gene_info(path: Path, landmark_only: bool = True) -> pd.DataFrame:
    """Load gene_info, optionally restricting to landmark genes."""
    log.info("Loading gene_info from %s", path)
    df = pd.read_csv(path, sep="\t", low_memory=False)
    if landmark_only and "pr_is_lm" in df.columns:
        df = df[df["pr_is_lm"] == 1].copy()
        log.info("  %d landmark genes retained", len(df))
    return df


def _load_gctx_slice(
    gctx_path: Path,
    sig_ids: list[str],
    gene_ids: list[str],
) -> pd.DataFrame:
    """
    Load a slice of the GCTx file for the requested signatures and genes.
    Returns a DataFrame with shape (n_genes, n_sigs), index = gene_id (str).

    cmapPy reads GCTx lazily so this avoids loading the full matrix.
    """
    import gzip
    import shutil
    import tempfile
    from cmapPy.pandasGEXpress.parse import parse  # type: ignore

    log.info(
        "Reading GCTx slice: %d sigs x %d genes from %s",
        len(sig_ids),
        len(gene_ids),
        gctx_path.name,
    )

    # cmapPy cannot read .gctx.gz — prefer a pre-decompressed .gctx sibling,
    # otherwise decompress to a temp file (slow, ~5 min for 5 GB).
    tmp_path = None
    if gctx_path.suffix == ".gz":
        permanent = gctx_path.with_suffix("")  # strip .gz -> .gctx
        if permanent.exists():
            log.info("Using pre-decompressed file: %s", permanent.name)
            parse_path = permanent
        else:
            log.warning(
                "No pre-decompressed .gctx found. Decompressing to tmp (slow). "
                "Run: python -c \"import gzip,shutil; "
                "shutil.copyfileobj(gzip.open('%s','rb'), open('%s','wb'))\" "
                "once to avoid this.",
                gctx_path,
                permanent,
            )
            tmp = tempfile.NamedTemporaryFile(suffix=".gctx", delete=False)
            tmp_path = Path(tmp.name)
            tmp.close()
            with gzip.open(gctx_path, "rb") as f_in, open(tmp_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
            parse_path = tmp_path
    else:
        parse_path = gctx_path

    try:
        gctoo = parse(
            str(parse_path),
            cid=sig_ids,
            rid=[str(g) for g in gene_ids],
        )
    finally:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink()

    # gctoo.data_df is (n_rid x n_cid) i.e. genes x signatures
    df = gctoo.data_df
    df.index = df.index.astype(str)
    return df


def _zscore_to_labels(
    z: float,
    thresh: float,
) -> int | None:
    """
    Convert a z-score to a ternary label.
    Returns 1 (up), 0 (down), or None (below threshold -> excluded).
    """
    if z >= thresh:
        return 1
    if z <= -thresh:
        return 0
    return None


# ---------------------------------------------------------------------------
# Core ingestion
# ---------------------------------------------------------------------------

def ingest_level5(
    lincs_dir: str | Path,
    cell_lines: Iterable[str] = ("LNCAP", "MCF7", "PC3"),
    datasets: Iterable[str] = ("gse70138",),
    zscore_thresh: float = 2.0,
    landmark_only: bool = True,
    max_sigs_per_dataset: int | None = None,
    sig_chunk_size: int = 5000,
) -> pd.DataFrame:
    """
    Build a clean training table from LINCS Level 5 GCTx files.

    Parameters
    ----------
    lincs_dir:
        Root directory written by download_lincs_level5.py.
        Expected layout: lincs_dir/{dataset}/{filename}
    cell_lines:
        Cell lines to include. Normalised internally.
    datasets:
        Which GEO datasets to include. One or both of gse92742, gse70138.
    zscore_thresh:
        Absolute z-score threshold for labelling. Genes below this in both
        directions are dropped (ambiguous/noise). Typical values: 1.5-2.5.
    landmark_only:
        If True (default), restrict to the 978 landmark genes.
    max_sigs_per_dataset:
        Cap on signatures per dataset for development / smoke testing.
        Set to e.g. 500 during local iteration to avoid loading full GCTx.
    sig_chunk_size:
        Number of signatures to process per chunk. Lower values use less memory
        but take longer. Default 5000 is safe for ~16 GB RAM machines.

    Returns
    -------
    DataFrame with columns:
        sig_id, pert_id, pert_iname, cell_id, pert_idose, pert_itime,
        pert_type, distil_nsample, gene_id, gene_symbol, zscore, label
    """
    _check_cmappy()

    lincs_dir = Path(lincs_dir)
    cell_lines_norm = {_normalise_cell_id(c) for c in cell_lines}
    datasets = list(datasets)

    all_frames: list[pd.DataFrame] = []

    for dataset in datasets:
        if dataset not in DATASET_FILES:
            raise ValueError(
                f"Unknown dataset '{dataset}'. "
                f"Choose from: {list(DATASET_FILES)}"
            )

        files = DATASET_FILES[dataset]
        ds_dir = lincs_dir / dataset

        # --- validate files exist ---
        for key, fname in files.items():
            fpath = ds_dir / fname
            if not fpath.exists():
                raise FileNotFoundError(
                    f"Expected {key} file not found: {fpath}\n"
                    f"Run: python scripts/download_lincs_level5.py "
                    f"--dataset {dataset} --out-dir {lincs_dir}"
                )

        # --- metadata ---
        sig_info = _load_sig_info(
            ds_dir / files["sig_info"],
            cell_lines=cell_lines_norm,
        )
        if sig_info.empty:
            log.warning(
                "No signatures matched cell lines %s in %s - skipping",
                cell_lines_norm,
                dataset,
            )
            continue

        gene_info = _load_gene_info(
            ds_dir / files["gene_info"],
            landmark_only=landmark_only,
        )

        if max_sigs_per_dataset is not None:
            sig_info = sig_info.head(max_sigs_per_dataset)
            log.info(
                "  Capped to %d signatures for development run",
                len(sig_info),
            )

        sig_ids = sig_info["sig_id"].tolist()
        gene_ids = gene_info["pr_gene_id"].tolist()
        gene_id_to_symbol = gene_info.set_index(
            gene_info["pr_gene_id"].astype(str)
        )["pr_gene_symbol"].to_dict()
        meta_cols = [c for c in SIG_META_COLS if c in sig_info.columns]

        dataset_frames: list[pd.DataFrame] = []
        n_chunks = (len(sig_ids) + sig_chunk_size - 1) // sig_chunk_size

        for chunk_idx in range(n_chunks):
            start = chunk_idx * sig_chunk_size
            end = min((chunk_idx + 1) * sig_chunk_size, len(sig_ids))
            chunk_sig_ids = sig_ids[start:end]
            sig_info_chunk = sig_info[sig_info["sig_id"].isin(chunk_sig_ids)].copy()

            log.info(
                "Dataset %s chunk %d/%d: %d signatures",
                dataset,
                chunk_idx + 1,
                n_chunks,
                len(chunk_sig_ids),
            )

            # --- expression matrix ---
            gctx_path = ds_dir / files["gctx"]
            expr = _load_gctx_slice(gctx_path, chunk_sig_ids, gene_ids)

            # expr is (genes x sigs). Melt to long format.
            log.info("Melting expression matrix to long format...")
            expr.index.name = "gene_id"
            expr_long = (
                expr.reset_index()
                .melt(id_vars="gene_id", var_name="sig_id", value_name="zscore")
            )

            # --- attach gene symbols ---
            expr_long["gene_symbol"] = expr_long["gene_id"].map(gene_id_to_symbol)

            # --- attach signature metadata ---
            expr_long = expr_long.merge(
                sig_info_chunk[meta_cols].rename(columns={"cell_id": "cell_id_raw"}),
                on="sig_id",
                how="left",
            )
            expr_long["cell_id"] = expr_long["cell_id_raw"].map(_normalise_cell_id)
            expr_long.drop(columns=["cell_id_raw"], inplace=True, errors="ignore")

            # --- label from z-score ---
            log.info(
                "Applying z-score threshold %.2f to generate labels...", zscore_thresh
            )
            expr_long["label"] = expr_long["zscore"].apply(
                lambda z: _zscore_to_labels(z, zscore_thresh)
            )
            before = len(expr_long)
            expr_long = expr_long.dropna(subset=["label"]).copy()
            expr_long["label"] = expr_long["label"].astype(int)
            after = len(expr_long)
            log.info(
                "  Retained %d / %d rows (%.1f%%) above z-score threshold",
                after,
                before,
                100 * after / max(before, 1),
            )

            expr_long["source_dataset"] = dataset
            dataset_frames.append(expr_long)

        if dataset_frames:
            all_frames.append(pd.concat(dataset_frames, ignore_index=True))

    if not all_frames:
        raise RuntimeError(
            "No data was ingested. Check cell line names and dataset files."
        )

    result = pd.concat(all_frames, ignore_index=True)

    # --- dedup: keep highest |zscore| per (pert_id, gene_id, cell_id) ---
    # Multiple doses/timepoints may exist; keep the strongest signal.
    result["abs_zscore"] = result["zscore"].abs()
    result = (
        result.sort_values("abs_zscore", ascending=False)
        .drop_duplicates(subset=["pert_id", "gene_id", "cell_id"])
        .drop(columns=["abs_zscore"])
        .reset_index(drop=True)
    )

    log.info(
        "Final table: %d rows, %d unique genes, %d unique compounds, %d cell lines",
        len(result),
        result["gene_id"].nunique(),
        result["pert_id"].nunique(),
        result["cell_id"].nunique(),
    )
    log.info(
        "Label distribution: %s",
        dict(result["label"].value_counts().sort_index()),
    )

    return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Ingest LINCS Level 5 GCTx data into a clean parquet training table."
        )
    )
    p.add_argument(
        "--lincs-dir",
        default="data/raw/lincs_level5",
        help="Root directory of downloaded LINCS files",
    )
    p.add_argument(
        "--out",
        default="data/processed/lincs_multicell.parquet",
        help="Output parquet path",
    )
    p.add_argument(
        "--cell-lines",
        nargs="+",
        default=["LNCAP", "MCF7", "PC3"],
        help="Cell lines to include",
    )
    p.add_argument(
        "--datasets",
        nargs="+",
        choices=["gse92742", "gse70138"],
        default=["gse70138"],
        help="GEO datasets to process",
    )
    p.add_argument(
        "--zscore-thresh",
        type=float,
        default=2.0,
        help="Absolute z-score threshold for labelling (default: 2.0)",
    )
    p.add_argument(
        "--no-landmark-only",
        action="store_false",
        dest="landmark_only",
        help="Include inferred genes as well as landmark genes",
    )
    p.add_argument(
        "--max-sigs",
        type=int,
        default=None,
        help="Cap signatures per dataset (for development smoke tests)",
    )
    p.add_argument(
        "--chunk-sigs",
        type=int,
        default=5000,
        help="Signatures to process per chunk (default: 5000)",
    )
    p.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return p


def main() -> None:
    args = _build_parser().parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        datefmt="%H:%M:%S",
    )

    frame = ingest_level5(
        lincs_dir=args.lincs_dir,
        cell_lines=args.cell_lines,
        datasets=args.datasets,
        zscore_thresh=args.zscore_thresh,
        landmark_only=args.landmark_only,
        max_sigs_per_dataset=args.max_sigs,
        sig_chunk_size=args.chunk_sigs,
    )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(out, index=False)
    log.info("Wrote %d rows to %s", len(frame), out)

    print()
    print(f"Output : {out}")
    print(f"Shape  : {frame.shape}")
    print(f"Cols   : {list(frame.columns)}")
    print()
    print("Label distribution:")
    print(frame["label"].value_counts().sort_index().to_string())
    print()
    print("Cell line distribution:")
    print(frame["cell_id"].value_counts().to_string())
    print()
    print("Next step:")
    print(
        "  python -m signalforge_ml.features "
        f"--input {out} --config ml/configs/lincs_multicell.yaml"
    )


if __name__ == "__main__":
    main()
