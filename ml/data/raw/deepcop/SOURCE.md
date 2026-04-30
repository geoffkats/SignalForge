# DeepCOP Data Source Manifest

This folder contains the DeepCOP project-hosted data bundle.

- Original repository: https://github.com/godwinwoo/DeepCOP
- Large files hosted on: https://huggingface.co/datasets/geoffkats/signalforge-deepcop

## Downloading the large files (phase1/2 compound fingerprints)

The files `phase1_compounds_morgan_2048.csv` (159 MB), `phase2_compounds_morgan_2048.csv`,
and the `.rar` archives are excluded from git. Download them with:

```bash
pip install huggingface_hub

python - <<'EOF'
from huggingface_hub import hf_hub_download
import shutil, pathlib

dest = pathlib.Path("ml/data/raw/deepcop")
dest.mkdir(parents=True, exist_ok=True)

for filename in [
    "phase1_compounds_morgan_2048.csv",
    "phase2_compounds_morgan_2048.csv",
    "DESeq2results.rar",
    "phase1_compounds_morgan_2048.rar",
    "phase2_compounds_morgan_2048.rar",
]:
    path = hf_hub_download(
        repo_id="geoffkats/signalforge-deepcop",
        filename=filename,
        repo_type="dataset",
        local_dir=str(dest),
    )
    print(f"Downloaded: {path}")
EOF
```

Or use the helper script from the repo root:
```bash
python scripts/upload_to_huggingface.py --username YOUR_HF_USERNAME --token hf_...
```

## Files fetched from DeepCOP

- DESeq2results.rar
- DESeq2results.csv
- LNCAPcorr_cols.csv
- LNCAPdrugs.csv
- Phase1_Cell_Line_Metadata.txt
- Phase2_Cell_Line_Metadata.txt
- go_fingerprints.csv
- inhouse_morgan_2048.csv
- landmark_genes.json
- phase1_compounds_morgan_2048.rar
- phase1_compounds_morgan_2048.csv
- phase2_compounds_morgan_2048.rar
- phase2_compounds_morgan_2048.csv

## Extraction notes

The original DeepCOP repository stores some larger files as `.rar` archives. Those archives were downloaded and extracted locally into this folder.

## External LINCS dependencies not fetched here

The original DeepCOP README also requires GEO LINCS files that are not hosted directly inside the DeepCOP repo:

- Phase 1 GEO accession: https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE92742
- Phase 2 GEO accession: https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE70138

The DeepCOP README references these files specifically:

- GSE92742_Broad_LINCS_Level5_COMPZ.MODZ_n473647x12328.gctx.gz
- GSE92742_Broad_LINCS_sig_info.txt.gz
- GSE70138_Broad_LINCS_Level5_COMPZ_n118050x12328_2017-03-06.gctx.gz
- GSE70138_Broad_LINCS_sig_info_2017-03-06.txt.gz

Those GEO payloads are substantially larger and were not automatically downloaded as part of this fetch.
