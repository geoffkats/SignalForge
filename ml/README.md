# SignalForge ML Pipeline

Production-ready ML pipeline for predicting compound-to-gene transcriptomic regulation.
Trained on LNCaP androgen receptor program data from the **DeepCOP** study (PMID 31504186).

## Architecture

```
data/raw/deepcop/          ← DESeq2 results + LINCS L1000 GO-term fingerprints (978 genes × 1107 GO terms)
      ↓
signalforge_ml/ingest_lincs.py   ← schema validation + checksum guard
      ↓
signalforge_ml/features.py       ← Morgan-2048 (RDKit) + GO-term gene vectors (hash fallback for OOV genes)
      ↓
signalforge_ml/training.py       ← scikit-learn LogisticRegression (class_weight=balanced)
      ↓
artifacts/models/baseline.joblib ← serialised model
artifacts/manifests/latest.json  ← metrics + provenance manifest
      ↓
signalforge_ml/inference.py      ← SignalForgeModel — online per-gene scoring + reversal scoring
```

## Large data files

`phase1_compounds_morgan_2048.csv` (159 MB) and `phase2_compounds_morgan_2048.csv` (14 MB) are **not committed to git**. Download them from HuggingFace:

```python
from huggingface_hub import hf_hub_download, snapshot_download
snapshot_download(
    repo_id="Geoffkats/signalforge-deepcop",
    repo_type="dataset",
    local_dir="data/raw/deepcop",
)
```

Or see `data/raw/deepcop/SOURCE.md` for per-file download snippets.

## Data sources

| Source | File | Description |
|---|---|---|
| DeepCOP (PMID 31504186) | `DESeq2results.csv` | LNCaP DESeq2 fold-change for Enzalutamide |
| LINCS L1000 | `go_fingerprints.csv` | 978 landmark genes × 1107 GO-term binary matrix |
| DeepCOP | `phase1/2_compounds_morgan_2048.csv` | Pre-computed Morgan fingerprints |

## Current model performance

| Metric | Value |
|---|---|
| Accuracy | 0.51 |
| Macro F1 | 0.51 |
| Down-class recall | 0.50 |
| Up-class recall | 0.53 |
| Training compound | Enzalutamide (LNCaP) |

> Model trained on a single compound. Performance improves substantially with multi-compound LINCS data.

## Setup

```bash
cd ml
pip install -e ".[dev]"
```

## Retrain

```bash
signalforge-ml train --config configs/baseline.yaml
```

## Test

```bash
pytest tests/ -v
```

## Roadmap

- [ ] Wire trained model into backend predictor (`backend/app/services/predictor.py`)
- [ ] Add VPC compound SMILES to expand training beyond single Enzalutamide compound
- [ ] Integrate full LINCS Phase 1 (GSE92742) + Phase 2 (GSE70138) compound profiles
- [ ] Multi-task GNN chemical encoder (AttentiveFP via DeepChem)
- [ ] Batch correction with ComBat-seq for cross-cell-line generalisation
- [ ] DepMap CRISPR essential gene integration
- [ ] Replace gene hash fallback with ESM-2 protein embeddings for OOV genes
