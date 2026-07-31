# Security Architecture

SignalForge is a research platform concept, not a clinical decision system. The repo scaffold reflects that boundary explicitly.

## Guardrails in this scaffold

- API key support for protected endpoints
- in-memory rate limiting to reduce scraping and abuse
- request IDs for auditability
- security response headers
- biotech request size limits for gene lists and signatures
- checksum verification before model training on source datasets
- explicit research-use-only classification in request handling

## Why this matters in biotech

Biotech tools fail badly when they blur experimentation, provenance, and deployment boundaries. This scaffold keeps those boundaries visible:

- the app layer exposes predictions with audit IDs
- the ML layer refuses unverified datasets when a checksum is configured
- the project documentation does not overclaim medical validity

## Recommended next security upgrades

1. Replace in-memory rate limiting with Redis-backed quotas (`fastapi-limiter` + Redis).
2. Add signed model manifests and artifact hashing (cosign or SLSA attestation).
3. ~~Wire the trained `baseline.joblib` model into the backend predictor to replace the deterministic heuristic.~~ **Done (Phase 4)** — eager load with `inference_mode` provenance; heuristic remains fallback only.
4. Add structured audit logging to PostgreSQL or an append-only store.
5. Add role-based access control for batch screening and dataset upload flows.
6. Hash API keys before storage; implement key rotation without downtime.
7. ~~Validate SMILES input server-side with RDKit before passing to the ML pipeline.~~ **Done (Phase 4)**.

## Phase 3/4 Operational Security Additions

Recent large-scale training runs introduced operational controls that should be treated as part of the platform security posture:

- explicit config-root path resolution to avoid loading unintended files from the wrong working directory
- guarded deep-to-RF sequencing so the second model does not run on incomplete upstream state
- process-level verification before terminating long-running jobs (prevents accidental kill of active worker process)
- manifest-based completion checks before promotion or follow-up stages

## Artifact and Provenance Guidance

For deep and RF artifacts generated in long runs:

- always check manifest `status == trained` before promoting
- keep model path and manifest path coupled in release notes
- retain run incident logs for traceability of failures, restarts, and fix commits

Primary operational log file for current full-data training cycle:

- `docs/training-incident-log-2026-05-02.md`