# SignalForge Translational Analytics Platform

> Molecule-to-transcriptome intelligence — built on the DeepCOP paper (PMID 31504186).

[![CI](https://github.com/geoffkats/SignalForge/actions/workflows/ci.yml/badge.svg)](https://github.com/geoffkats/SignalForge/actions/workflows/ci.yml)

SignalForge is a translational analytics platform that predicts how small molecules perturb gene expression and ranks candidate compounds against a desired therapeutic signature — turning transcriptomic reasoning into a reproducible, auditable, API-driven workflow.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  React SPA (frontend/)                                          │
│  Assay Page → Compound query + gene effect prediction           │
│  Atlas Page → Reverse-signature design + candidate ranking      │
│  Molecule Viewer → SmilesDrawer holographic rendering           │
└──────────────────────────┬──────────────────────────────────────┘
                           │ REST / JSON
┌──────────────────────────▼──────────────────────────────────────┐
│  FastAPI (backend/)                                             │
│  POST /predict/gene-effect  → per-gene up/down/neutral scores   │
│  POST /search/reverse-signature → ranked compound list          │
│  GET  /healthz  /meta        → telemetry + model provenance     │
│  Security: API key, rate limiter, request-ID, audit trail       │
└──────────────────────────┬──────────────────────────────────────┘
                           │ joblib
┌──────────────────────────▼──────────────────────────────────────┐
│  ML pipeline (ml/)                                              │
│  Data: DeepCOP DESeq2 + LINCS L1000 GO-term fingerprints        │
  │  Features: Morgan-2048 (RDKit) + GO-term gene vectors (978 genes × 1107 GO terms, hash fallback for OOV)
│  Model: LogisticRegression (class_weight=balanced, sklearn)     │
│  Macro F1: 0.51  |  Down-recall: 0.50  |  Up-recall: 0.53      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Repository structure

| Folder | Description |
|---|---|
| `backend/` | FastAPI API — prediction endpoints, audit IDs, API key auth, rate limiting |
| `frontend/` | React + TypeScript SPA — assay explorer, atlas, molecular visualisation |
| `ml/` | RDKit feature engineering, GO-term gene embeddings, training pipeline, model artifacts |
| `docs/` | Technical documentation and security architecture |
| `.github/workflows/` | CI — ML tests, backend tests, frontend build on every push |

---

## Quickstart

### 1. ML — train the model

```bash
cd ml
pip install -e ".[dev]"
signalforge-ml train --config configs/baseline.yaml
```

### 2. Backend — start the API

```bash
cd backend
pip install -e "."
cp .env.example .env          # edit API keys if needed
.venv/Scripts/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 3. Frontend — start the dev server

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** — paste a SMILES string, pick genes, run the assay.

---

## API reference

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/healthz` | — | Service health + model version |
| `GET` | `/meta` | — | Platform metadata + pipeline stages |
| `POST` | `/predict/gene-effect` | API key | Predict up/down/neutral per gene |
| `POST` | `/search/reverse-signature` | API key | Rank compounds by transcriptomic reversal score |

Full interactive docs at **http://127.0.0.1:8000/docs** (Swagger UI).

---

## Running tests

```bash
# ML pipeline
cd ml && pytest tests/ -v

# Backend API
cd backend && pytest tests/ -v

# Frontend type-check + build
cd frontend && npm run build
```

---

## Technology stack

- **ML**: Python 3.12, scikit-learn, RDKit, pandas, joblib
- **Backend**: FastAPI, Pydantic v2, uvicorn, Python 3.12
- **Frontend**: React 19, TypeScript strict, Vite 7, SmilesDrawer, React Router v6
- **CI**: GitHub Actions (ml-tests → backend-tests → frontend-build)
- **Containerisation**: Docker Compose (backend + frontend services)

---

## Scientific basis

Built on the DeepCOP framework (Moo *et al.*, 2019 — PMID 31504186).  
Training data: LNCaP prostate cancer cell line, Enzalutamide DESeq2 perturbation results, LINCS L1000 978 landmark genes.

> **Research use only.** Not validated for clinical decision-making.


### 1. Reverse Signature Search

The user uploads a disease signature such as genes that are too high or too low, and the system searches for compounds predicted to reverse it.

Pitch: "Find molecules that may counteract a disease program."

### 2. Mechanism Contrast Lab

Compare multiple compounds and show how different mechanisms could converge or diverge at the gene-expression level.

Pitch: "Why do two drugs with different targets still create similar transcriptomic outcomes?"

### 3. AI for Oncology Sandbox

Focus on cancer and let users explore compounds against prostate, breast, or lung cancer signatures.

Pitch: "A precision oncology explorer for gene-expression-directed compound screening."

## MVP

Build the smallest version first:

1. Load a compound library with SMILES.
2. Generate molecular fingerprints with RDKit.
3. Represent genes using Gene Ontology-derived features or a simpler embedding baseline.
4. Train a model to predict up/down regulation labels from LINCS-style perturbation data.
5. Build a UI that lets a user query one compound against one or more genes.
6. Show ranked predictions and a simple pathway/network visualization.

## Practical stack

- Model: PyTorch
- Cheminformatics: RDKit
- Data wrangling: pandas, pyarrow
- API: FastAPI
- Frontend: React or Next.js
- Visualization: Plotly, Cytoscape.js, or D3
- Storage: PostgreSQL or DuckDB for fast local iteration

## Suggested datasets

- LINCS L1000 perturbation data
- DrugBank or ChEMBL compound metadata
- Gene Ontology annotations
- MSigDB or pathway gene-set resources for pathway views

## What makes it cool

Most drug-AI demos stop at binding or classification. This one predicts downstream biological effect. That is a much better story:

- not "does molecule bind target?"
- but "what gene program might this molecule induce?"

That is a more visual, more intuitive, and more productizable idea.

## Repo plan

- [docs/deepcop-project-brief.md](docs/deepcop-project-brief.md): product concept, architecture, and phased roadmap
- [docs/security-architecture.md](docs/security-architecture.md): biotech-oriented guardrails and upgrade path
- [CONTRIBUTING.md](CONTRIBUTING.md): contribution workflow, PR expectations, and data/model contribution rules
- [LICENSE](LICENSE): GNU Affero General Public License v3.0 or later

## Open source policy

SignalForge Explorer is open source under the AGPL-3.0-or-later license.

That choice keeps the project open while providing stronger protection than permissive licenses: if someone modifies and serves the software over a network, they must also make the corresponding source available under the same license.

## Recommended next build

If you want to turn this into a real portfolio project, build SignalForge Explorer first. It has the best mix of research value, visual output, and demo quality.

## Quick start

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
copy .env.example .env
uvicorn app.main:app --reload
```

### Frontend

```powershell
cd frontend
npm install
copy .env.example .env
npm run dev
```

### ML pipeline

```powershell
cd ml
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
signalforge-ml ingest
signalforge-ml train
```

## Containerized deployment (enterprise-ready)

Use Docker Compose to run a stable backend/frontend stack with health checks and pinned runtime images.

```powershell
docker compose up --build -d
```

Services:

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

To stop:

```powershell
docker compose down
```

## Model metric transparency

SignalForge exposes training status and key quality metrics in `GET /meta` so reviewers can verify model quality before trusting results.

Example:

```powershell
Invoke-RestMethod http://localhost:8000/meta | ConvertTo-Json -Depth 6
```

The response includes:

- `training_status`
- `training_metrics` (for example `accuracy`, `macro_f1`, `weighted_f1`, `rauc` when available)
- `metrics_source` (manifest file path)

## What stands out technically

- molecule-plus-gene reasoning instead of plain compound classification
- reverse-signature ranking for disease-program exploration
- deterministic placeholder inference so the full stack is demoable before the real model is trained
- checksum-gated dataset handling and explicit research-use-only security posture