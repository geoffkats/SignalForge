// Enzalutamide — androgen receptor antagonist (MDV3100)
// SMILES: clinically validated, LNCaP antiandrogen
export const defaultSmiles = "CC1(C(=O)Nc2cccc(c2)C#N)CS(=O)(=O)c2cc(C(F)(F)F)ccc2N1";
export const sampleCompound = "Enzalutamide (MDV3100)";
export const sampleTumorContext = "LNCaP · androgen receptor program · CRPC progression";

export type WorkspaceId = "overview" | "assay" | "atlas" | "api";

export const workspaces: Array<{ id: WorkspaceId; kicker: string; title: string; description: string }> = [
  {
    id: "overview",
    kicker: "Status",
    title: "Overview",
    description: "Model health, metrics, and recent run posture.",
  },
  {
    id: "assay",
    kicker: "Assay",
    title: "Assay",
    description: "Predict gene effects for a compound SMILES.",
  },
  {
    id: "atlas",
    kicker: "Atlas",
    title: "Atlas",
    description: "Rank compounds that reverse a gene signature.",
  },
  {
    id: "api",
    kicker: "API",
    title: "API",
    description: "Endpoint contracts and runtime surface.",
  },
];

export const moleculeNodes: ReadonlyArray<{ x: number; y: number }> = [
  { x: 12, y: 58 },
  { x: 25, y: 42 },
  { x: 40, y: 61 },
  { x: 54, y: 40 },
  { x: 68, y: 56 },
  { x: 80, y: 36 },
  { x: 87, y: 62 },
];

export const moleculeBonds: ReadonlyArray<readonly [number, number]> = [
  [0, 1],
  [1, 2],
  [2, 3],
  [3, 4],
  [4, 5],
  [4, 6],
];

export const readoutParticles: ReadonlyArray<{
  left: string;
  top: string;
  size: number;
  duration: string;
  delay: string;
  tone: "teal" | "amber" | "violet";
}> = [
  { left: "6%", top: "14%", size: 4, duration: "11s", delay: "-2s", tone: "teal" },
  { left: "18%", top: "62%", size: 5, duration: "13s", delay: "-7s", tone: "amber" },
  { left: "26%", top: "30%", size: 3, duration: "9s", delay: "-3s", tone: "violet" },
  { left: "38%", top: "78%", size: 6, duration: "15s", delay: "-5s", tone: "teal" },
  { left: "47%", top: "18%", size: 4, duration: "10s", delay: "-6s", tone: "amber" },
  { left: "56%", top: "42%", size: 5, duration: "14s", delay: "-1s", tone: "violet" },
  { left: "64%", top: "72%", size: 4, duration: "12s", delay: "-8s", tone: "teal" },
  { left: "73%", top: "22%", size: 6, duration: "16s", delay: "-4s", tone: "amber" },
  { left: "82%", top: "56%", size: 5, duration: "12s", delay: "-10s", tone: "violet" },
  { left: "90%", top: "34%", size: 4, duration: "11s", delay: "-6s", tone: "teal" },
];
