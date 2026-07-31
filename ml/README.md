# SignalForge ML Pipeline

Production-ready ML pipeline for predicting compound-to-gene transcriptomic regulation.
Trained on LNCaP androgen receptor program data from the **DeepCOP** study (PMID 31504186),
with Phase 3 dual-encoder training on full LINCS multicell profiles.

## Architecture

```
data/raw/deepcop/                 ← DESeq2 + GO-term fingerprints (978 × 1107)
data/processed/lincs_smiles.csv   ← LINCS compound SMILES library
      ↓
signalforge_ml/features.py        ← Morgan-2048 (RDKit) + GO gene vectors
signalforge_ml/training.py        ← baseline RandomForest (LNCAPcorr bits)
signalforge_ml/train_deep.py      ← SignalForgeNet dual-encoder (optional)
signalforge_ml/build_atlas.py     ← curated ~300-compound reverse-signature atlas
      ↓
artifacts/models/baseline.joblib  ← served by default (Docker / production)
artifacts/models/deep_dual_encoder.pt
artifacts/manifests/latest.json
artifacts/libraries/compound_atlas.json
      ↓
signalforge_ml/inference.py       ← SignalForgeModel (RF) + validate_smiles
signalforge_ml/inference_deep.py  ← SignalForgeDeepModel (.pt, optional / local)
```

## Large data files

`phase1_compounds_morgan_2048.csv` (159 MB) and `phase2_compounds_morgan_2048.csv` (14 MB) are **not committed to git**. Download them from HuggingFace:

```python
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id="Geoffkats/signalforge-deepcop",
    repo_type="dataset",
    local_dir="data/raw/deepcop",
)
```

Huge LINCS Level 5 `.gctx` / `.gctx.gz` files are gitignored — use `scripts/download_lincs_level5.py`.

## Data sources

| Source | File | Description |
|---|---|---|
| DeepCOP (PMID 31504186) | `DESeq2results.csv` | LNCaP DESeq2 fold-change for Enzalutamide |
| LINCS L1000 | `go_fingerprints.csv` | 978 landmark genes × 1107 GO-term binary matrix |
| DeepCOP | `phase1/2_compounds_morgan_2048.csv` | Pre-computed Morgan fingerprints |
| LINCS pert_info | `lincs_smiles.csv` | Compound IDs + SMILES for atlas building |

## Current model performance

| Artifact | Accuracy | Macro F1 |
|---|---|---|
| `baseline.joblib` (RF, LNCaP) | ~0.71 | ~0.71 |
| `deep_dual_encoder.pt` (full LINCS) | 0.8736 | 0.8733 |

## Setup

```bash
cd ml
pip install -e ".[dev]"
```

For backend serving only (no torch):

```bash
pip install -e ".[inference]"
```

## Train + atlas

```bash
signalforge-ml train --config configs/baseline.yaml
python -m signalforge_ml.build_atlas
```

Optional deep trainer:

```bash
python -m signalforge_ml.train_deep configs/deep_lincs.yaml
```

## Test

```bash
pytest tests/ -v
```

## Phase status

- [x] Wire trained model into backend predictor
- [x] Curated compound atlas for reverse-signature search
- [x] RDKit SMILES validation + inference provenance
- [x] Full LINCS Phase 1/2 dual-encoder path
- [ ] Multi-task GNN chemical encoder (AttentiveFP via DeepChem)
- [ ] DepMap CRISPR essential gene integration
- [ ] Replace gene hash fallback with ESM-2 protein embeddings for OOV genes
