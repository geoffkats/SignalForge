import { type FormEvent } from "react";
import type { ReverseSignatureResponse } from "../types";
import AtlasGraph from "../components/AtlasGraph";

interface AtlasPageProps {
  upInput: string;
  setUpInput: (v: string) => void;
  downInput: string;
  setDownInput: (v: string) => void;
  suppressedGenes: string[];
  restoredGenes: string[];
  reverseResponse: ReverseSignatureResponse | null;
  isSearching: boolean;
  onSubmit: (e: FormEvent<HTMLFormElement>) => void;
}

export default function AtlasPage({
  upInput, setUpInput,
  downInput, setDownInput,
  suppressedGenes,
  restoredGenes,
  reverseResponse,
  isSearching,
  onSubmit,
}: AtlasPageProps) {
  const strongestReversal = reverseResponse?.results[0];

  return (
    <div className="workspace-grid atlas-grid">
      <section className="glass-panel workbench-panel">
        <div className="section-heading">
          <p className="eyebrow">Bench B</p>
          <h2>Reverse-signature design</h2>
        </div>
        <form onSubmit={onSubmit} className="stack-form">
          <label>
            <span>Genes to suppress</span>
            <input value={upInput} onChange={(e) => setUpInput(e.target.value)} />
          </label>
          <div className="chip-row compact">
            {suppressedGenes.map((gene) => (
              <span key={gene} className="gene-chip gene-chip-warm">{gene}</span>
            ))}
          </div>
          <label>
            <span>Genes to restore</span>
            <input value={downInput} onChange={(e) => setDownInput(e.target.value)} />
          </label>
          <div className="chip-row compact">
            {restoredGenes.map((gene) => (
              <span key={gene} className="gene-chip gene-chip-cool">{gene}</span>
            ))}
          </div>
          <button className="submit-button secondary" type="submit" disabled={isSearching}>
            {isSearching ? "Ranking perturbation candidates..." : "Search reversal candidates"}
          </button>
        </form>
      </section>

      <section className="glass-panel candidate-panel">
        <div className="section-heading split-heading">
          <div>
            <p className="eyebrow">Candidate atlas</p>
            <h2>Ranked compounds</h2>
          </div>
          <div className="mini-stat">
            <span>Top K</span>
            <strong>{reverseResponse?.results.length ?? 0}</strong>
          </div>
        </div>
        {reverseResponse ? (
          <div className="candidate-list">
            {reverseResponse.results.map((result, index) => (
              <article key={result.compound_id} className="candidate-card">
                <div className="candidate-rank">{String(index + 1).padStart(2, "0")}</div>
                <div className="candidate-body">
                  <div className="result-topline">
                    <strong>{result.compound_name}</strong>
                    <span className="score-badge">score {result.reversal_score.toFixed(2)}</span>
                  </div>
                  <p className="smiles-line">{result.smiles}</p>
                  <p>{result.explanation}</p>
                </div>
              </article>
            ))}
            <p className="audit-line">Audit trail: {reverseResponse.audit_id}</p>
          </div>
        ) : (
          <p className="empty-state">No candidate ranking yet. Submit a reversal signature to populate the atlas.</p>
        )}
      </section>

      <AtlasGraph
        strongestReversal={strongestReversal}
        suppressedGenes={suppressedGenes}
        restoredGenes={restoredGenes}
      />

      <section className="glass-panel atlas-sidecar">
        <div className="section-heading">
          <p className="eyebrow">Signature profile</p>
          <h2>Intent mapping</h2>
        </div>
        <div className="docs-grid compact-grid">
          <article>
            <span className="docs-label">Suppress</span>
            <p>{suppressedGenes.join(", ") || "none"}</p>
          </article>
          <article>
            <span className="docs-label">Restore</span>
            <p>{restoredGenes.join(", ") || "none"}</p>
          </article>
          <article>
            <span className="docs-label">Best current match</span>
            <p>{strongestReversal?.compound_name ?? "awaiting search"}</p>
          </article>
          <article>
            <span className="docs-label">Workflow</span>
            <p>Signature assembly → candidate scoring → audit capture</p>
          </article>
        </div>
      </section>
    </div>
  );
}
