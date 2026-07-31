import type { RankedCompound } from "../types";
import ForceGraph from "./ForceGraph";

interface AtlasGraphProps {
  strongestReversal: RankedCompound | undefined;
  suppressedGenes: string[];
  restoredGenes: string[];
  embedded?: boolean;
}

export default function AtlasGraph({
  strongestReversal,
  suppressedGenes,
  restoredGenes,
  embedded = false,
}: AtlasGraphProps) {
  if (!strongestReversal) {
    return <p className="empty-state">Rank a signature to show the interaction graph.</p>;
  }

  const graphGenes = [
    ...suppressedGenes.map((gene) => ({ gene, tone: "down" as const })),
    ...restoredGenes.map((gene) => ({ gene, tone: "up" as const })),
  ];

  const canvas = (
    <div className={`graph-canvas${embedded ? " graph-canvas-embedded" : ""}`}>
      <ForceGraph
        genes={graphGenes}
        compound={strongestReversal.compound_name}
        score={strongestReversal.reversal_score}
      />
    </div>
  );

  if (embedded) {
    return canvas;
  }

  return (
    <section className="glass-panel graph-panel">
      <div className="section-heading split-heading">
        <div>
          <p className="eyebrow">Graph</p>
          <h2>Signature links</h2>
        </div>
        <div className="mini-stat compact-stat">
          <span>Primary</span>
          <strong>{strongestReversal.compound_name}</strong>
        </div>
      </div>
      {canvas}
    </section>
  );
}
