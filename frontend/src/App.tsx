import { FormEvent, useEffect, useState } from "react";
import { NavLink, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";

import { API_DOCS_URL, fetchMeta, predictGeneEffects, searchReverseSignature } from "./lib/api";
import type { GeneEffectResponse, MetaResponse, ReverseSignatureResponse } from "./types";
import { defaultSmiles, workspaces, type WorkspaceId } from "./constants";
import { splitGenes } from "./utils";

import BrownianCanvas from "./components/BrownianCanvas";
import CommandPalette from "./components/CommandPalette";
import ErrorBoundary from "./components/ErrorBoundary";
import ToolPlaygroundPage from "./pages/ToolPlaygroundPage";
import OverviewPage from "./pages/OverviewPage";
import AssayPage from "./pages/AssayPage";
import AtlasPage from "./pages/AtlasPage";
import ApiPage from "./pages/ApiPage";

function workspaceFromPath(pathname: string): WorkspaceId | null {
  if (pathname === "/overview") return "overview";
  if (pathname === "/assay") return "assay";
  if (pathname === "/atlas") return "atlas";
  if (pathname === "/api") return "api";
  return null;
}

export default function App() {
  const navigate = useNavigate();
  const location = useLocation();

  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [wetLabMode, setWetLabMode] = useState(false);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const [commandQuery, setCommandQuery] = useState("");
  const [smiles, setSmiles] = useState(defaultSmiles);
  // Androgen response + LINCS L1000 landmark gene panel (LNCaP / CRPC context)
  const [geneInput, setGeneInput] = useState("AR, KLK3, TMPRSS2, NKX3-1, EZH2, SYK, MYC, EGR1, PTEN, CCNA2");
  // Reverse-signature defaults: oncogenic up-regulated state → expect antiandrogens / HDAC inhibitors
  const [upInput, setUpInput] = useState("AR, KLK3, TMPRSS2, EZH2");
  // Tumor suppressors / growth-arrest genes to restore
  const [downInput, setDownInput] = useState("PTEN, NKX3-1, CDKN1A, LCN2");
  const [meta, setMeta] = useState<MetaResponse | null>(null);
  const [predictionResponse, setPredictionResponse] = useState<GeneEffectResponse | null>(null);
  const [reverseResponse, setReverseResponse] = useState<ReverseSignatureResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPredicting, setIsPredicting] = useState(false);
  const [isSearching, setIsSearching] = useState(false);

  const geneTokens = splitGenes(geneInput);
  const suppressedGenes = splitGenes(upInput);
  const restoredGenes = splitGenes(downInput);
  const meanConfidence = predictionResponse
    ? predictionResponse.predictions.reduce((sum, p) => sum + p.confidence, 0) / predictionResponse.predictions.length
    : 0;
  const strongestReversal = reverseResponse?.results[0];
  const activeWorkspace = workspaceFromPath(location.pathname);
  const activeWorkspaceMeta = activeWorkspace
    ? (workspaces.find((w) => w.id === activeWorkspace) ?? workspaces[0]!)
    : null;
  const isToolWorkspace = activeWorkspace === "assay" || activeWorkspace === "atlas";
  const systemHealth = meta ? "online" : "degraded";

  function setActiveWorkspace(id: WorkspaceId) {
    navigate(`/${id}`);
  }

  const commandActions = [
    { id: "home", label: "Open workspace home", hint: "Start a new analysis", run: () => navigate("/") },
    { id: "assay", label: "Open Assay", hint: "Compound → gene effects", run: () => navigate("/assay") },
    { id: "atlas", label: "Open Atlas", hint: "Signature → ranked compounds", run: () => navigate("/atlas") },
    { id: "toggle-mode", label: wetLabMode ? "Switch to Data view" : "Switch to Wet Lab view", hint: "Toggle assay result presentation", run: () => setWetLabMode((c) => !c) },
    { id: "refresh", label: "Refresh model status", hint: "Reload /meta", run: () => { void fetchMeta().then(setMeta).catch(() => setMeta(null)); } },
    { id: "api", label: "Open API", hint: "Endpoint contracts", run: () => navigate("/api") },
  ];

  useEffect(() => {
    void fetchMeta().then(setMeta).catch(() => setMeta(null));
  }, []);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setCommandPaletteOpen((c) => !c);
        setCommandQuery("");
      }
      if (event.key === "Escape") setCommandPaletteOpen(false);
      if (!event.metaKey && !event.ctrlKey && !event.altKey) {
        if (event.key === "0") navigate("/");
        if (event.key === "1") navigate("/assay");
        if (event.key === "2") navigate("/atlas");
        if (event.key === "3") navigate("/overview");
        if (event.key === "4") navigate("/api");
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [navigate]);

  useEffect(() => {
    // Give Assay/Atlas full width by default; Overview keeps the nav open.
    if (location.pathname === "/assay" || location.pathname === "/atlas") {
      setIsSidebarCollapsed(true);
    }
  }, [location.pathname]);

  async function handlePredict(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsPredicting(true);
    setError(null);
    try {
      const response = await predictGeneEffects(smiles, geneTokens);
      setPredictionResponse(response);
      navigate("/assay");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Prediction failed");
    } finally {
      setIsPredicting(false);
    }
  }

  async function handleReverseSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSearching(true);
    setError(null);
    try {
      const response = await searchReverseSignature(suppressedGenes, restoredGenes);
      setReverseResponse(response);
      navigate("/atlas");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reverse search failed");
    } finally {
      setIsSearching(false);
    }
  }

  async function handleRerunAssay() {
    setIsPredicting(true);
    setError(null);
    try {
      const response = await predictGeneEffects(smiles, geneTokens);
      setPredictionResponse(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Prediction failed");
    } finally {
      setIsPredicting(false);
    }
  }

  return (
    <div className={`app-shell ${isSidebarCollapsed ? "sidebar-collapsed" : ""}${isToolWorkspace ? " tool-mode" : ""}`}>
      {!isToolWorkspace ? <BrownianCanvas /> : null}
      {!isToolWorkspace ? (
        <div className="ambient-grid" aria-hidden="true">
          <span /><span /><span />
        </div>
      ) : null}

      <aside className="glass-panel nav-shell">
        <div className="brand-block">
          <p className="eyebrow">SignalForge</p>
          <h2>Workspace</h2>
          <p>Assay gene effects. Atlas reverse signatures.</p>
        </div>

        <nav className="workspace-nav" aria-label="Primary workspaces">
          <NavLink to="/" className={({ isActive }) => `workspace-link ${isActive ? "workspace-link-active" : ""}`}>
            <span>Home</span>
            <strong>Start</strong>
            <small>Jump into Assay or Atlas</small>
          </NavLink>
          {workspaces.filter((workspace) => workspace.id === "assay" || workspace.id === "atlas").map((workspace) => (
            <NavLink
              key={workspace.id}
              to={`/${workspace.id}`}
              className={({ isActive }) => `workspace-link ${isActive ? "workspace-link-active" : ""}`}
            >
              <span>{workspace.kicker}</span>
              <strong>{workspace.title}</strong>
              <small>{workspace.description}</small>
            </NavLink>
          ))}
        </nav>

        <div className="nav-status glass-panel inset-panel">
          <span className="docs-label">Status</span>
          <strong>{systemHealth}</strong>
          <div className="status-list">
            <article>
              <span>Model</span>
              <strong>{meta?.model_version ?? "unavailable"}</strong>
            </article>
            <article>
              <span>Mode</span>
              <strong>{meta?.inference_mode ?? "unknown"}</strong>
            </article>
          </div>
        </div>
      </aside>

      <div className="workspace-shell">
        <header className={`glass-panel command-bar${isToolWorkspace ? " command-bar-compact" : ""}`}>
          <div>
            <p className="eyebrow">{activeWorkspaceMeta?.kicker ?? "SignalForge"}</p>
            <h1>{activeWorkspaceMeta?.title ?? "Workspace"}</h1>
            {!isToolWorkspace ? (
              <p className="lede compact">
                {activeWorkspaceMeta?.description ?? "Open Assay or Atlas to run an analysis."}
              </p>
            ) : null}
          </div>
          <div className="command-actions">
            <button
              className="secondary-action"
              type="button"
              aria-pressed={isSidebarCollapsed}
              onClick={() => setIsSidebarCollapsed((collapsed) => !collapsed)}
            >
              {isSidebarCollapsed ? "Menu" : "Hide menu"}
            </button>
            <button className="secondary-action command-trigger" type="button" onClick={() => setCommandPaletteOpen(true)}>
              ⌘K
            </button>
            {!isToolWorkspace ? (
              <button className="primary-action" type="button" onClick={() => void fetchMeta().then(setMeta).catch(() => setMeta(null))}>
                Refresh
              </button>
            ) : null}
            {location.pathname === "/api" ? (
              <a className="secondary-action" href={API_DOCS_URL} target="_blank" rel="noreferrer">
                Docs
              </a>
            ) : null}
          </div>
        </header>

        {!isToolWorkspace && activeWorkspace === "overview" ? (
          <section className="glass-panel summary-ribbon summary-ribbon-compact">
            <article>
              <span className="docs-label">Model</span>
              <strong>{meta?.model_version ?? "—"}</strong>
            </article>
            <article>
              <span className="docs-label">Mode</span>
              <strong>{meta?.inference_mode ?? "—"}</strong>
            </article>
            <article>
              <span className="docs-label">Training</span>
              <strong>{meta?.training_status ?? "unknown"}</strong>
            </article>
            <article>
              <span className="docs-label">Atlas</span>
              <strong>{meta?.atlas_size ?? "—"}</strong>
            </article>
          </section>
        ) : null}

        <ErrorBoundary>
        <Routes>
          <Route
            path="/"
            element={
              <ErrorBoundary>
              <ToolPlaygroundPage
                smiles={smiles}
                setSmiles={setSmiles}
                geneInput={geneInput}
                setGeneInput={setGeneInput}
                upInput={upInput}
                setUpInput={setUpInput}
                downInput={downInput}
                setDownInput={setDownInput}
                isPredicting={isPredicting}
                isSearching={isSearching}
                predictionResponse={predictionResponse}
                reverseResponse={reverseResponse}
                onPredict={handlePredict}
                onReverseSearch={handleReverseSearch}
              />
              </ErrorBoundary>
            }
          />
          <Route
            path="/overview"
            element={
              <OverviewPage
                meta={meta}
                geneCount={geneTokens.length}
                meanConfidence={meanConfidence}
                predictionRan={predictionResponse !== null}
                strongestReversal={strongestReversal}
                activeWorkspace="overview"
                setActiveWorkspace={setActiveWorkspace}
              />
            }
          />
          <Route
            path="/assay"
            element={
              <AssayPage
                smiles={smiles}
                setSmiles={setSmiles}
                geneInput={geneInput}
                setGeneInput={setGeneInput}
                geneTokens={geneTokens}
                meta={meta}
                predictionResponse={predictionResponse}
                isPredicting={isPredicting}
                wetLabMode={wetLabMode}
                setWetLabMode={setWetLabMode}
                meanConfidence={meanConfidence}
                onSubmit={handlePredict}
                onRerun={() => void handleRerunAssay()}
              />
            }
          />
          <Route
            path="/atlas"
            element={
              <AtlasPage
                upInput={upInput}
                setUpInput={setUpInput}
                downInput={downInput}
                setDownInput={setDownInput}
                suppressedGenes={suppressedGenes}
                restoredGenes={restoredGenes}
                reverseResponse={reverseResponse}
                isSearching={isSearching}
                atlasSize={meta?.atlas_size}
                onSubmit={handleReverseSearch}
              />
            }
          />
          <Route path="/api" element={<ErrorBoundary><ApiPage meta={meta} /></ErrorBoundary>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        </ErrorBoundary>

        {error ? <div className="error-banner" role="alert">{error}</div> : null}
      </div>

      {commandPaletteOpen ? (
        <CommandPalette
          actions={commandActions}
          query={commandQuery}
          onQueryChange={setCommandQuery}
          onRun={(action) => {
            action.run();
            setCommandPaletteOpen(false);
            setCommandQuery("");
          }}
          onClose={() => setCommandPaletteOpen(false)}
        />
      ) : null}
    </div>
  );
}
