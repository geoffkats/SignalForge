import type { RankedCompound } from "../types";
import ForceGraph from "./ForceGraph";

interface AtlasGraphProps {
  strongestReversal: RankedCompound | undefined;
  suppressedGenes: string[];
  restoredGenes: string[];
}

export default function AtlasGraph({ strongestReversal, suppressedGenes, restoredGenes }: AtlasGraphProps) {
  if (!strongestReversal) {
    return <p className="empty-state">Run a reversal signature to generate the candidate interaction field.</p>;
  }

  const graphGenes = [
    ...suppressedGenes.map((gene) => ({ gene, tone: "down" as const })),
    ...restoredGenes.map((gene) => ({ gene, tone: "up" as const })),
  ];

  return (
    <section className="glass-panel graph-panel">
      <div className="section-heading split-heading">
        <div>
          <p className="eyebrow">Interaction field</p>
          <h2>Candidate-to-signature graph</h2>
        </div>
        <div className="mini-stat">
          <span>Primary node</span>
          <strong>{strongestReversal.compound_name}</strong>
        </div>
      </div>
      <div className="graph-canvas">
        <ForceGraph
          genes={graphGenes}
          compound={strongestReversal.compound_name}
          score={strongestReversal.reversal_score}
        />
      </div>
    </section>
  );
}
