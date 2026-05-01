from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
from rdkit import Chem
from rdkit.Chem.rdFingerprintGenerator import GetMorganGenerator

# ---------------------------------------------------------------------------
# GO-term gene embeddings (978 LINCS landmark genes × 1107 GO terms)
# Loaded once at import time from the DeepCOP data bundle.
# Falls back to SHA-256 hash embedding for out-of-vocabulary genes.
# ---------------------------------------------------------------------------
_DATA_DIR = Path(__file__).parent.parent / "data" / "raw" / "deepcop"
_GO_FP_PATH = _DATA_DIR / "go_fingerprints.csv"
_PRECOMP_MORGAN_PATH = _DATA_DIR / "inhouse_morgan_2048.csv"
_CORR_COLS_PATH = _DATA_DIR / "LNCAPcorr_cols.csv"

_GO_MATRIX: pd.DataFrame | None = None
_GO_WIDTH: int = 1107

# Cache for pre-computed Morgan FPs keyed by drug name
_PRECOMP_MORGAN: dict[str, np.ndarray] | None = None
# Selected Morgan FP column indices from LNCAPcorr feature selection
_CORR_COLS: np.ndarray | None = None


def _load_go_matrix() -> pd.DataFrame:
    global _GO_MATRIX
    if _GO_MATRIX is None:
        if _GO_FP_PATH.exists():
            _GO_MATRIX = pd.read_csv(_GO_FP_PATH, index_col=0).astype(np.float32)
        else:
            _GO_MATRIX = pd.DataFrame()
    return _GO_MATRIX


def _load_precomp_morgan() -> dict[str, np.ndarray]:
    """Load pre-computed 2048-bit Morgan FPs from inhouse_morgan_2048.csv."""
    global _PRECOMP_MORGAN
    if _PRECOMP_MORGAN is None:
        _PRECOMP_MORGAN = {}
        if _PRECOMP_MORGAN_PATH.exists():
            df = pd.read_csv(_PRECOMP_MORGAN_PATH)
            fp_cols = [c for c in df.columns if c.startswith("fps")]
            for _, row in df.iterrows():
                drug_name = str(row["mol"])
                fp = row[fp_cols].to_numpy(dtype=np.float32)
                _PRECOMP_MORGAN[drug_name] = fp
    return _PRECOMP_MORGAN


def _load_corr_cols() -> np.ndarray | None:
    """Load LNCAPcorr column indices for Morgan FP feature selection (optional)."""
    global _CORR_COLS
    if _CORR_COLS is None and _CORR_COLS_PATH.exists():
        df = pd.read_csv(_CORR_COLS_PATH, header=0)
        _CORR_COLS = df.iloc[:, 0].to_numpy(dtype=np.int32)
    return _CORR_COLS


def smiles_to_morgan(smiles: str, radius: int, n_bits: int) -> np.ndarray:
    molecule = Chem.MolFromSmiles(smiles)
    if molecule is None:
        raise ValueError(f"Invalid SMILES string: {smiles}")

    gen = GetMorganGenerator(radius=radius, fpSize=n_bits)
    bit_vector = gen.GetFingerprint(molecule)
    array = np.zeros((n_bits,), dtype=np.float32)
    for index in bit_vector.GetOnBits():
        array[index] = 1.0
    return array


def gene_symbol_to_vector(gene_symbol: str, width: int = _GO_WIDTH) -> np.ndarray:
    """Return GO-term binary vector if gene is in the LINCS landmark set,
    otherwise fall back to a length-normalised SHA-256 hash embedding."""
    go = _load_go_matrix()
    symbol = gene_symbol.upper()
    # GO matrix index may be mixed case — try exact then upper
    if symbol in go.index:
        vec = go.loc[symbol].to_numpy(dtype=np.float32)
    elif gene_symbol in go.index:
        vec = go.loc[gene_symbol].to_numpy(dtype=np.float32)
    else:
        # Hash fallback — pad/truncate to GO width so shapes stay consistent
        digest = hashlib.sha256(symbol.encode("utf-8")).digest()
        raw = np.frombuffer(digest, dtype=np.uint8).astype(np.float32) / 255.0
        vec = np.resize(raw, width)
    return vec


def _compound_vector(smiles: str, compound_name: str, radius: int, n_bits: int) -> np.ndarray:
    """Return Morgan FP for a compound.

    If smiles == 'PRECOMPUTED', the fingerprint is looked up from the
    pre-computed inhouse_morgan_2048.csv by compound_name.
    Otherwise RDKit computes it from the SMILES string.
    """
    if smiles == "PRECOMPUTED":
        cache = _load_precomp_morgan()
        if compound_name in cache:
            return cache[compound_name]
        raise ValueError(
            f"Drug '{compound_name}' marked PRECOMPUTED but not found in "
            f"{_PRECOMP_MORGAN_PATH}. Add it to inhouse_morgan_2048.csv."
        )
    return smiles_to_morgan(smiles, radius, n_bits)


def build_feature_table(
    frame: pd.DataFrame,
    radius: int,
    n_bits: int,
    use_corr_selection: bool = True,
) -> tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    """Build (features, labels, frame) from the training DataFrame.

    Compound vectors are Morgan FPs (computed from SMILES or read from
    pre-computed cache when smiles == 'PRECOMPUTED').
    Gene vectors are GO-term binary vectors.

    When use_corr_selection=True and LNCAPcorr_cols.csv is present, only the
    correlated Morgan FP bits are used (reduces noise in the compound vector).
    """
    compound_name_col = frame.get("compound_name", frame.get("smiles"))
    compound_vectors_raw = np.stack([
        _compound_vector(row["smiles"], row.get("compound_name", ""), radius, n_bits)
        for _, row in frame.iterrows()
    ])

    # Apply LNCAPcorr feature selection to Morgan FP bits (optional)
    if use_corr_selection:
        corr_idx = _load_corr_cols()
        if corr_idx is not None and len(corr_idx) > 0:
            compound_vectors = compound_vectors_raw[:, corr_idx]
        else:
            compound_vectors = compound_vectors_raw
    else:
        compound_vectors = compound_vectors_raw

    gene_vectors = np.stack([gene_symbol_to_vector(gene) for gene in frame["gene_symbol"]])
    features = np.concatenate([compound_vectors, gene_vectors], axis=1)
    labels = frame["regulation_label"].map({"up": 1, "down": 0}).to_numpy(dtype=np.int64)
    return features, labels, frame