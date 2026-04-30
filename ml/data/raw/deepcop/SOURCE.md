# DeepCOP Data Source Manifest

This folder contains the DeepCOP project-hosted data bundle fetched from the public GitHub repository:

- Repository: https://github.com/godwinwoo/DeepCOP
- Data directory: https://github.com/godwinwoo/DeepCOP/tree/master/Data

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
