# SignalForge Wiki

Welcome to the **SignalForge** documentation hub. SignalForge is a translational analytics platform that predicts how small molecules perturb gene expression and ranks candidate compounds against desired therapeutic signatures.

## Quick Navigation

- **[[Getting Started]]** — Setup, installation, and first run
- **[[Architecture Overview]]** — System design and components
- **[[API Reference]]** — Complete API documentation
- **[[Data Model]]** — Database schema and data formats
- **[[ML Pipeline]]** — Model training, evaluation, and deployment
- **[[Frontend Guide]]** — UI components and user workflows
- **[[Development]]** — Contributing, local development, and testing
- **[[Deployment]]** — Production setup and operations
- **[[FAQ & Troubleshooting]]** — Common issues and solutions

## What is SignalForge?

SignalForge turns transcriptomic reasoning into a reproducible, auditable, API-driven workflow. It enables researchers and drug discovery teams to:

1. **Predict molecule-gene interactions** — Input a small molecule and predict its regulatory effects on genes
2. **Reverse-signature search** — Upload a disease signature and rank compounds likely to invert it
3. **Mechanism comparison** — Compare how different compounds affect shared gene programs
4. **Hit identification** — Identify promising therapeutic candidates from large compound libraries

## Key Features

| Feature | Description |
|---------|-------------|
| **Fast predictions** | Sub-second inference on millions of compound-gene pairs |
| **Explainability** | Pathway overlays and nearest-neighbor compound explanations |
| **Multi-drug learning** | Models trained on diverse perturbations (not single drugs) |
| **Production-ready** | Docker-containerized, versioned models, feature drift detection |
| **Transparent** | Clear preprocessing, realistic performance expectations |

## Project Status

**Phase 4 (Complete)** — Full product deployment with:
- Trained random forest and optional deep encoders
- FastAPI backend with eager model loading
- ~300-compound reverse-signature atlas from LINCS
- RDKit SMILES validation and inference provenance
- Docker containerization

**Current Performance:**
- Accuracy: **0.8736**
- Macro F1: **0.8733**

## Technology Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.9+, FastAPI, scikit-learn, RDKit, PyTorch |
| **Frontend** | TypeScript, React, Tailwind CSS |
| **Data** | PostgreSQL, pandas, NumPy |
| **Deployment** | Docker, Docker Compose |
| **ML** | Random Forest, Neural Networks, Morgan fingerprints, GO embeddings |

## Repository Structure

```
SignalForge/
├── backend/              # FastAPI prediction service
├── frontend/             # React UI
├── ml/                   # Model training and evaluation
├── data/                 # Data schemas and ingestion
├── docker/               # Deployment configurations
├── docs/                 # Documentation and project brief
└── tests/                # Test suites
```

## Getting Help

- **Bug reports**: Open an issue on GitHub
- **Feature requests**: Check existing issues or create a new one
- **Questions**: See [[FAQ & Troubleshooting]]
- **Contributing**: Read [[Development]] for guidelines

## Latest Updates

- **Model improvements**: Upgraded to random forest with sample weighting (Phase 2)
- **Multi-cell data**: Expanded to full LINCS perturbation data (Phase 3)
- **Production deployment**: FastAPI + Docker containerization (Phase 4)
- **Reverse search**: ~300-compound atlas with SMILES validation

---

**Last updated**: September 2026  
**Maintained by**: SignalForge team
