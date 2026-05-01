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

- Ship a real multi-drug training upgrade and harden inference so feature drift fails loudly.

#### What changed in this phase

1. Replaced the noisy single-drug training set with a clean multi-drug landmark dataset.
2. Switched the model from logistic regression to a random forest.
3. Added sample weighting by $|log_2FC|$ so weakly regulated genes do not dominate training.
4. Added LNCaP-specific Morgan-bit selection (`LNCAPcorr_cols.csv`) to reduce compound-side noise.
5. Fixed the training/inference feature-shape mismatch and added a regression test.

#### Root cause analysis

The initial baseline plateaued near 51% accuracy because three constraints were stacked together:

- Only one drug was present in the training CSV, so the model could not learn cross-compound structure.
- Most labels were statistically weak, so the classifier was fitting noise rather than robust perturbation effects.
- Most genes were outside the 978-gene GO matrix, so inference often fell back to hash embeddings.

With three drugs and only landmark genes, 71% is a realistic ceiling for this phase. The jump to 89% at the stricter $|log_2FC| > 0.5$ threshold confirms that the biology is present, but the $|log_2FC| > 0.25$ band still contains genuinely ambiguous regulation.

#### Dataset redesign

Phase 2 training now uses:

- `Enzalutamide` via RDKit Morgan fingerprints from SMILES
- `VPC14449` via pre-computed Morgan fingerprints from `inhouse_morgan_2048.csv`
- `VPC17005` via pre-computed Morgan fingerprints from `inhouse_morgan_2048.csv`
- Landmark genes only, so every gene has a real GO-term vector
- A label filter of $|log_2FC| > 0.25$

This produces:

- 722 clean samples
- 3 compounds
- 405 landmark genes
- label balance of 376 `up` / 346 `down`

#### Key code changes

Training-data construction was rewritten so compounds can come from either real SMILES or pre-computed in-house Morgan fingerprints:

```python
DRUG_SMILES: dict[str, str] = {
	"Enzalutamide": "CC1(C)C(=O)N(c2ccc(C#N)cc2C(F)(F)F)C(=S)N1c3ccc(C(=O)NC)cc3F",
}

DRUG_PRECOMPUTED: set[str] = {"VPC14449", "VPC17005"}
```

The generated CSV now preserves the effect magnitude for weighting during training:

```python
result = df[
	[
		"perturbation_id",
		"compound_id",
		"compound_name",
		"smiles",
		"gene_symbol",
		"regulation_label",
		"log2fc",
	]
].reset_index(drop=True)
```

Compound-side noise is reduced with the LNCaP correlation prior:

```python
corr_idx = _load_corr_cols()
if corr_idx is not None and len(corr_idx) > 0:
	compound_vectors = compound_vectors_raw[:, corr_idx]
else:
	compound_vectors = compound_vectors_raw
```

The classifier was upgraded to a random forest with sample weights derived from $|log_2FC|$:

```python
w_all = cleaned_frame["log2fc"].abs().to_numpy(dtype=np.float64)
w_all = w_all / (w_all.mean() + 1e-9)

model = RandomForestClassifier(
	n_estimators=300,
	max_features="sqrt",
	class_weight="balanced",
	random_state=42,
	n_jobs=-1,
)
model.fit(x_train, y_train, sample_weight=sample_weight_train)
```

Inference now asserts feature width before calling `predict_proba`, so future training/inference drift fails immediately instead of silently producing incorrect scores:

```python
if self._expected_feature_count is not None and feature.shape[1] != self._expected_feature_count:
	raise ValueError(
		"Inference feature width mismatch: "
		f"built {feature.shape[1]} features, "
		f"model expects {self._expected_feature_count}."
	)
```

#### Phase 2 metrics

Using the current `baseline.yaml` configuration:

- Accuracy: **0.7103**
- Macro F1: **0.7087**
- Weighted F1: **0.7097**
- Down-class F1: **0.6866**
- Up-class F1: **0.7308**

This is a meaningful step up from the earlier baseline near 0.51 accuracy / 0.51 macro F1.

#### Interpretation

71% is a respectable floor for the current biological regime, not a tuning failure.

- All three compounds are AR antagonists, so the model mainly learns a family of related perturbations.
- The GO-term to direction relationship is real.
- The remaining error is likely dominated by ambiguous genes in the $|log_2FC| > 0.25$ band and mechanism overlap between AR suppression and general stress-response programs.

#### Natural next moves after Phase 2

1. Add a fourth drug with a non-AR mechanism, ideally something that perturbs FOXA1, MYC, or a parallel lineage program.
2. Test tighter Morgan-bit subsets, for example the top 800 or top 1,000 bits from `LNCAPcorr_cols.csv`.
3. Upgrade the manifest/version naming to reflect the new model family more precisely than `baseline-logreg-v1`.
4. Add group-aware evaluation so train/test splits do not overstate generalization across closely related compounds.
5. Expand beyond the in-house DeepCOP compounds by ingesting the GEO LINCS Level 2 files from `GSE92742` and `GSE70138`.

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