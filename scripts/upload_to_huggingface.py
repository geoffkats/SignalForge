"""
Upload the SignalForge / DeepCOP large raw data files to Hugging Face Datasets.

Usage
-----
1. Install the client (already in the backend venv):
       pip install huggingface_hub

2. Run this script:
       python scripts/upload_to_huggingface.py --username YOUR_HF_USERNAME --token hf_...

   Or set the token via environment variable and omit --token:
       $env:HF_TOKEN = "hf_..."
       python scripts/upload_to_huggingface.py --username YOUR_HF_USERNAME

After upload the dataset is at:
   https://huggingface.co/datasets/YOUR_HF_USERNAME/signalforge-deepcop
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
DATA_DIR = REPO_ROOT / "ml" / "data" / "raw" / "deepcop"

# Files that are too large for GitHub but belong on HuggingFace
LARGE_FILES = [
    "phase1_compounds_morgan_2048.csv",
    "phase2_compounds_morgan_2048.csv",
    "DESeq2results.rar",
    "phase1_compounds_morgan_2048.rar",
    "phase2_compounds_morgan_2048.rar",
]

DATASET_NAME = "signalforge-deepcop"
CARD_CONTENT = """\
---
license: cc-by-4.0
task_categories:
  - tabular-classification
language:
  - en
tags:
  - biology
  - genomics
  - drug-discovery
  - transcriptomics
  - lincs
  - deepcop
pretty_name: SignalForge / DeepCOP LNCaP Compound Fingerprints
size_categories:
  - 100K<n<1M
---

# SignalForge / DeepCOP LNCaP Dataset

Companion data for the [SignalForge](https://github.com/geoffkats/SignalForge)
translational analytics platform.

Sourced from the [DeepCOP](https://github.com/godwinwoo/DeepCOP) project
(Moo *et al.*, 2019 — PMID 31504186).

## Files

| File | Description |
|---|---|
| `phase1_compounds_morgan_2048.csv` | LINCS Phase 1 compound Morgan-2048 fingerprints (159 MB) |
| `phase2_compounds_morgan_2048.csv` | LINCS Phase 2 compound Morgan-2048 fingerprints (14 MB) |
| `DESeq2results.rar` | LNCaP DESeq2 differential expression results archive |
| `phase1_compounds_morgan_2048.rar` | Phase 1 fingerprints archive |
| `phase2_compounds_morgan_2048.rar` | Phase 2 fingerprints archive |

## Download in Python

```python
from huggingface_hub import hf_hub_download

path = hf_hub_download(
    repo_id="YOUR_HF_USERNAME/signalforge-deepcop",
    filename="phase1_compounds_morgan_2048.csv",
    repo_type="dataset",
    local_dir="ml/data/raw/deepcop",
)
```

## Citation

```bibtex
@article{moo2019deepcop,
  title={DeepCOP: Deep Learning-Based Approach to Predict Gene Regulating Effects
         of Small Molecules},
  author={Moo, Kang and others},
  journal={Bioinformatics},
  year={2019},
  doi={10.1093/bioinformatics/btz749}
}
```
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload large DeepCOP files to Hugging Face Datasets")
    parser.add_argument("--username", required=True, help="Your Hugging Face username")
    parser.add_argument("--token", default=os.environ.get("HF_TOKEN"), help="HF write token (or set HF_TOKEN env var)")
    args = parser.parse_args()

    if not args.token:
        parser.error("Provide --token or set the HF_TOKEN environment variable")

    try:
        from huggingface_hub import HfApi
    except ImportError:
        raise SystemExit("huggingface_hub not installed. Run: pip install huggingface_hub")

    api = HfApi(token=args.token)
    repo_id = f"{args.username}/{DATASET_NAME}"

    print(f"Creating dataset repo: {repo_id}")
    api.create_repo(repo_id=repo_id, repo_type="dataset", exist_ok=True, private=False)

    # Upload dataset card
    api.upload_file(
        repo_id=repo_id,
        repo_type="dataset",
        path_or_fileobj=CARD_CONTENT.encode(),
        path_in_repo="README.md",
    )
    print("Uploaded README.md (dataset card)")

    # Upload each large file
    for filename in LARGE_FILES:
        local_path = DATA_DIR / filename
        if not local_path.exists():
            print(f"  SKIP (not found): {filename}")
            continue
        size_mb = local_path.stat().st_size / (1024 ** 2)
        print(f"  Uploading {filename} ({size_mb:.1f} MB) ...")
        api.upload_file(
            repo_id=repo_id,
            repo_type="dataset",
            path_or_fileobj=str(local_path),
            path_in_repo=filename,
        )
        print(f"  Done: {filename}")

    print(f"\nDataset live at: https://huggingface.co/datasets/{repo_id}")
    print("\nAdd this to ml/data/raw/deepcop/SOURCE.md download instructions.")


if __name__ == "__main__":
    main()
