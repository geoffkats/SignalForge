"""Unit tests for signalforge_ml.features — fingerprint and gene embedding functions."""
from __future__ import annotations

import numpy as np
import pytest

from signalforge_ml.features import (
    _GO_WIDTH,
    gene_symbol_to_vector,
    smiles_to_morgan,
)

# ---------------------------------------------------------------------------
# SMILES → Morgan fingerprint
# ---------------------------------------------------------------------------

ENZALUTAMIDE = "CC1(C)C(=O)N(c2ccc(C#N)cc2C(F)(F)F)C(=S)N1c3ccc(C(=O)NC)cc3F"
ASPIRIN = "CC(=O)Oc1ccccc1C(=O)O"
INVALID_SMILES = "not_a_smiles_string$$"


def test_morgan_returns_correct_length():
    fp = smiles_to_morgan(ENZALUTAMIDE, radius=2, n_bits=2048)
    assert fp.shape == (2048,)


def test_morgan_dtype_is_float32():
    fp = smiles_to_morgan(ASPIRIN, radius=2, n_bits=2048)
    assert fp.dtype == np.float32


def test_morgan_values_are_binary():
    fp = smiles_to_morgan(ENZALUTAMIDE, radius=2, n_bits=2048)
    assert set(fp.tolist()).issubset({0.0, 1.0})


def test_morgan_different_compounds_differ():
    fp1 = smiles_to_morgan(ENZALUTAMIDE, radius=2, n_bits=2048)
    fp2 = smiles_to_morgan(ASPIRIN, radius=2, n_bits=2048)
    assert not np.array_equal(fp1, fp2)


def test_morgan_same_compound_deterministic():
    fp1 = smiles_to_morgan(ENZALUTAMIDE, radius=2, n_bits=2048)
    fp2 = smiles_to_morgan(ENZALUTAMIDE, radius=2, n_bits=2048)
    np.testing.assert_array_equal(fp1, fp2)


def test_morgan_invalid_smiles_raises():
    with pytest.raises(ValueError, match="Invalid SMILES"):
        smiles_to_morgan(INVALID_SMILES, radius=2, n_bits=2048)


# ---------------------------------------------------------------------------
# Gene symbol → GO vector (or hash fallback)
# ---------------------------------------------------------------------------

def test_gene_vector_returns_correct_length():
    vec = gene_symbol_to_vector("AR")
    assert vec.shape == (_GO_WIDTH,)


def test_gene_vector_dtype_is_float32():
    vec = gene_symbol_to_vector("KLK3")
    assert vec.dtype == np.float32


def test_gene_vector_values_in_range():
    vec = gene_symbol_to_vector("PTEN")
    assert vec.min() >= 0.0
    assert vec.max() <= 1.0


def test_gene_vector_different_genes_differ():
    vec_ar = gene_symbol_to_vector("AR")
    vec_pten = gene_symbol_to_vector("PTEN")
    assert not np.array_equal(vec_ar, vec_pten)


def test_gene_vector_deterministic():
    v1 = gene_symbol_to_vector("EZH2")
    v2 = gene_symbol_to_vector("EZH2")
    np.testing.assert_array_equal(v1, v2)


def test_unknown_gene_fallback_has_correct_shape():
    """Genes outside the 978-gene landmark set fall back to hash embedding."""
    vec = gene_symbol_to_vector("TOTALLY_UNKNOWN_GENE_XYZ")
    assert vec.shape == (_GO_WIDTH,)
