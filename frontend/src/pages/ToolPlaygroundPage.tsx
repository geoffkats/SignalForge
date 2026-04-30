import { FormEvent } from "react";
import type { GeneEffectResponse, ReverseSignatureResponse } from "../types";

interface ToolPlaygroundPageProps {
  smiles: string;
  setSmiles: (v: string) => void;
  geneInput: string;
  setGeneInput: (v: string) => void;
  upInput: string;
  setUpInput: (v: string) => void;
  downInput: string;
  setDownInput: (v: string) => void;
  isPredicting: boolean;
  isSearching: boolean;
  predictionResponse: GeneEffectResponse | null;
  reverseResponse: ReverseSignatureResponse | null;
  onPredict: (event: FormEvent<HTMLFormElement>) => void;
  onReverseSearch: (event: FormEvent<HTMLFormElement>) => void;
}

export default function ToolPlaygroundPage({
  smiles,
  setSmiles,
  geneInput,
  setGeneInput,
  upInput,
  setUpInput,
  downInput,
  setDownInput,
  isPredicting,
  isSearching,
  predictionResponse,
  reverseResponse,
  onPredict,
  onReverseSearch,
}: ToolPlaygroundPageProps) {
  return (
    <div className="workspace-grid tool-playground-grid">
      <section className="glass-panel tool-playground-hero">
        <p className="eyebrow">Translational analysis workspace</p>
        <h1>Execute perturbational and prioritization workflows immediately.</h1>
      </section>

      <section className="glass-panel tool-runner-card">
        <div className="section-heading">
          <p className="eyebrow">Analytical module A</p>
          <h2>Perturbational effect modeling</h2>
        </div>
        <form className="stack-form" onSubmit={onPredict}>
          <label>
            <span>Compound SMILES</span>
            <textarea value={smiles} onChange={(e) => setSmiles(e.target.value)} rows={4} />
          </label>
          <label>
            <span>Gene panel</span>
            <input value={geneInput} onChange={(e) => setGeneInput(e.target.value)} />
          </label>
          <button className="submit-button" type="submit" disabled={isPredicting}>
            {isPredicting ? "Running..." : "Run modeling"}
          </button>
        </form>

        <div className="tool-result-list">
          {predictionResponse ? (
            predictionResponse.predictions.slice(0, 5).map((p) => (
              <article key={p.gene} className="tool-result-row">
                <strong>{p.gene}</strong>
                <span>{p.direction}</span>
                <small>{p.confidence.toFixed(2)}</small>
              </article>
            ))
          ) : (
            <p className="empty-state">Run modeling to inspect predicted transcriptomic effects.</p>
          )}
        </div>
      </section>

      <section className="glass-panel tool-runner-card">
        <div className="section-heading">
          <p className="eyebrow">Analytical module B</p>
          <h2>Signature inversion ranking</h2>
        </div>
        <form className="stack-form" onSubmit={onReverseSearch}>
          <label>
            <span>Genes to suppress</span>
            <input value={upInput} onChange={(e) => setUpInput(e.target.value)} />
          </label>
          <label>
            <span>Genes to restore</span>
            <input value={downInput} onChange={(e) => setDownInput(e.target.value)} />
          </label>
          <button className="submit-button secondary" type="submit" disabled={isSearching}>
            {isSearching ? "Searching..." : "Compute ranking"}
          </button>
        </form>

        <div className="tool-result-list">
          {reverseResponse ? (
            reverseResponse.results.slice(0, 5).map((r) => (
              <article key={r.compound_id} className="tool-result-row">
                <strong>{r.compound_name}</strong>
                <span>reversal score</span>
                <small>{r.reversal_score.toFixed(2)}</small>
              </article>
            ))
          ) : (
            <p className="empty-state">Compute ranking to view prioritized reversal candidates.</p>
          )}
        </div>
      </section>
    </div>
  );
}
