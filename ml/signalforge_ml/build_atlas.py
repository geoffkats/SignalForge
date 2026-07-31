"""Build a curated compound atlas for reverse-signature search."""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import pandas as pd
from rdkit import Chem

_PKG_ROOT = Path(__file__).parent.parent
_DEFAULT_SMILES = _PKG_ROOT / "data" / "processed" / "lincs_smiles.csv"
_DEFAULT_OUT = _PKG_ROOT / "artifacts" / "libraries" / "compound_atlas.json"

# Clinical / DeepCOP LNCaP AR panel — always retained
_CLINICAL_PANEL: list[dict[str, str]] = [
    {
        "compound_id": "BRD-FBDF768A",
        "compound_name": "Enzalutamide",
        "smiles": "CC1(C)C(=O)N(c2ccc(C#N)cc2C(F)(F)F)C(=S)N1c3ccc(C(=O)NC)cc3F",
    },
    {
        "compound_id": "BRD-A80177499",
        "compound_name": "Bicalutamide",
        "smiles": "CC(CS(=O)(=O)c1ccc(F)cc1)(C#N)NC(=O)c1ccc(cc1)OC(F)(F)F",
    },
    {
        "compound_id": "BRD-K88742100",
        "compound_name": "Apalutamide",
        "smiles": "Cc1c(F)cccc1N1CC(C)(C)CN(c2ncc(C#N)c(=O)n2)C1=O",
    },
    {
        "compound_id": "BRD-K88742101",
        "compound_name": "Darolutamide",
        "smiles": "CC(O)c1cc(NC(=O)c2cc(C(F)(F)F)ccc2N)ccc1F",
    },
    {
        "compound_id": "BRD-K12345678",
        "compound_name": "Vorinostat",
        "smiles": "O=C(CCCCCCC(=O)Nc1ccccc1)NO",
    },
    {
        "compound_id": "BRD-K87654321",
        "compound_name": "Entinostat",
        "smiles": "CCOc1cc(NC(=O)Cc2ccc(NC(=O)c3ccncc3)cc2)ccc1N",
    },
]

log = logging.getLogger(__name__)


def _canonical(smiles: str) -> str | None:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return Chem.MolToSmiles(mol)


def _is_named_drug(name: str) -> bool:
    cleaned = (name or "").strip()
    if not cleaned:
        return False
    upper = cleaned.upper()
    if upper.startswith("BRD-"):
        return False
    if cleaned.startswith("compound "):
        return False
    return True


def build_compound_atlas(
    smiles_csv: Path = _DEFAULT_SMILES,
    out_path: Path = _DEFAULT_OUT,
    target_size: int = 300,
) -> list[dict[str, str]]:
    """Return curated atlas rows and write JSON to out_path."""
    atlas: list[dict[str, str]] = []
    seen_smiles: set[str] = set()
    seen_ids: set[str] = set()

    for row in _CLINICAL_PANEL:
        canonical = _canonical(row["smiles"])
        if canonical is None:
            continue
        entry = {
            "compound_id": row["compound_id"],
            "compound_name": row["compound_name"],
            "smiles": canonical,
        }
        atlas.append(entry)
        seen_smiles.add(canonical)
        seen_ids.add(row["compound_id"])

    if smiles_csv.exists():
        df = pd.read_csv(smiles_csv)
        # Prefer short, named drugs for a readable Atlas UI
        df = df.dropna(subset=["canonical_smiles", "pert_id"])
        df["pert_iname"] = df.get("pert_iname", pd.Series([""] * len(df))).fillna("").astype(str)
        df = df[df["pert_iname"].map(_is_named_drug)]
        df = df.assign(name_len=df["pert_iname"].str.len()).sort_values(
            ["name_len", "pert_iname"], ascending=[True, True]
        )

        for _, row in df.iterrows():
            if len(atlas) >= target_size:
                break
            pert_id = str(row["pert_id"]).strip()
            if pert_id in seen_ids:
                continue
            canonical = _canonical(str(row["canonical_smiles"]))
            if canonical is None or canonical in seen_smiles:
                continue
            atlas.append(
                {
                    "compound_id": pert_id,
                    "compound_name": str(row["pert_iname"]).strip(),
                    "smiles": canonical,
                }
            )
            seen_smiles.add(canonical)
            seen_ids.add(pert_id)
    else:
        log.warning("LINCS SMILES CSV not found at %s — clinical panel only", smiles_csv)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": "compound-atlas-v1",
        "source": str(smiles_csv) if smiles_csv.exists() else "clinical-panel-only",
        "n_compounds": len(atlas),
        "compounds": atlas,
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    log.info("Wrote %d compounds to %s", len(atlas), out_path)
    return atlas


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Build SignalForge compound atlas JSON")
    parser.add_argument("--smiles-csv", type=Path, default=_DEFAULT_SMILES)
    parser.add_argument("--out", type=Path, default=_DEFAULT_OUT)
    parser.add_argument("--target-size", type=int, default=300)
    args = parser.parse_args()
    build_compound_atlas(smiles_csv=args.smiles_csv, out_path=args.out, target_size=args.target_size)


if __name__ == "__main__":
    main()
