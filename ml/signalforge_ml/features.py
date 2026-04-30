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
_GO_FP_PATH = Path(__file__).parent.parent / "data" / "raw" / "deepcop" / "go_fingerprints.csv"
_GO_MATRIX: pd.DataFrame | None = None
_GO_WIDTH: int = 1107


def _load_go_matrix() -> pd.DataFrame:
    global _GO_MATRIX
    if _GO_MATRIX is None:
        if _GO_FP_PATH.exists():
            _GO_MATRIX = pd.read_csv(_GO_FP_PATH, index_col=0).astype(np.float32)
        else:
            _GO_MATRIX = pd.DataFrame()
    return _GO_MATRIX


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


def build_feature_table(frame: pd.DataFrame, radius: int, n_bits: int) -> tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    compound_vectors = np.stack([smiles_to_morgan(smiles, radius, n_bits) for smiles in frame["smiles"]])
    gene_vectors = np.stack([gene_symbol_to_vector(gene) for gene in frame["gene_symbol"]])
    features = np.concatenate([compound_vectors, gene_vectors], axis=1)
    labels = frame["regulation_label"].map({"up": 1, "down": 0}).to_numpy(dtype=np.int64)
    return features, labels, frame