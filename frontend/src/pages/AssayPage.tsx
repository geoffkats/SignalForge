import { type FormEvent } from "react";
import type { GeneEffectResponse, MetaResponse } from "../types";
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
    <div className={`workspace-grid assay-grid assay-grid-task${isPredicting ? " is-predicting" : ""}`}>
      <section className="glass-panel workbench-panel assay-input">
        <div className="section-heading compact-heading">
          <p className="eyebrow">Input</p>
          <h2>Compound → genes</h2>
        </div>
        <form onSubmit={onSubmit} className="stack-form">
          <label>
            <span>SMILES</span>
            <textarea value={smiles} onChange={(e) => setSmiles(e.target.value)} rows={4} />
          </label>
          <label>
            <span>Gene panel</span>
            <input value={geneInput} onChange={(e) => setGeneInput(e.target.value)} />
          </label>
          <div className="chip-row compact">
            {geneTokens.map((gene) => (
              <span key={gene} className="gene-chip">{gene}</span>
            ))}
          </div>
          <button className="submit-button" type="submit" disabled={isPredicting}>
            {isPredicting ? "Running…" : "Run prediction"}
          </button>
          <p className="tool-meta-line">
            {meta?.model_version ?? "model unavailable"}
            {meta?.inference_mode ? ` · ${meta.inference_mode}` : ""}
          </p>
        </form>
      </section>

      <MoleculeConstruct smiles={smiles} isPredicting={isPredicting} />

      <section className={`glass-panel matrix-panel assay-results${isPredicting ? " shimmer" : ""}`}>
        <div className="sf-content">
          <div className="sf-header">
            <div>
              <p className="sf-eyebrow">Results</p>
              <h2 className="sf-title">Predicted regulation</h2>
            </div>
            <div className="sf-audit">
              <span className="sf-audit-label">Audit</span>
              <span className="sf-audit-value">{predictionResponse?.audit_id.slice(0, 8) ?? "—"}</span>
            </div>
          </div>

          <div className="sf-tabs">
            <button type="button" className={`sf-tab ${!wetLabMode ? "active" : ""}`} onClick={() => setWetLabMode(false)}>
              Data
            </button>
            <button type="button" className={`sf-tab ${wetLabMode ? "active" : ""}`} onClick={() => setWetLabMode(true)}>
              Wet lab
            </button>
          </div>

          {isPredicting ? (
            <div className="assay-loading-state">
              <div className="assay-loading-bar" />
              <p className="assay-loading-text">Scoring gene panel…</p>
            </div>
          ) : (
            <PredictionSurface predictionResponse={predictionResponse} wetLabMode={wetLabMode} />
          )}

          <footer className="sf-footer">
            <span className="sf-mean">
              Mean confidence <strong>{predictionResponse ? meanConfidence.toFixed(2) : "—"}</strong>
            </span>
            <button className="sf-run-btn" type="button" onClick={onRerun} disabled={isPredicting}>
              {isPredicting ? "Running…" : "Re-run"}
            </button>
          </footer>
        </div>
      </section>
    </div>
  );
}
