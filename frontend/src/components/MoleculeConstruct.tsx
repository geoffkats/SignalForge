import { useEffect, useRef, useState } from "react";
import SmilesDrawer, { type Drawer as DrawerType } from "smiles-drawer";

interface MoleculeConstructProps {
  smiles: string;
  isPredicting: boolean;
}

// Holographic teal/amber palette — dark viewport embedded in glass panel
const HOLO_THEME = {
  C: "#7dd3d8",
  N: "#818cf8",
  O: "#f59e0b",
  F: "#34d399",
  CL: "#34d399",
  BR: "#fb923c",
  I: "#c084fc",
  P: "#f97316",
  S: "#fbbf24",
  B: "#93c5fd",
  SI: "#a5b4fc",
  H: "#94a3b8",
  BACKGROUND: "#060e1e",
};

export default function MoleculeConstruct({ smiles, isPredicting }: MoleculeConstructProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const drawerRef = useRef<DrawerType | null>(null);
  const [parseError, setParseError] = useState(false);
  const [atomCount, setAtomCount] = useState(0);

  // Initialise drawer once
  useEffect(() => {
    drawerRef.current = new SmilesDrawer.Drawer({
      width: 420,
      height: 260,
      bondThickness: 1.6,
      bondLength: 28,
      shortBondLength: 0.85,
      bondSpacing: 5,
      atomVisualization: "default",
      terminalCarbons: true,
      compactDrawing: false,
      fontSizeLarge: 12,
      fontSizeSmall: 8,
      padding: 24,
      themes: { holo: HOLO_THEME },
    });
  }, []);

  // Re-render whenever the SMILES string changes
  useEffect(() => {
    if (!drawerRef.current || !smiles) return;
    setParseError(false);

    SmilesDrawer.parse(
      smiles,
      (tree) => {
        drawerRef.current!.draw(tree, canvasRef.current, "holo", false);
        // Derive atom count from SMILES heavy-atom uppercase letters
        const heavyAtoms = smiles.match(/[A-Z][a-z]?/g) ?? [];
        setAtomCount(heavyAtoms.length);
      },
      () => {
        setParseError(true);
        // Clear canvas on error
        const ctx = canvasRef.current?.getContext("2d");
        if (ctx && canvasRef.current) {
          ctx.fillStyle = HOLO_THEME.BACKGROUND;
          ctx.fillRect(0, 0, canvasRef.current.width, canvasRef.current.height);
        }
      }
    );
  }, [smiles]);

  return (
    <section className={`glass-panel molecule-panel ${isPredicting ? "is-active-scan" : ""}`}>
      <div className="section-heading split-heading">
        <div>
          <p className="eyebrow">Molecular scaffold</p>
          <h2>2D structure projection</h2>
        </div>
        <div className="mol-meta-row">
          <div className="mini-stat mono-stat">
            <span>Heavy atoms</span>
            <strong>{atomCount || "—"}</strong>
          </div>
          <div className="mini-stat mono-stat">
            <span>SMILES length</span>
            <strong>{smiles.length}</strong>
          </div>
        </div>
      </div>

      <div className="holo-viewport">
        {isPredicting && <div className="holo-scan-line" />}
        <div className="holo-corner holo-corner--tl" />
        <div className="holo-corner holo-corner--tr" />
        <div className="holo-corner holo-corner--bl" />
        <div className="holo-corner holo-corner--br" />
        {parseError ? (
          <div className="holo-error">
            <span className="mono-label">SMILES parse error</span>
            <code className="holo-smiles-code">{smiles}</code>
          </div>
        ) : (
          <canvas ref={canvasRef} width={420} height={260} className="holo-canvas" />
        )}
      </div>

      <div className="smiles-terminal">
        <span className="docs-label">SMILES string</span>
        <code>{smiles}</code>
      </div>
    </section>
  );
}
