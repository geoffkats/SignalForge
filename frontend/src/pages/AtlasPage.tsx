import { type FormEvent, useEffect, useState } from "react";
import type { RankedCompound, ReverseSignatureResponse } from "../types";
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
  atlasSize?: number;
  onSubmit: (e: FormEvent<HTMLFormElement>) => void;
}

export default function AtlasPage({
  upInput, setUpInput,
  downInput, setDownInput,
  suppressedGenes,
  restoredGenes,
  reverseResponse,
  isSearching,
  atlasSize,
  onSubmit,
}: AtlasPageProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    setSelectedId(reverseResponse?.results[0]?.compound_id ?? null);
  }, [reverseResponse]);

  const selected: RankedCompound | undefined =
    reverseResponse?.results.find((r) => r.compound_id === selectedId) ?? reverseResponse?.results[0];

  return (
    <div className="workspace-grid atlas-grid atlas-grid-task">
      <section className="glass-panel workbench-panel atlas-input">
        <div className="section-heading compact-heading">
          <p className="eyebrow">Signature</p>
          <h2>Reverse search</h2>
        </div>
        <form onSubmit={onSubmit} className="stack-form">
          <label>
            <span>Suppress</span>
            <input value={upInput} onChange={(e) => setUpInput(e.target.value)} />
          </label>
          <div className="chip-row compact">
            {suppressedGenes.map((gene) => (
              <span key={gene} className="gene-chip gene-chip-warm">{gene}</span>
            ))}
          </div>
          <label>
            <span>Restore</span>
            <input value={downInput} onChange={(e) => setDownInput(e.target.value)} />
          </label>
          <div className="chip-row compact">
            {restoredGenes.map((gene) => (
              <span key={gene} className="gene-chip gene-chip-cool">{gene}</span>
            ))}
          </div>
          <button className="submit-button secondary" type="submit" disabled={isSearching}>
            {isSearching ? "Ranking…" : "Rank compounds"}
          </button>
          <p className="tool-meta-line">
            Library {atlasSize ?? "—"}
            {reverseResponse?.inference_mode ? ` · ${reverseResponse.inference_mode}` : ""}
          </p>
        </form>
      </section>

      <section className="glass-panel candidate-panel atlas-rankings">
        <div className="section-heading split-heading compact-heading">
          <div>
            <p className="eyebrow">Rankings</p>
            <h2>Candidates</h2>
          </div>
          <div className="mini-stat compact-stat">
            <span>Shown</span>
            <strong>{reverseResponse?.results.length ?? 0}</strong>
          </div>
        </div>

        {reverseResponse ? (
          <>
            <div className="rank-table" role="list">
              {reverseResponse.results.map((result, index) => {
                const active = result.compound_id === selected?.compound_id;
                return (
                  <button
                    key={result.compound_id}
                    type="button"
                    role="listitem"
                    className={`rank-row${active ? " rank-row-active" : ""}`}
                    onClick={() => setSelectedId(result.compound_id)}
                  >
                    <span className="rank-index">{String(index + 1).padStart(2, "0")}</span>
                    <span className="rank-name">{result.compound_name}</span>
                    <span className="rank-score">{result.reversal_score.toFixed(2)}</span>
                  </button>
                );
              })}
            </div>
            <p className="audit-line">
              Audit {reverseResponse.audit_id.slice(0, 12)}
            </p>
          </>
        ) : (
          <p className="empty-state">Set a signature and rank to fill the atlas.</p>
        )}
      </section>

      <section className="glass-panel atlas-detail">
        <div className="section-heading compact-heading">
          <p className="eyebrow">Selected</p>
          <h2>{selected?.compound_name ?? "No selection"}</h2>
        </div>
        {selected ? (
          <div className="atlas-detail-body">
            <div className="docs-grid compact-grid">
              <article>
                <span className="docs-label">Score</span>
                <strong>{selected.reversal_score.toFixed(3)}</strong>
              </article>
              <article>
                <span className="docs-label">ID</span>
                <strong>{selected.compound_id}</strong>
              </article>
            </div>
            <p className="smiles-line">{selected.smiles}</p>
            <p className="atlas-detail-note">{selected.explanation}</p>
            <AtlasGraph
              strongestReversal={selected}
              suppressedGenes={suppressedGenes}
              restoredGenes={restoredGenes}
              embedded
            />
          </div>
        ) : (
          <p className="empty-state">Select a ranked compound to inspect structure context.</p>
        )}
      </section>
    </div>
  );
}
