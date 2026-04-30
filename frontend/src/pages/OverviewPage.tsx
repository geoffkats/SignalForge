import type { MetaResponse, RankedCompound } from "../types";
import { sampleCompound, sampleTumorContext, workspaces, type WorkspaceId } from "../constants";

interface OverviewPageProps {
  meta: MetaResponse | null;
  geneCount: number;
  meanConfidence: number | null;
  predictionRan: boolean;
  strongestReversal: RankedCompound | undefined;
  activeWorkspace: WorkspaceId;
  setActiveWorkspace: (id: WorkspaceId) => void;
}

export default function OverviewPage({
  meta,
  geneCount,
  meanConfidence,
  predictionRan,
  strongestReversal,
  activeWorkspace,
  setActiveWorkspace,
}: OverviewPageProps) {
  const isOnline = !!meta;
  const systemHealth = isOnline ? "online" : "degraded";

  return (
    <div className="workspace-grid overview-grid">
      <section className="glass-panel hero-panel overview-hero">
        <div>
          <p className="eyebrow">Mission control</p>
          <h1>SignalForge behaves like a platform, not a splash page.</h1>
          <p className="lede">
            Navigate between assay execution, candidate discovery, and API operations from a persistent lab shell that
            feels closer to translational software than a marketing layout.
          </p>
        </div>
        <div className="overview-hero-grid">
          <article className="metric-panel glow">
            <span>
              <span className={`status-dot${isOnline ? "" : " status-dot-degraded"}`} aria-hidden="true" />
              System health
            </span>
            <strong>{systemHealth}</strong>
            <small>metadata service and UI shell handshake</small>
          </article>
          <article className="metric-panel">
            <span>Loaded targets</span>
            <strong>{geneCount}</strong>
            <small>genes ready for the next assay run</small>
          </article>
          <article className="metric-panel">
            <span>Mean confidence</span>
            <strong>{predictionRan && meanConfidence !== null ? meanConfidence.toFixed(2) : "—"}</strong>
            <small>from the latest inference batch</small>
          </article>
          <article className="metric-panel">
            <span>Top reversal</span>
            <strong>{strongestReversal ? strongestReversal.reversal_score.toFixed(2) : "—"}</strong>
            <small>{strongestReversal?.compound_name ?? "awaiting ranking"}</small>
          </article>
        </div>
      </section>

      <section className="glass-panel module-panel">
        <div className="section-heading">
          <p className="eyebrow">System modules</p>
          <h2>Lab workspaces</h2>
        </div>
        <div className="module-grid">
          {workspaces.map((workspace) => (
            <button
              key={workspace.id}
              type="button"
              className={`module-card ${workspace.id === activeWorkspace ? "module-card-active" : ""}`}
              onClick={() => setActiveWorkspace(workspace.id)}
            >
              <span>{workspace.kicker}</span>
              <strong>{workspace.title}</strong>
              <p>{workspace.description}</p>
            </button>
          ))}
        </div>
      </section>

      <section className="glass-panel telemetry-panel">
        <div className="section-heading split-heading">
          <div>
            <p className="eyebrow">Telemetry</p>
            <h2>Run posture</h2>
          </div>
          <div className="mini-stat mono-stat">
            <span>Model</span>
            <strong>{meta?.model_version ?? "baseline-heuristic-v0"}</strong>
          </div>
        </div>
        <div className="telemetry-stack">
          <article>
            <span className="docs-label">Active compound</span>
            <strong>{sampleCompound}</strong>
          </article>
          <article>
            <span className="docs-label">Assay context</span>
            <strong>{sampleTumorContext}</strong>
          </article>
          <article>
            <span className="docs-label">Security modes</span>
            <div className="tag-list">
              {(meta?.security_modes ?? ["api-key", "rate-limit", "request-id", "research-use-only"]).map((mode) => (
                <span key={mode}>{mode}</span>
              ))}
            </div>
          </article>
        </div>
      </section>

      <section className="glass-panel feed-panel">
        <div className="section-heading">
          <p className="eyebrow">Pipeline feed</p>
          <h2>Operational trace</h2>
        </div>
        <div className="timeline">
          {(meta?.pipeline_stages ?? ["ingestion", "feature-store", "training", "inference", "audit"]).map((stage, index) => (
            <article key={stage} className="timeline-row">
              <span className="timeline-index">0{index + 1}</span>
              <div>
                <strong>{stage}</strong>
                <p>
                  {index < 2
                    ? "Prepared and indexed for platform execution."
                    : index === 2
                    ? "Model artifacts available for research runs."
                    : "Serving active operator workflows."}
                </p>
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
