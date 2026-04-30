"""
prepare_deepcop.py – Bridge DeepCOP LNCaP DESeq2 results → SignalForge training CSV.

Input files (all under data/raw/deepcop/):
  DESeq2results.csv   – Drug, geneName, log2FoldChange, padj no NA, pvalue
  go_fingerprints.csv – gene × GO-term binary matrix (978 landmark genes)

Output:
  data/raw/deepcop/lncap_training.csv
  Columns: perturbation_id, compound_id, compound_name, smiles, gene_symbol, regulation_label

Label strategy:
  UP   : log2FoldChange >  FC_THRESHOLD
  DOWN : log2FoldChange < -FC_THRESHOLD
  Neutral rows (|log2FC| ≤ FC_THRESHOLD) are discarded.

Only drugs with a valid entry in DRUG_SMILES are included.
Add VPC compound SMILES below once sourced from the original publications.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Known-drug SMILES map
# Enzalutamide (MDV3100) – ChEMBL1346080, PubChem CID 15951529
# Molecular formula C21H16F4N4O2S, MW 464.44
# IUPAC: 4-[3-[4-cyano-3-(trifluoromethyl)phenyl]-5,5-dimethyl-4-oxo-2-
#         thioxoimidazolidin-1-yl]-2-fluoro-N-methylbenzamide
# ---------------------------------------------------------------------------
DRUG_SMILES: dict[str, str] = {
    "Enzalutamide": "CC1(C)C(=O)N(c2ccc(C#N)cc2C(F)(F)F)C(=S)N1c3ccc(C(=O)NC)cc3F",
    # Uncomment and fill SMILES when sourced from publication supplementaries:
    # "VPC13789":   "...",
    # "VPC14449":   "...",
    # "VPC17005":   "...",
    # "VPC220010":  "...",
}

# Absolute log2FC required to call up / down
FC_THRESHOLD: float = 0.5


def prepare(
    deseq2_path: str | Path,
    go_path: str | Path,
    output_path: str | Path,
    fc_threshold: float = FC_THRESHOLD,
    require_landmark: bool = True,
) -> pd.DataFrame:
    """Build training CSV and return the resulting DataFrame."""
    deseq2_path = Path(deseq2_path)
    go_path = Path(go_path)
    output_path = Path(output_path)

    # ------------------------------------------------------------------
    # 1. Load & normalise DESeq2 results
    # ------------------------------------------------------------------
    df = pd.read_csv(deseq2_path)
    df.columns = df.columns.str.strip()
    df = df.rename(
        columns={
            "Drug": "drug",
            "geneName": "gene_symbol",
            "log2FoldChange": "log2fc",
            "padj no NA": "padj",
            "pvalue": "pvalue",
        }
    )
    print(f"[INFO] Loaded {len(df):,} rows from {deseq2_path.name}")

    # ------------------------------------------------------------------
    # 2. Drop drugs without SMILES
    # ------------------------------------------------------------------
    all_drugs = set(df["drug"].unique())
    known_drugs = set(DRUG_SMILES.keys())
    missing_drugs = all_drugs - known_drugs
    if missing_drugs:
        print(
            f"[WARN] No SMILES for: {sorted(missing_drugs)} — these rows are excluded.\n"
            f"       Add entries to DRUG_SMILES in prepare_deepcop.py to include them."
        )
    df = df[df["drug"].isin(known_drugs)].copy()
    if df.empty:
        raise RuntimeError(
            "No rows remain after SMILES filter.\n"
            "Add at least one drug's SMILES to DRUG_SMILES in prepare_deepcop.py."
        )

    # ------------------------------------------------------------------
    # 3. Apply fold-change threshold → regulation label
    # ------------------------------------------------------------------
    before = len(df)
    df = df[df["log2fc"].abs() > fc_threshold].copy()
    print(
        f"[INFO] FC filter (|log2FC| > {fc_threshold}): {before:,} → {len(df):,} rows"
    )
    df["regulation_label"] = df["log2fc"].apply(lambda x: "up" if x > 0 else "down")

    # ------------------------------------------------------------------
    # 4. Restrict to landmark genes (GO fingerprint index)
    # ------------------------------------------------------------------
    if require_landmark:
        go_df = pd.read_csv(go_path, index_col=0)
        landmark_genes = set(go_df.index.astype(str).str.strip())
        before = len(df)
        df = df[df["gene_symbol"].isin(landmark_genes)].copy()
        print(
            f"[INFO] Landmark gene filter: {before:,} → {len(df):,} rows "
            f"({len(landmark_genes)} landmark genes available)"
        )

    if df.empty:
        raise RuntimeError(
            "No rows remain after gene filter.\n"
            "Check that go_fingerprints.csv gene names match DESeq2 gene symbols."
        )

    # ------------------------------------------------------------------
    # 5. Validate SMILES with RDKit
    # ------------------------------------------------------------------
    try:
        from rdkit import Chem  # type: ignore
        for drug, smiles in DRUG_SMILES.items():
            if drug in df["drug"].values:
                mol = Chem.MolFromSmiles(smiles)
                if mol is None:
                    raise ValueError(
                        f"RDKit rejected SMILES for '{drug}': {smiles!r}\n"
                        f"Fix the SMILES entry in DRUG_SMILES."
                    )
        print("[INFO] SMILES validation passed (RDKit)")
    except ImportError:
        print("[WARN] RDKit not available; skipping SMILES validation.")

    # ------------------------------------------------------------------
    # 6. Build required columns
    # ------------------------------------------------------------------
    df = df.copy()
    df["compound_name"] = df["drug"]
    df["smiles"] = df["drug"].map(DRUG_SMILES)
    df["compound_id"] = df["drug"].apply(
        lambda d: "BRD-" + hashlib.md5(d.encode()).hexdigest()[:8].upper()
    )
    df["perturbation_id"] = (
        df["compound_id"] + "_" + df["gene_symbol"] + "_LNCaP"
    )

    result = df[
        [
            "perturbation_id",
            "compound_id",
            "compound_name",
            "smiles",
            "gene_symbol",
            "regulation_label",
        ]
    ].reset_index(drop=True)

    # ------------------------------------------------------------------
    # 7. Write output
    # ------------------------------------------------------------------
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)

    label_counts = result["regulation_label"].value_counts().to_dict()
    print(f"\n[OK] Training CSV written: {output_path}")
    print(f"     Rows:              {len(result):,}")
    print(f"     Label distribution: {label_counts}")
    print(f"     Unique compounds:   {result['compound_name'].nunique()}")
    print(f"     Unique genes:       {result['gene_symbol'].nunique()}")
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent  # ml/
    prepare(
        deseq2_path=root / "data/raw/deepcop/DESeq2results.csv",
        go_path=root / "data/raw/deepcop/go_fingerprints.csv",
        output_path=root / "data/raw/deepcop/lncap_training.csv",
        # Landmark gene filter disabled: DESeq2 captures all coding genes,
        # not just the 978 L1000 landmark genes. Hash-based gene embeddings
        # work for any gene symbol so no restriction is needed.
        require_landmark=False,
    )
