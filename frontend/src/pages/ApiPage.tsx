import { API_BASE, API_DOCS_URL } from "../lib/api";
import type { MetaResponse } from "../types";

interface ApiPageProps {
  meta: MetaResponse | null;
}

export default function ApiPage({ meta }: ApiPageProps) {
  const endpoints: Array<{ method: string; path: string; description: string }> = [
    { method: "GET", path: "/healthz", description: "Health check and environment state" },
    { method: "GET", path: "/meta", description: "Platform metadata and pipeline posture" },
    { method: "POST", path: "/predict/gene-effect", description: "Compound-to-gene regulation prediction" },
    { method: "POST", path: "/search/reverse-signature", description: "Candidate ranking against expression goals" },
  ];

  return (
    <div className="workspace-grid api-grid">
      <section className="glass-panel api-hero-panel">
        <div className="section-heading">
          <p className="eyebrow">API control room</p>
          <h2>Runtime contract surface</h2>
        </div>
        <div className="docs-grid">
          <article>
            <span className="docs-label">Base URL</span>
            <strong>{API_BASE}</strong>
          </article>
          <article>
            <span className="docs-label">Swagger UI</span>
            <a href={API_DOCS_URL} target="_blank" rel="noreferrer">{API_DOCS_URL}</a>
          </article>
          <article>
            <span className="docs-label">OpenAPI</span>
            <a href={`${API_BASE}/openapi.json`} target="_blank" rel="noreferrer">{`${API_BASE}/openapi.json`}</a>
          </article>
          <article>
            <span className="docs-label">Protection model</span>
            <p>{(meta?.security_modes ?? ["api-key", "rate-limit", "request-id", "research-use-only"]).join(" · ")}</p>
          </article>
        </div>
      </section>

      <section className="glass-panel endpoint-panel">
        <div className="section-heading">
          <p className="eyebrow">Endpoints</p>
          <h2>Live operator surface</h2>
        </div>
        <div className="endpoint-table">
          {endpoints.map(({ method, path, description }) => (
            <article key={path} className="endpoint-row">
              <span className={`method-pill method-${method.toLowerCase()}`}>{method}</span>
              <div>
                <strong>{path}</strong>
                <p>{description}</p>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="glass-panel docs-panel">
        <div className="section-heading">
          <p className="eyebrow">Contract posture</p>
          <h2>Documentation quality</h2>
        </div>
        <div className="timeline">
          <article className="timeline-row">
            <span className="timeline-index">01</span>
            <div>
              <strong>Tagged routes</strong>
              <p>Operations, platform, and inference surfaces are grouped in Swagger.</p>
            </div>
          </article>
          <article className="timeline-row">
            <span className="timeline-index">02</span>
            <div>
              <strong>Examples</strong>
              <p>Request models publish concrete payload examples for assay and reversal flows.</p>
            </div>
          </article>
          <article className="timeline-row">
            <span className="timeline-index">03</span>
            <div>
              <strong>Responses</strong>
              <p>Response semantics and operational status codes are exposed in the live schema.</p>
            </div>
          </article>
        </div>
      </section>
    </div>
  );
}
