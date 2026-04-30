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
3. Wire the trained `baseline.joblib` model into the backend predictor to replace the deterministic heuristic.
4. Add structured audit logging to PostgreSQL or an append-only store.
5. Add role-based access control for batch screening and dataset upload flows.
6. Hash API keys before storage; implement key rotation without downtime.
7. Validate SMILES input server-side with RDKit before passing to the ML pipeline.