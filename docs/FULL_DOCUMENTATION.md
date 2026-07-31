# SignalForge — Complete Technical Documentation

> Molecule-to-transcriptome intelligence platform.  
> Built from the DeepCOP paper (PMID 31504186 · Bioinformatics 2020 36(3):813-818).
>
> **GitHub:** https://github.com/geoffkats/SignalForge  
> **Large data files:** https://huggingface.co/datasets/Geoffkats/signalforge-deepcop

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Current Phase Status](#2-current-phase-status)
3. [Scientific Foundation — DeepCOP Paper](#3-scientific-foundation--deepcop-paper)
4. [Repository Structure](#4-repository-structure)
5. [ML Pipeline (signalforge_ml)](#5-ml-pipeline-signalforge_ml)
   - 4.1 [Data Ingestion — prepare_deepcop.py](#41-data-ingestion--prepare_deepcopypy)
   - 4.2 [Dataset Schema — ingest_lincs.py](#42-dataset-schema--ingest_lincspy)
   - 4.3 [Feature Engineering — features.py](#43-feature-engineering--featurespy)
   - 4.4 [Training — training.py](#44-training--trainingpy)
   - 4.5 [Inference — inference.py](#45-inference--inferencepy)
   - 4.6 [Security — ml/security.py](#46-security--mlsecuritypy)
   - 4.7 [CLI — cli.py](#47-cli--clipy)
   - 4.8 [Config — configs/baseline.yaml](#48-config--configsbaselineyaml)
   - 4.9 [Schemas — schemas.py](#49-schemas--schemaspy)
   - 4.10 [Training Results](#410-training-results)
6. [Backend API (FastAPI)](#6-backend-api-fastapi)
   - 5.1 [Application Factory — main.py](#51-application-factory--mainpy)
   - 5.2 [Configuration — config.py](#52-configuration--configpy)
   - 5.3 [Security Middleware — security.py](#53-security-middleware--securitypy)
   - 5.4 [Pydantic Models — models.py](#54-pydantic-models--modelspy)
   - 5.5 [API Routes — api/routes.py](#55-api-routes--apiroutespy)
   - 5.6 [Predictor Service — services/predictor.py](#56-predictor-service--servicespredictorpy)
   - 5.7 [Audit Service — services/audit.py](#57-audit-service--servicesauditpy)
7. [Frontend (React + Vite)](#7-frontend-react--vite)
   - 6.1 [API Client — lib/api.ts](#61-api-client--libapiits)
   - 6.2 [TypeScript Types — types.ts](#62-typescript-types--typests)
   - 6.3 [Main Component — App.tsx](#63-main-component--apptsx)
8. [Data Assets](#8-data-assets)
9. [Security Architecture](#9-security-architecture)
10. [Environment Variables](#9-environment-variables)
11. [Quick-Start — Running Everything](#10-quick-start--running-everything)
12. [Known Limitations and Upgrade Path](#11-known-limitations-and-upgrade-path)
13. [Containerized Deployment](#12-containerized-deployment)
14. [Operational Incident Log](#13-operational-incident-log)

---

## 1. Project Overview

SignalForge lets a researcher:

- Paste a **SMILES** string for any small molecule.
- Select one or more **gene symbols** (e.g., `AR`, `KLK3`, `TMPRSS2`).
- Receive a prediction of whether the compound is likely to **up-regulate** or **down-regulate** each gene.
- Perform a **reverse signature search** — given a set of up/down genes that characterise a disease state, find compounds predicted to counteract that programme.

The platform is built as a production-grade monorepo with security controls, an audit trail, and a real ML training pipeline trained on LNCaP prostate cancer RNAseq data from the DeepCOP dataset.

---

## 2. Current Phase Status

| Phase | Status | What Was Added |
|---|---|---|
| Phase 1 | Completed | Baseline data ingestion and logistic classification pipeline |
| Phase 2 | Completed | Multi-drug training, RF baseline improvements, weighted samples |
| Phase 3 | Completed | Full dual-encoder deep model (`train_deep.py`) on full LINCS multicell parquet |
| Phase 4 | Completed | Real model serving, curated compound atlas, SMILES validation, provenance |

### Recent model outcomes

- Full dual-encoder test accuracy: **0.8736**
- Full dual-encoder macro F1: **0.8733**
- Promotion threshold check: passed (`min_accuracy=0.85`, `min_macro_f1=0.84`)

### Recent trainer hardening

- Config-relative path resolution for stable execution from any working directory
- Memory-safe two-pass feature matrix build for large full-data runs
- Index-based train/val/test loading (avoid split-array duplication)
- Optional scaler disabled by default for full-data CPU stability

---

## 3. Scientific Foundation — DeepCOP Paper

**Citation:** Woo G, et al. "DeepCOP: deep learning-based approach to predict gene regulating effects of small molecules." *Bioinformatics* 2020;36(3):813-818. PMID 31504186.

### Core Idea

| Input | Representation |
|---|---|
| Small molecule | Morgan fingerprint (radius 2, 2048 bits) |
| Gene | Gene Ontology (GO) term binary vector |

The model predicts **direction** (up / down) of gene expression change when a compound perturbs a cell.

### Training Data Source

- **LINCS L1000** programme (NIH): ~500,000 perturbation profiles measuring the 978 "landmark" gene expression levels after compound treatment.
- Two phases: Phase 1 (GSE92742) and Phase 2 (GSE70138), together ~590,000 unique perturbation signatures.
- SignalForge uses a subset: the LNCaP prostate cancer RNAseq DESeq2 results from the DeepCOP GitHub repository.

### Data Files Downloaded (ml/data/raw/deepcop/)

| File | Contents |
|---|---|
| `phase1_compounds_morgan_2048.csv` | ~20,000 Phase 1 compound IDs + pre-computed 2048-bit Morgan fingerprints |
| `phase2_compounds_morgan_2048.csv` | Phase 2 compound fingerprints, same format |
| `go_fingerprints.csv` | 978 landmark gene symbols × GO-term binary matrix |
| `landmark_genes.json` | NCBI/Entrez gene ID ↔ symbol mapping for the 978 landmark genes |
| `DESeq2results.csv` | LNCaP in-house RNAseq: Drug, geneName, log2FoldChange, padj, pvalue |
| `LNCAPdrugs.csv` | Drug names used in LNCaP experiments |
| `Phase1_Cell_Line_Metadata.txt` | Cell line annotations for Phase 1 signatures |
| `Phase2_Cell_Line_Metadata.txt` | Cell line annotations for Phase 2 signatures |
| `SOURCE.md` | Provenance manifest — what was fetched and what still needs GEO |

---

## 4. Repository Structure

```
ai-project/
├── backend/                   FastAPI backend
│   ├── app/
│   │   ├── main.py            Application factory + lifespan + middleware wiring
│   │   ├── config.py          Settings (pydantic-settings, SIGNALFORGE_ env prefix)
│   │   ├── security.py        Middleware: request context, security headers, rate limit
│   │   ├── models.py          Pydantic request / response models
│   │   ├── api/
│   │   │   └── routes.py      GET /healthz, GET /meta, POST /predict/gene-effect,
│   │   │                      POST /search/reverse-signature
│   │   └── services/
│   │       ├── predictor.py   SignalForgePredictor (eager RF/deep load + atlas ranking)
│   │       └── audit.py       AuditRecord dataclass + builder
│   ├── pyproject.toml
│   └── .env.example
│
├── frontend/                  React 19 + Vite 7 + TypeScript
│   ├── src/
│   │   ├── App.tsx            Full UI: predict form, reverse-search form, result panels
│   │   ├── main.tsx           React entry point
│   │   ├── types.ts           TypeScript types mirroring backend Pydantic models
│   │   ├── styles.css         Organic biotech aesthetic (CSS custom properties)
│   │   └── lib/
│   │       └── api.ts         Typed API client (fetch wrapper, env-var config)
│   ├── vite.config.ts
│   ├── package.json
│   └── .env.example
│
├── ml/                        Python ML package + data pipeline
│   ├── signalforge_ml/
│   │   ├── prepare_deepcop.py  DeepCOP → training CSV bridge script
│   │   ├── ingest_lincs.py     CSV ingestion with schema validation + checksum
│   │   ├── features.py         Morgan fingerprints + gene hash embeddings
│   │   ├── training.py         Full train/eval/artifact pipeline
│   │   ├── inference.py        Model manifest loader
│   │   ├── security.py         SHA-256 dataset integrity check
│   │   ├── schemas.py          PerturbationRecord dataclass
│   │   ├── config.py           YAML config loader
│   │   └── cli.py              Typer CLI: `signalforge-ml ingest` / `train`
│   ├── configs/
│   │   └── baseline.yaml       Training configuration
│   ├── data/
│   │   ├── raw/deepcop/        All fetched DeepCOP data files
│   │   └── processed/          Parquet feature store (generated at training time)
│   ├── artifacts/
│   │   ├── models/             Trained model joblib files
│   │   └── manifests/          JSON training manifest (metrics, versions, paths)
│   ├── pyproject.toml
│   └── .venv/                  (git-ignored) Python 3.12 virtual environment
│
└── docs/
    ├── deepcop-project-brief.md
    ├── security-architecture.md
    └── FULL_DOCUMENTATION.md  (this file)
```

---

## 5. ML Pipeline (signalforge_ml)

### 4.1 Data Ingestion — `prepare_deepcop.py`

**Purpose:** Converts raw DeepCOP LNCaP DESeq2 differential expression results into the training CSV schema expected by the rest of the pipeline.

**Location:** `ml/signalforge_ml/prepare_deepcop.py`

**How to run:**
```powershell
cd ml
.\.venv\Scripts\Activate.ps1
python -m signalforge_ml.prepare_deepcop
```

**What it does, step by step:**

| Step | Action |
|---|---|
| 1 | Load `DESeq2results.csv` (137,995 rows: Drug × gene × log2FoldChange × padj) |
| 2 | Drop any drug not in `DRUG_SMILES` dict (warns about missing SMILES) |
| 3 | Apply fold-change threshold: keep only rows where `|log2FC| > 0.5` |
| 4 | Assign `regulation_label`: `"up"` if log2FC > 0, `"down"` if log2FC < 0 |
| 5 | Optionally restrict to 978 landmark genes (`require_landmark=False` by default) |
| 6 | Validate SMILES with RDKit (raises if RDKit rejects a SMILES string) |
| 7 | Build required columns: `perturbation_id`, `compound_id` (MD5 hash), `compound_name`, `smiles`, `gene_symbol`, `regulation_label` |
| 8 | Write `data/raw/deepcop/lncap_training.csv` |

**Output stats (current run):**
- Input rows: 137,995
- After SMILES filter (only Enzalutamide has SMILES): 27,599 rows
- After |log2FC| > 0.5 filter: 7,958 rows
- Label distribution: 4,436 up / 3,522 down
- Written to: `ml/data/raw/deepcop/lncap_training.csv`

**Extending with more drugs:**

To include the 4 VPC research compounds (which boost model utility significantly), add their SMILES to the `DRUG_SMILES` dict at the top of the file:
```python
DRUG_SMILES: dict[str, str] = {
    "Enzalutamide": "CC1(C)C(=O)N(c2ccc(C#N)cc2C(F)(F)F)C(=S)N1c3ccc(C(=O)NC)cc3F",
    "VPC13789":    "<SMILES from publication>",
    "VPC14449":    "<SMILES from publication>",
    "VPC17005":    "<SMILES from publication>",
    "VPC220010":   "<SMILES from publication>",
}
```

**Key parameters:**

| Parameter | Default | Meaning |
|---|---|---|
| `fc_threshold` | `0.5` | Minimum absolute log2 fold-change to call up/down |
| `require_landmark` | `False` | Restrict genes to the 978 L1000 landmark genes |

---

### 4.2 Dataset Schema — `ingest_lincs.py`

**Purpose:** Loads and validates the training CSV, optionally verifying a SHA-256 checksum.

**Function:** `ingest_lincs_csv(input_path, expected_columns, checksum_sha256="")`

**Required CSV columns:**

| Column | Type | Description |
|---|---|---|
| `perturbation_id` | string | Unique ID per (compound, gene, experiment) triple |
| `compound_id` | string | Broad compound ID (BRD-XXXXXXXX format) |
| `compound_name` | string | Human-readable drug name |
| `smiles` | string | SMILES string for the compound |
| `gene_symbol` | string | HGNC gene symbol (e.g., `AR`, `TP53`) |
| `regulation_label` | string | `"up"` or `"down"` |

**Checksum feature:** If `checksum_sha256` is set in `baseline.yaml`, the file's SHA-256 is computed and compared before training. This prevents training on accidentally modified or corrupted data. Set to `""` to skip (default for development).

---

### 4.3 Feature Engineering — `features.py`

**Purpose:** Converts raw compound SMILES and gene symbols into numeric feature vectors suitable for scikit-learn.

#### `smiles_to_morgan(smiles, radius, n_bits)`

Converts a SMILES string to a **Morgan circular fingerprint** (ECFP-style) bit vector.

- Uses RDKit `GetMorganGenerator` (modern API, no deprecation warnings).
- `radius=2` → captures atom environments up to 2 bonds away (equivalent to ECFP4).
- `n_bits=2048` → 2048-dimensional binary vector.
- Returns `np.ndarray[float32]` of shape `(2048,)` with 0.0 / 1.0 values.

**Why Morgan fingerprints?** They are the industry standard for encoding molecular structure as a fixed-length bit vector. Each bit represents the presence of a specific circular substructure around an atom. Two molecules with similar Morgan fingerprints share similar local chemistry.

#### `gene_symbol_to_vector(gene_symbol, width=1107)`

Converts a gene symbol string to a **GO-term binary vector** (or SHA-256 hash fallback for out-of-vocabulary genes).

- Loads `go_fingerprints.csv` once at import time (978 LINCS landmark genes × 1107 GO-term columns).
- If the gene symbol appears in the GO matrix (case-insensitive lookup), returns that row as a `float32` vector of shape `(1107,)`.
- If the gene is **not** in the landmark set, falls back to a length-normalised SHA-256 hash embedding: 32 uint8 bytes → normalised to [0, 1] → `np.resize` to `(1107,)` so shapes are always consistent.
- Returns `np.ndarray[float32]` of shape `(1107,)`.

**Why GO-term vectors?** Each dimension represents the presence of a specific Gene Ontology annotation for that gene, encoding real biological function. The 978 × 1107 matrix comes directly from the DeepCOP repository. The hash fallback ensures the model can still generate a feature vector for novel genes not in the landmark set.

#### `build_feature_table(frame, radius, n_bits)`

Builds the full feature matrix from a DataFrame.

- Stacks all Morgan fingerprints → shape `(N, 2048)`.
- Stacks all GO-term gene vectors → shape `(N, 1107)`.
- Concatenates horizontally → shape `(N, 3155)`.
- Maps `regulation_label` column: `"up" → 1`, `"down" → 0`.
- Returns `(features: np.ndarray, labels: np.ndarray, cleaned_frame: DataFrame)`.

**Final feature vector layout:**

```
[  bit_0, bit_1, ..., bit_2047,  go_0, go_1, ..., go_1106  ]
 |<---------- Morgan 2048 -------->| |<-- GO-term 1107 ------>|
```

Total dimensions: **3,155 per sample.**

---

### 4.4 Training — `training.py`

**Purpose:** End-to-end training pipeline: load data → build features → split → train → evaluate → save artifacts.

**Function:** `train_baseline(config: dict) → dict`

**Pipeline steps:**

```
ingest_lincs_csv()
       ↓
build_feature_table()        → X: (N, 2112)   y: (N,)
       ↓
train_test_split()           → 80% train / 20% test  (stratified)
       ↓
LogisticRegression.fit()     → max_iter=500
       ↓
classification_report()      → per-class precision, recall, F1
       ↓
joblib.dump(model)           → artifacts/models/baseline.joblib
cleaned_frame.to_parquet()   → data/processed/training_table.parquet
       ↓
manifest JSON                → artifacts/manifests/latest.json
```

**Config parameters consumed:**

| Key | Value |
|---|---|
| `dataset.input_path` | Path to training CSV |
| `dataset.processed_path` | Output Parquet path |
| `dataset.expected_columns` | Column schema validation list |
| `dataset.checksum_sha256` | SHA-256 of dataset file (empty = skip) |
| `features.fingerprint_radius` | Morgan fingerprint radius |
| `features.fingerprint_bits` | Morgan fingerprint bit count |
| `training.test_size` | Fraction held out for evaluation |
| `training.random_state` | Seed for reproducibility |
| `training.logistic_max_iter` | Max iterations for LogisticRegression solver |
| `artifacts.model_path` | Where to write `baseline.joblib` |
| `artifacts.manifest_path` | Where to write `latest.json` |

**Output artifact — `artifacts/manifests/latest.json`:**

```json
{
  "model_version": "baseline-rf-v1",
  "algorithm": "Morgan fingerprint (LNCAPcorr-selected bits) + LINCS L1000 GO-term gene fingerprint + random forest",
  "artifact_path": "artifacts/models/baseline.joblib",
  "processed_dataset_path": "data/processed/training_table.parquet",
  "metrics": { ... sklearn classification_report dict ... },
  "status": "trained"
}
```

---

### 4.5 Inference — `inference.py` / `inference_deep.py` / `build_atlas.py`

**Purpose:** Online scoring for the FastAPI backend and reverse-signature atlas.

| Module | Role |
|---|---|
| `inference.py` | `validate_smiles`, `SignalForgeModel` (joblib RF), reversal scoring |
| `inference_deep.py` | `SignalForgeDeepModel` for `.pt` dual-encoder checkpoints (optional; requires torch) |
| `build_atlas.py` | Builds `artifacts/libraries/compound_atlas.json` (~300 named LINCS + clinical AR panel) |

**Backend wiring:** `SignalForgePredictor` eagerly loads the artifact at startup. Paths ending in `.pt` use the deep loader; otherwise joblib RF. `/healthz` and `/meta` expose `inference_mode` (`model` \| `heuristic`) and `atlas_size`.

---

### 4.6 Security — `ml/security.py`

**Purpose:** Dataset integrity verification at training time.

**Functions:**

| Function | Behaviour |
|---|---|
| `sha256_file(path) → str` | Streams file in 8 KB chunks and returns hex SHA-256 digest |
| `verify_checksum(path, expected_checksum)` | Raises `ValueError` if computed hash ≠ expected hash. No-op when `expected_checksum=""` |

**Why this matters:** Biotech ML pipelines can silently produce wrong models if training data is corrupted, swapped, or tampered with. The checksum gate is a lightweight immutable proof that the exact expected dataset was used.

To generate a checksum for a dataset file:
```python
from signalforge_ml.security import sha256_file
print(sha256_file("data/raw/deepcop/lncap_training.csv"))
```
Then paste the result into `baseline.yaml` under `dataset.checksum_sha256`.

---

### 4.7 CLI — `cli.py`

**Entry point:** `signalforge-ml` (installed via `[project.scripts]` in `pyproject.toml`).

**Commands:**

```
signalforge-ml ingest [--config-path PATH]
    Loads and echoes the dataset section of the config.
    Use to verify the path and column schema before training.

signalforge-ml train [--config-path PATH]
    Runs the full train_baseline() pipeline.
    Default config: configs/baseline.yaml
    Output: JSON manifest printed to stdout + saved to artifacts/manifests/latest.json
```

**Example:**
```powershell
cd ml
.\.venv\Scripts\Activate.ps1
signalforge-ml train --config-path configs/baseline.yaml
```

---

### 4.8 Config — `configs/baseline.yaml`

Full annotated config:

```yaml
dataset:
  input_path: data/raw/deepcop/lncap_training.csv   # prepared by prepare_deepcop.py
  processed_path: data/processed/training_table.parquet
  expected_columns:
    - perturbation_id
    - compound_id
    - compound_name
    - smiles
    - gene_symbol
    - regulation_label
  checksum_sha256: ""                               # set to SHA-256 hex to lock dataset

features:
  fingerprint_radius: 2                             # ECFP4 equivalent
  fingerprint_bits: 2048
  gene_vector_strategy: go_fingerprint               # uses GO-term matrix; falls back to hash for OOV genes

training:
  test_size: 0.2
  random_state: 42
  logistic_max_iter: 500

artifacts:
  model_path: artifacts/models/baseline.joblib
  manifest_path: artifacts/manifests/latest.json
```

---

### 4.9 Schemas — `schemas.py`

Defines the internal data record dataclass used for type-safe data handling within the ML package:

```python
@dataclass(slots=True)
class PerturbationRecord:
    perturbation_id: str
    compound_id: str
    compound_name: str
    smiles: str
    gene_symbol: str
    regulation_label: str   # "up" | "down"
```

---

### 4.10 Training Results

Trained on: LNCaP RNAseq DESeq2 data — Enzalutamide vs. control, |log2FC| > 0.5 threshold.

| Metric | Value |
|---|---|
| Training samples | 6,366 (80% of 7,958) |
| Test samples | 1,592 (20% of 7,958) |
| Features per sample | 3,155 (2048 Morgan + 1107 GO-term gene vector) |
| Algorithm | Logistic Regression (L2, max_iter=500) |
| Overall accuracy | 55.3% |
| Up-regulation recall | 94.9% |
| Down-regulation recall | 5.4% |
| Model file size | ~17 KB |

**Interpretation:** The model is above chance but shows strong class imbalance in predictions — it almost always predicts "up". This is expected because all 7,958 samples have the *same* compound (Enzalutamide), meaning the Morgan fingerprint is constant across all rows. The model differentiates between genes via their GO-term vectors, but without compound variation the structural signal is limited. Performance will improve dramatically once multi-compound LINCS data is added.

---

## 5. Backend API (FastAPI)

### 5.1 Application Factory — `main.py`

**How the app is constructed:**

```python
create_app()
  ├─ lifespan()                        # startup: initialise SignalForgePredictor
  ├─ RequestContextMiddleware          # UUID + timing on every request
  ├─ SecurityHeadersMiddleware         # 6 security response headers
  ├─ InMemoryRateLimitMiddleware       # sliding-window per IP+key
  ├─ CORSMiddleware                    # allows only listed origins
  └─ router                            # all route handlers
```

The app uses **FastAPI lifespan** (not deprecated startup events) to initialise the predictor once at startup and attach it to `app.state.predictor`. Route handlers access it via `request.app.state.predictor`.

**To run:**
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
uvicorn app.main:app --reload --port 8000
```

---

### 5.2 Configuration — `config.py`

All configuration comes from **environment variables** with the `SIGNALFORGE_` prefix (using pydantic-settings).

| Env Variable | Default | Purpose |
|---|---|---|
| `SIGNALFORGE_APP_NAME` | `"SignalForge API"` | Title shown in OpenAPI docs |
| `SIGNALFORGE_ENVIRONMENT` | `"development"` | Passed through to health response |
| `SIGNALFORGE_ALLOWED_ORIGINS` | `["http://localhost:5173"]` | CORS allowed origins |
| `SIGNALFORGE_API_KEYS` | `[]` (no auth) | List of valid API keys. Empty = authentication disabled |
| `SIGNALFORGE_REQUESTS_PER_MINUTE` | `60` | Sliding-window rate limit per client IP + key |
| `SIGNALFORGE_MAX_GENES_PER_REQUEST` | `64` | Hard cap on genes per `/predict/gene-effect` call |
| `SIGNALFORGE_MAX_SIGNATURE_GENES` | `256` | Hard cap on total genes in a reverse-signature query |
| `SIGNALFORGE_MODEL_VERSION` | `"baseline-rf-v1"` | Version string echoed in responses |
| `SIGNALFORGE_MODEL_MANIFEST_PATH` | `ml/artifacts/manifests/latest.json` | Active training manifest |
| `SIGNALFORGE_MODEL_ARTIFACT_PATH` | `ml/artifacts/models/baseline.joblib` | Joblib RF (or `.pt` for optional deep) |
| `SIGNALFORGE_COMPOUND_ATLAS_PATH` | `ml/artifacts/libraries/compound_atlas.json` | Curated reverse-signature library |

Settings are loaded once and cached with `@lru_cache` — changing env vars requires a server restart.

Copy `.env.example` to `.env` and fill in values for production.

---

### 5.3 Security Middleware — `security.py`

#### `RequestContextMiddleware`

Runs on every request, before any route handler.

- Generates a UUID v4 → stored as `request.state.request_id`.
- Records start time → stored as `request.state.started_at`.
- Injects into response headers:
  - `X-Request-ID: <uuid>` — for log correlation and client-side tracing.
  - `X-Process-Time-Ms: <float>` — server-side processing latency.

#### `SecurityHeadersMiddleware`

Injects 5 hardening headers on every response:

| Header | Value | Purpose |
|---|---|---|
| `X-Content-Type-Options` | `nosniff` | Prevents MIME-type sniffing |
| `X-Frame-Options` | `DENY` | Blocks clickjacking via iframes |
| `Referrer-Policy` | `same-origin` | Controls referrer leakage |
| `Permissions-Policy` | `geolocation=(), microphone=(), camera=()` | Restricts browser APIs |
| `Cache-Control` | `no-store` | Prevents sensitive biotech query data from being cached |

#### `InMemoryRateLimitMiddleware`

Implements a **sliding-window** counter per client `IP:API_key` pair.

- Uses a `deque` per key, storing timestamps of recent requests.
- On each request: evict timestamps older than 60 seconds, then check if count ≥ limit.
- Returns **HTTP 429** if limit exceeded.
- Configured via `SIGNALFORGE_REQUESTS_PER_MINUTE` (default: 60).

**Limitation:** In-memory only — does not survive server restarts or scale across multiple backend instances. Use Redis-based rate limiting (e.g., `fastapi-limiter`) for production multi-replica deployments.

#### `require_api_key()`

FastAPI dependency injected on protected routes.

- Reads the `X-API-Key` request header.
- If `SIGNALFORGE_API_KEYS` is empty, authentication is **disabled** (dev mode).
- If non-empty, the key must appear in the list. Returns **HTTP 401** otherwise.

#### `enforce_biotech_query_policy()`

Called at the start of each prediction route handler.

- Enforces `SIGNALFORGE_MAX_GENES_PER_REQUEST` (default 64 genes).
- Enforces `SIGNALFORGE_MAX_SIGNATURE_GENES` (default 256 total genes in a signature query).
- Sets `request.state.query_classification = "research-use-only"`.
- Returns **HTTP 422** if limits are exceeded.

---

### 5.4 Pydantic Models — `models.py`

All request/response models use Pydantic v2 with strict validation.

#### Request Models

**`GeneEffectRequest`**
```
smiles        str      1-512 chars — SMILES string for the compound
genes         list[str]  1-64 items — gene symbols to query
context       str|None   optional — free-text annotation (max 128 chars)
```
Validator: `normalize_genes` strips whitespace and uppercases all symbols, drops empty strings.

**`ReverseSignatureRequest`**
```
up_genes      list[str]  0-256 items — genes known to be over-expressed in disease state
down_genes    list[str]  0-256 items — genes known to be under-expressed in disease state
top_k         int        1-50 — number of compounds to return (default 10)
```

#### Response Models

**`GeneEffectPrediction`** (per gene)
```
gene              str     Gene symbol
direction         enum    "up" | "down" | "neutral"
up_probability    float   Probability of up-regulation [0, 1]
down_probability  float   Probability of down-regulation [0, 1]
confidence        float   max(up_prob, down_prob)
rationale         str     Human-readable explanation text
```

**`GeneEffectResponse`**
```
model_version     str                    Version string from settings
predictions       list[GeneEffectPrediction]
audit_id          str                    UUID from RequestContextMiddleware
```

**`RankedCompound`**
```
compound_id       str     Broad compound ID
compound_name     str     Human-readable name
smiles            str     SMILES string
reversal_score    float   [0, 1] — how well compound reverses the query signature
explanation       str     Human-readable rationale
```

**`ReverseSignatureResponse`**
```
model_version     str
results           list[RankedCompound]   sorted descending by reversal_score
audit_id          str
```

**`HealthResponse`**
```
status            str     "ok"
model_version     str
environment       str
```

**`MetaResponse`**
```
app_name          str
model_version     str
security_modes    list[str]
pipeline_stages   list[str]
```

---

### 5.5 API Routes — `api/routes.py`

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/healthz` | None | Returns status, model version, environment |
| `GET` | `/meta` | None | Returns app metadata, security modes, pipeline stages |
| `POST` | `/predict/gene-effect` | API key | Predicts up/down regulation for each gene given a compound SMILES |
| `POST` | `/search/reverse-signature` | API key | Ranks compounds that may reverse a disease gene-expression signature |

Interactive API docs (Swagger UI) available at `http://localhost:8000/docs` when running in development.

---

### 5.6 Predictor Service — `services/predictor.py`

**Current status: Phase 4 complete.** The predictor eagerly loads `baseline.joblib` (or a `.pt` dual-encoder checkpoint when configured) at startup, validates SMILES with RDKit, and ranks a curated compound atlas for reverse-signature search. A deterministic hash heuristic remains only as fallback when the artifact cannot be loaded (`inference_mode=heuristic`).

**`SignalForgePredictor`**

Initialised with `model_version`, manifest path, artifact path, and compound atlas path. Exposes `inference_mode` and `atlas_size` for `/healthz` and `/meta`.

**`predict_gene_effects(smiles, genes)`**

1. Canonicalises SMILES via RDKit (`ValueError` → HTTP 422).
2. Builds Morgan (+ LNCAPcorr selection for RF) and GO gene vectors via `signalforge_ml`.
3. Returns per-gene up/down/neutral scores from the loaded model.
4. Falls back to the hash heuristic only when no model is loaded.

**`reverse_signature_search(up_genes, down_genes, top_k)`**

Scores the curated atlas (`compound_atlas.json`, ~300 compounds including the clinical AR panel), optionally reusing precomputed compound feature vectors, and returns the top_k reversal candidates.

---

### 5.7 Audit Service — `services/audit.py`

**`AuditRecord`** dataclass:
```
audit_id              str   UUID (reused from request context)
event_type            str   e.g. "predict.gene_effect", "search.reverse_signature"
created_at            str   UTC ISO 8601 timestamp
query_classification  str   "research-use-only" (set by biotech policy enforcer)
```

**`build_audit_record(audit_id, event_type, query_classification)`**

Creates and returns an `AuditRecord`. Currently in-memory only. Upgrade path: write to a PostgreSQL `audit_log` table or ship to a structured log sink (e.g., Datadog, Cloud Logging).

---

## 6. Frontend (React + Vite)

### 6.1 API Client — `lib/api.ts`

Typed fetch wrapper. Reads two environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000` | Backend base URL |
| `VITE_SIGNALFORGE_API_KEY` | `""` | API key sent as `X-API-Key` header (omitted if empty) |

**Exported functions:**

```typescript
fetchMeta(): Promise<MetaResponse>
  // GET /meta — called on mount to populate platform posture panel

predictGeneEffects(smiles: string, genes: string[]): Promise<GeneEffectResponse>
  // POST /predict/gene-effect

searchReverseSignature(upGenes: string[], downGenes: string[]): Promise<ReverseSignatureResponse>
  // POST /search/reverse-signature  (top_k=5 hardcoded)
```

All functions throw `Error` on non-2xx HTTP status.

---

### 6.2 TypeScript Types — `types.ts`

Mirrors the backend Pydantic models exactly. Key types:

```typescript
GeneEffectPrediction   { gene, direction, up_probability, down_probability, confidence, rationale }
GeneEffectResponse     { model_version, predictions, audit_id }
RankedCompound         { compound_id, compound_name, smiles, reversal_score, explanation }
ReverseSignatureResponse { model_version, results, audit_id }
MetaResponse           { app_name, model_version, security_modes, pipeline_stages }
```

---

### 6.3 Main Component — `App.tsx`

Single-page application with three main sections:

**Platform posture panel** (top right of hero)  
Live-fetches `/meta` on mount. Displays security modes and pipeline stages as tags. Falls back to defaults if the backend is unavailable.

**Gene Effect Predict form**  
- Input: SMILES string, comma/space-separated gene list.
- Submits to `POST /predict/gene-effect`.
- Default SMILES: Enzalutamide. Default genes: `AR, KLK3, TMPRSS2, FOXA1`.
- Results: table of gene → direction → up prob → down prob → confidence.

**Reverse Signature Search form**  
- Input: up-regulated genes, down-regulated genes.
- Submits to `POST /search/reverse-signature`.
- Default: up `MYC, E2F1`, down `TP53, CDKN1A`.
- Results: ranked compound cards with reversal score.

**To run:**
```powershell
cd frontend
npm install
cp .env.example .env        # fill in VITE_API_BASE_URL and VITE_SIGNALFORGE_API_KEY
npm run dev                 # starts on http://localhost:5173
```

---

## 7. Data Assets

### Training Data Provenance

All raw data lives under `ml/data/raw/deepcop/`. Nothing in that folder should be modified manually — always regenerate via `prepare_deepcop.py`.

The two large Morgan fingerprint CSVs and the RAR archives are **not committed to git**. Download them from HuggingFace:

```python
from huggingface_hub import hf_hub_download
hf_hub_download(repo_id="Geoffkats/signalforge-deepcop", repo_type="dataset",
                filename="phase1_compounds_morgan_2048.csv",
                local_dir="ml/data/raw/deepcop")
```

| File | Origin | Size | Used for | Location |
|---|---|---|---|---|
| `DESeq2results.csv` | DeepCOP GitHub repo | ~11 MB | Primary training label source | git-tracked |
| `go_fingerprints.csv` | DeepCOP GitHub repo | ~4 MB | Gene GO-term feature matrix (978 genes × 1107 GO terms) | git-tracked |
| `landmark_genes.json` | DeepCOP GitHub repo | ~60 KB | Entrez ID ↔ gene symbol mapping | git-tracked |
| `phase1_compounds_morgan_2048.csv` | DeepCOP GitHub repo | ~159 MB | Pre-computed fingerprints for LINCS Phase 1 compounds | **HuggingFace** |
| `phase2_compounds_morgan_2048.csv` | DeepCOP GitHub repo | ~14 MB | Phase 2 compound fingerprints | **HuggingFace** |
| `LNCAPdrugs.csv` | DeepCOP GitHub repo | ~200 B | Drug list for LNCaP experiments | git-tracked |
| `Phase1_Cell_Line_Metadata.txt` | DeepCOP GitHub repo | ~4 KB | Cell line annotations | git-tracked |
| `Phase2_Cell_Line_Metadata.txt` | DeepCOP GitHub repo | ~4 KB | Cell line annotations | git-tracked |
| `lncap_training.csv` | Generated by `prepare_deepcop.py` | ~500 KB | Actual training input | generated |

### Processed Data

| File | Description |
|---|---|
| `ml/data/processed/training_table.parquet` | Parquet snapshot of the cleaned training DataFrame (generated during `signalforge-ml train`) |

### Model Artifacts

| File | Description |
|---|---|
| `ml/artifacts/models/baseline.joblib` | Serialised `sklearn.LogisticRegression` model (~17 KB) |
| `ml/artifacts/manifests/latest.json` | Training manifest with metrics, version, and artifact paths |

Both are listed in `.gitignore` and should be stored separately (e.g., S3, GCS, DVC, or reproduced locally by running `signalforge-ml train`) for team workflows.

---

## 8. Security Architecture

### Defence-in-Depth Layers

```
Client request
    │
    ▼
[1] CORS enforcement         Only listed origins pass
    │
    ▼
[2] Rate limiting            60 req/min per IP:key sliding window
    │
    ▼
[3] API key validation       X-API-Key header check (optional in dev)
    │
    ▼
[4] Biotech query policy     Gene count caps; query classification
    │
    ▼
[5] Pydantic validation      Input length bounds, type coercion
    │
    ▼
[6] Route handler            Business logic
    │
    ▼
[7] Audit record             UUID, event type, timestamp, classification
    │
    ▼
Response
    │
    ▼
[8] Security headers         nosniff, DENY frames, no-store, permissions
    │
    ▼
[9] Request ID + timing      X-Request-ID, X-Process-Time-Ms
```

### Data Integrity (ML pipeline)

```
Dataset file
    │
    ▼
[1] SHA-256 checksum gate    Refuse training if hash mismatches
    │
    ▼
[2] Schema validation        Refuse if required columns are absent
    │
    ▼
[3] RDKit SMILES check       Refuse if SMILES cannot be parsed
    │
    ▼
Training run
```

### Upgrade Path for Production

| Feature | Current | Production Upgrade |
|---|---|---|
| Rate limiting | In-memory deque | Redis + `fastapi-limiter` |
| API keys | Plain string list in env | Hashed keys in database, key rotation |
| Audit log | In-memory dataclass | Write to PostgreSQL `audit_log` table |
| Dataset integrity | SHA-256 checksum | Signed manifests (cosign or SLSA) |
| CORS | Origin whitelist | Review per deployment |
| Role-based access | Not implemented | OAuth2 + scopes per route |

---

## 9. Environment Variables

### Backend (`backend/.env`)

```
SIGNALFORGE_APP_NAME=SignalForge API
SIGNALFORGE_ENVIRONMENT=development
SIGNALFORGE_ALLOWED_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]
SIGNALFORGE_API_KEYS=["your-key-here"]
SIGNALFORGE_REQUESTS_PER_MINUTE=60
SIGNALFORGE_MAX_GENES_PER_REQUEST=64
SIGNALFORGE_MAX_SIGNATURE_GENES=256
SIGNALFORGE_MODEL_VERSION=baseline-rf-v1
SIGNALFORGE_MODEL_MANIFEST_PATH=../ml/artifacts/manifests/latest.json
SIGNALFORGE_MODEL_ARTIFACT_PATH=../ml/artifacts/models/baseline.joblib
SIGNALFORGE_COMPOUND_ATLAS_PATH=../ml/artifacts/libraries/compound_atlas.json
```

Copy `backend/.env.example` to `backend/.env` and fill in values.

### Frontend (`frontend/.env`)

```
VITE_API_BASE_URL=http://localhost:8000
VITE_SIGNALFORGE_API_KEY=your-key-here
```

Copy `frontend/.env.example` to `frontend/.env`.

---

## 10. Quick-Start — Running Everything

### Prerequisites

- Python 3.12
- Node.js 22+
- RDKit (installed automatically via pip)
- PowerShell (Windows) or Bash (Linux/macOS)

### 1 — ML pipeline

```powershell
cd ml

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1                          # Windows
# source .venv/bin/activate                           # Linux/macOS

# Install dependencies
pip install -e .

# Step 1: prepare training data from DeepCOP DESeq2 results
python -m signalforge_ml.prepare_deepcop

# Step 2: train
signalforge-ml train --config-path configs/baseline.yaml

# Verify artifacts exist
Test-Path artifacts/models/baseline.joblib
Test-Path artifacts/manifests/latest.json
Get-Content artifacts/manifests/latest.json
```

### 2 — Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
cp .env.example .env         # edit as needed
uvicorn app.main:app --reload --port 8000
# Open: http://localhost:8000/docs

# Verify metrics transparency contract
Invoke-RestMethod http://localhost:8000/meta | ConvertTo-Json -Depth 6
```

### 3 — Frontend

```powershell
cd frontend
npm install
cp .env.example .env         # set VITE_API_BASE_URL=http://localhost:8000
npm run dev
# Open: http://localhost:5173
```

---

## 11. Known Limitations and Upgrade Path

### Current Baseline Model

| Limitation | Root Cause | Fix |
|---|---|---|
| Only Enzalutamide data | VPC compound SMILES not available in DESeq2 file | Add SMILES to `DRUG_SMILES` in `prepare_deepcop.py` |
| Poor down-regulation recall (5%) | Class imbalance + single compound | Use `class_weight='balanced'` + multi-drug data |
| Gene hash fallback for OOV genes | GO matrix only covers 978 landmark genes | Expand gene coverage or use ESM-2 protein embeddings |
| Placeholder predictor in backend | `predictor.py` not yet wired to `baseline.joblib` | Implement joblib-load path + RDKit feature computation in predictor service |
| No LINCS L1000 full data | GEO files are 100+ GB and require NCBI account | Download per `SOURCE.md` instructions, retrain on full LINCS corpus |
| In-memory rate limiting | Does not scale to multiple backend replicas | Switch to Redis-backed rate limiter |

### Recommended Next Steps (Priority Order)

1. **Wire trained model into backend predictor** — load `baseline.joblib` in `SignalForgePredictor.__init__`, call feature pipeline in `predict_gene_effects`.
2. **Add VPC compound SMILES** — immediately expands training diversity from 1 to 5 compounds.
3. **Add `class_weight='balanced'`** to `LogisticRegression` — fixes recall asymmetry.
4. **Download full LINCS L1000 data** from GEO (see `ml/data/raw/deepcop/SOURCE.md`) — enables training at full DeepCOP scale (~500K perturbations).
5. **Expand gene coverage** — GO matrix covers 978 LINCS landmark genes; for novel genes, consider ESM-2 protein embeddings instead of the SHA-256 hash fallback.
6. **Swap LogisticRegression for a neural network** — the original DeepCOP architecture is a simple feedforward net; a 3-layer MLP with dropout would match the paper's performance.

---

## 12. Containerized Deployment

SignalForge now includes Docker assets for enterprise-friendly delivery:

- `backend/Dockerfile`
- `frontend/Dockerfile`
- `frontend/nginx.conf`
- `docker-compose.yml`

### Run with Docker Compose

```powershell
docker compose up --build -d
```

### Endpoints

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- OpenAPI docs: `http://localhost:8000/docs`
- Metrics transparency endpoint: `http://localhost:8000/meta`

### Stop

```powershell
docker compose down
```

### What `/meta` now exposes

`GET /meta` includes:

- `model_version`
- `training_status`
- `training_metrics` (for example `accuracy`, `macro_f1`, `weighted_f1`, and `rauc` when present)
- `metrics_source`

These values are loaded from the training manifest (`ml/artifacts/manifests/latest.json`) and surfaced directly in both JSON responses and OpenAPI documentation.

---

## 13. Operational Incident Log

The full production-scale training timeline, incidents, and fixes are documented in:

- `docs/training-incident-log-2026-05-02.md`

This log should be updated when any long-running training cycle experiences:

- process termination without traceback
- memory-related refactors
- changes to deep-to-RF execution sequencing
- promotion-threshold decisions or metric regressions
