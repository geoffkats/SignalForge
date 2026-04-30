# DeepCOP Project Brief

## Source paper

Paper: DeepCOP: deep learning-based approach to predict gene regulating effects of small molecules

Key idea:

- compound descriptors + gene descriptors -> predict regulation effect
- trained on LINCS-style differential expression endpoints
- avoids requiring explicit protein-target interaction knowledge

## Product concept

Turn the paper into a research-facing AI product:

### SignalForge Explorer

"Predict what a molecule will do to a gene program."

Users interact with three entities:

- molecules
- genes
- pathways or disease signatures

Core loop:

1. User selects or inputs a molecule.
2. User selects a gene, pathway, or custom signature.
3. Model predicts likely regulation effects.
4. System explains the prediction with pathway overlays and nearest known compounds.
5. User saves or exports promising hits.

## Why this works as a project

- The research story is credible and specific.
- The UI can be visually strong.
- Public data exists for a meaningful prototype.
- You can start with a simplified baseline and still have a compelling demo.

## Technical architecture

### Data layer

Inputs:

- compound SMILES
- compound fingerprints or learned embeddings
- gene identifiers
- gene ontology features or learned gene embeddings
- perturbation labels indicating up/down/no-change

Possible source tables:

- compounds
- genes
- compound_gene_effect_labels
- pathway_gene_sets

### Modeling layer

Baseline:

- Morgan fingerprint for compounds
- one-hot or embedding representation for genes
- binary or ternary classifier for regulation direction

Research-faithful version:

- RDKit fingerprints or graph encoder for molecules
- GO-term derived embedding for genes
- multi-task neural net for compound-gene regulation prediction

Good first model outputs:

- probability of up-regulation
- probability of down-regulation
- confidence score

### API layer

Suggested endpoints:

- `POST /predict/gene-effect`
- `POST /search/reverse-signature`
- `GET /compound/{id}`
- `GET /gene/{symbol}`
- `GET /pathway/{id}`

### Frontend layer

Core screens:

- home/search screen
- compound detail view
- gene/pathway effect heatmap
- reverse-signature ranking screen
- experiment history or saved runs

Strong visual elements:

- heatmaps for predicted regulation
- pathway cards with enrichment summaries
- similarity graph of compounds
- confidence sliders and filters

## MVP scope

Keep the first version tight.

### Phase 1

- ingest a small curated subset of LINCS-like perturbation examples
- compute fingerprints for a limited compound set
- train a baseline classifier
- expose a single prediction API
- build a minimal UI with molecule input and ranked gene outputs

### Phase 2

- add disease-signature reversal search
- add pathway enrichment summaries
- add nearest-neighbor comparison to known compounds

### Phase 3

- add explainability views
- support batch screening
- add saved projects and exportable reports

## Differentiators

If you want this to feel sharper than a standard ML demo, add one of these:

### 1. Counterfactual molecule editing

Let the user tweak a substructure and see how predicted gene effects shift.

### 2. Signature reversal mode

Upload a disease signature and rank compounds predicted to invert it.

### 3. Mechanism comparison panel

Compare two compounds with different modes of action and show where their predicted transcriptomic signatures overlap.

## Honest constraints

- Public perturbation data is noisy.
- Model quality depends heavily on preprocessing and label design.
- A strong MVP does not need to exactly reproduce the paper.
- A simplified, transparent version is better than an overclaimed biomedical product.

## Best implementation strategy

Do not start by reproducing the full paper end to end.

Start with:

1. a clean subset of compounds
2. a limited gene set
3. a baseline classifier
4. a clear, visual UI

That gives you a real demo quickly, then you can deepen the biology later.

## Recommended build order

1. data schema and ingestion scripts
2. baseline model notebook or training pipeline
3. FastAPI prediction service
4. frontend explorer UI
5. reverse-signature search
6. explainability and pathway overlays

## Stretch goal

Add a "precision oncology" mode:

- user uploads a tumor expression signature
- system identifies dysregulated genes
- system ranks compounds likely to counter that profile

That is the version most likely to feel like a standout project in a portfolio, hackathon, or demo day.