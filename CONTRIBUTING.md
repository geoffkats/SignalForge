# Contributing to SignalForge Explorer

Thanks for contributing to SignalForge Explorer.

This project combines biotech-focused application code, ML training workflows, and research-oriented data processing. Changes should be reproducible, reviewable, and safe to operate.

## Before You Start

- Read the main [README.md](README.md) and [docs/FULL_DOCUMENTATION.md](docs/FULL_DOCUMENTATION.md).
- Open an issue before making large architectural changes.
- Keep pull requests small and focused.
- Do not commit secrets, API keys, credentials, or proprietary datasets.
- Treat all model and biology-facing outputs as research tooling, not clinical guidance.

## Development Setup

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

### ML Pipeline

```powershell
cd ml
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
python -m signalforge_ml.prepare_deepcop
signalforge-ml train --config-path configs/baseline.yaml
```

## Contribution Rules

- Use clear branch names and clear commit messages.
- Prefer minimal diffs over wide refactors.
- Update docs when you change behavior, APIs, configs, or training flow.
- Keep code style consistent with the surrounding files.
- Add or update validation where practical for the area you touch.
- Do not break the current repo layout unless the change is intentional and documented.

## Pull Request Checklist

Before opening a pull request, make sure you have:

- Explained what changed and why.
- Linked the related issue, if one exists.
- Updated relevant docs.
- Run the narrowest useful validation for the touched area.
- Called out known limitations, follow-ups, or risks.

## Data and Model Contributions

If your change touches the ML pipeline or datasets:

- Document the source of any new dataset.
- Record schema assumptions and preprocessing steps.
- Do not replace raw source files silently.
- Prefer deterministic preprocessing scripts over manual edits.
- Preserve checksum or provenance safeguards when adding training inputs.
- Clearly state whether metrics are from placeholder logic or a trained artifact.
- Large data files (>50 MB) must be hosted on HuggingFace (`Geoffkats/signalforge-deepcop`) — **do not commit them to git**. Update `ml/data/raw/deepcop/SOURCE.md` with download instructions.

## Security Reporting

Do not open public issues for sensitive security problems.

Report security issues privately to the maintainers first. Include:

- affected component
- reproduction steps
- impact
- proposed mitigation if available

Until a dedicated contact channel is added, keep sensitive reports out of public issue threads.

## License

By contributing to this repository, you agree that your contributions will be licensed under the repository license.

This project uses the GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later).
