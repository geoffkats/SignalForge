import { type FormEvent } from "react";
import type { GeneEffectResponse, MetaResponse } from "../types";
import { readoutParticles, sampleCompound, sampleTumorContext } from "../constants";
import MoleculeConstruct from "../components/MoleculeConstruct";
import PredictionSurface from "../components/PredictionSurface";

interface AssayPageProps {
  smiles: string;
  setSmiles: (v: string) => void;
  geneInput: string;
  setGeneInput: (v: string) => void;
  geneTokens: string[];
  meta: MetaResponse | null;
  predictionResponse: GeneEffectResponse | null;
  isPredicting: boolean;
  wetLabMode: boolean;
  setWetLabMode: (v: boolean) => void;
  meanConfidence: number;
  onSubmit: (e: FormEvent<HTMLFormElement>) => void;
  onRerun: () => void;
}

export default function AssayPage({
  smiles, setSmiles,
  geneInput, setGeneInput,
  geneTokens,
  meta,
  predictionResponse,
  isPredicting,
  wetLabMode, setWetLabMode,
  meanConfidence,
  onSubmit,
  onRerun,
}: AssayPageProps) {
  return (
    <div className={`workspace-grid assay-grid${isPredicting ? " is-predicting" : ""}`}>
      <section className="glass-panel workbench-panel">
        <div className="section-heading">
          <p className="eyebrow">Bench A</p>
          <h2>Compound effect assay</h2>
        </div>
        <form onSubmit={onSubmit} className="stack-form">
          <label>
            <span>Compound SMILES</span>
            <textarea value={smiles} onChange={(e) => setSmiles(e.target.value)} rows={6} />
          </label>
          <label>
            <span>Gene panel</span>
            <input value={geneInput} onChange={(e) => setGeneInput(e.target.value)} />
          </label>
          <div className="chip-row">
            {geneTokens.map((gene) => (
              <span key={gene} className="gene-chip">{gene}</span>
            ))}
          </div>
          <button className="submit-button" type="submit" disabled={isPredicting}>
            {isPredicting ? "Running transcriptomic inference…" : "Run effect prediction"}
          </button>
        </form>
      </section>

      <MoleculeConstruct smiles={smiles} isPredicting={isPredicting} />

      <section className={`glass-panel matrix-panel sf-readout-shell${isPredicting ? " shimmer" : ""}`}>
        <div className="sf-particles" aria-hidden="true">
          {readoutParticles.map((particle, index) => (
            <span
              key={`${particle.left}-${particle.top}-${index}`}
              className={`sf-particle sf-particle-${particle.tone}`}
              style={{
                left: particle.left,
                top: particle.top,
                width: `${particle.size}px`,
                height: `${particle.size}px`,
                animationDuration: particle.duration,
                animationDelay: particle.delay,
              }}
            />
          ))}
        </div>
        <div className="sf-halo sf-halo-teal" aria-hidden="true" />
        <div className="sf-halo sf-halo-violet" aria-hidden="true" />
        <div className="sf-content">
          <div className="sf-header">
            <div>
              <p className="sf-eyebrow">Readout matrix · Bench A</p>
              <h2 className="sf-title">Predicted gene expression shifts</h2>
            </div>
            <div className="sf-audit">
              <span className="sf-audit-label">Audit ID</span>
              <span className="sf-audit-value">{predictionResponse?.audit_id.slice(0, 8) ?? "pending"}</span>
            </div>
          </div>

          <div className="sf-smiles-bar">
            <span className="sf-smiles-label">SMILES</span>
            <code className="sf-smiles-code">{smiles}</code>
          </div>

          <div className="sf-tabs">
            <button type="button" className={`sf-tab ${!wetLabMode ? "active" : ""}`} onClick={() => setWetLabMode(false)}>
              Data view
            </button>
            <button type="button" className={`sf-tab ${wetLabMode ? "active" : ""}`} onClick={() => setWetLabMode(true)}>
              Wet lab view
            </button>
          </div>

          {isPredicting ? (
            <div className="assay-loading-state">
              <div className="assay-loading-bar" />
              <p className="assay-loading-text">Inference running — transcriptomic signal resolution in progress…</p>
            </div>
          ) : (
            <PredictionSurface predictionResponse={predictionResponse} wetLabMode={wetLabMode} />
          )}

          <footer className="sf-footer">
            <span className="sf-mean">
              Mean confidence <strong>{predictionResponse ? meanConfidence.toFixed(2) : "—"}</strong>
            </span>
            <button className="sf-run-btn" type="button" onClick={onRerun} disabled={isPredicting}>
              {isPredicting ? "Running…" : "Re-run assay"}
            </button>
          </footer>
        </div>
      </section>

      <section className="glass-panel assay-sidecar">
        <div className="section-heading">
          <p className="eyebrow">Assay manifest</p>
          <h2>Run context</h2>
        </div>
        <div className="docs-grid compact-grid">
          <article>
            <span className="docs-label">Compound</span>
            <strong>{sampleCompound}</strong>
          </article>
          <article>
            <span className="docs-label">Biology</span>
            <strong>{sampleTumorContext}</strong>
          </article>
          <article>
            <span className="docs-label">Targets</span>
            <p>{geneTokens.join(", ")}</p>
          </article>
          <article>
            <span className="docs-label">Predictor</span>
            <p>{meta?.model_version ?? "baseline-heuristic-v0"}</p>
          </article>
        </div>
      </section>
    </div>
  );
}
