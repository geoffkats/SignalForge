import { useEffect, useRef } from "react";

type ForceNode = {
  gene: string;
  tone: "up" | "down";
  x: number; y: number;
  vx: number; vy: number;
  tx: number; ty: number;
  phase: number;
};

interface ForceGraphProps {
  genes: Array<{ gene: string; tone: "up" | "down" }>;
  compound: string;
  score: number;
}

export default function ForceGraph({ genes, compound, score }: ForceGraphProps) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const rect = canvas.parentElement!.getBoundingClientRect();
    let w = rect.width;
    let h = Math.max(rect.height, 280);
    canvas.width = w;
    canvas.height = h;

    const cx = w / 2;
    const cy = h / 2;
    const orbitX = w * 0.34;
    const orbitY = h * 0.26;

    const nodes: ForceNode[] = genes.map((g, i) => {
      const angle = (i / Math.max(genes.length, 1)) * Math.PI * 2 - Math.PI / 2;
      const tx = cx + Math.cos(angle) * orbitX;
      const ty = cy + Math.sin(angle) * orbitY;
      return { ...g, x: tx + (Math.random() - 0.5) * 24, y: ty + (Math.random() - 0.5) * 24, vx: 0, vy: 0, tx, ty, phase: Math.random() * Math.PI * 2 };
    });

    let t = 0;
    let raf: number;

    function frame() {
      t += 0.012;
      ctx!.clearRect(0, 0, w, h);

      for (const n of nodes) {
        const noiseAngle = Math.sin(t * 0.7 + n.phase) * Math.PI * 2 + Math.cos(t * 0.4 + n.phase * 1.3) * Math.PI;
        n.vx += (n.tx - n.x) * 0.022 + Math.cos(noiseAngle) * 0.18;
        n.vy += (n.ty - n.y) * 0.022 + Math.sin(noiseAngle) * 0.18;
        for (const m of nodes) {
          if (m === n) continue;
          const dx = n.x - m.x;
          const dy = n.y - m.y;
          const distSq = dx * dx + dy * dy + 1;
          const force = 900 / distSq;
          n.vx += (dx / Math.sqrt(distSq)) * force;
          n.vy += (dy / Math.sqrt(distSq)) * force;
        }
        n.vx *= 0.88;
        n.vy *= 0.88;
        n.x += n.vx;
        n.y += n.vy;
        n.x = Math.max(52, Math.min(w - 52, n.x));
        n.y = Math.max(20, Math.min(h - 20, n.y));
      }

      // Edges — magenta for up, violet for down
      for (const n of nodes) {
        const upColor = n.tone === "up" ? [232, 121, 249] : [139, 92, 246];
        const grad = ctx!.createLinearGradient(cx, cy, n.x, n.y);
        grad.addColorStop(0, `rgba(34,211,238,0.28)`);
        grad.addColorStop(1, `rgba(${upColor[0]},${upColor[1]},${upColor[2]},0.55)`);
        ctx!.strokeStyle = grad;
        ctx!.lineWidth = 0.75;
        ctx!.setLineDash([4, 6]);
        ctx!.beginPath();
        ctx!.moveTo(cx, cy);
        ctx!.lineTo(n.x, n.y);
        ctx!.stroke();
      }
      ctx!.setLineDash([]);

      // Gene nodes
      for (const n of nodes) {
        const isUp = n.tone === "up";
        const rgb = isUp ? [232, 121, 249] : [139, 92, 246];
        const grd = ctx!.createRadialGradient(n.x, n.y, 0, n.x, n.y, 32);
        grd.addColorStop(0, `rgba(${rgb[0]},${rgb[1]},${rgb[2]},0.22)`);
        grd.addColorStop(1, `rgba(${rgb[0]},${rgb[1]},${rgb[2]},0)`);
        ctx!.fillStyle = grd;
        ctx!.beginPath();
        ctx!.arc(n.x, n.y, 32, 0, Math.PI * 2);
        ctx!.fill();
        ctx!.strokeStyle = `rgba(${rgb[0]},${rgb[1]},${rgb[2]},0.52)`;
        ctx!.lineWidth = 0.5;
        ctx!.beginPath();
        ctx!.arc(n.x, n.y, 22, 0, Math.PI * 2);
        ctx!.stroke();
        ctx!.fillStyle = `rgba(${rgb[0]},${rgb[1]},${rgb[2]},0.12)`;
        ctx!.beginPath();
        ctx!.arc(n.x, n.y, 22, 0, Math.PI * 2);
        ctx!.fill();
        ctx!.fillStyle = "#eef2ff";
        ctx!.font = "bold 11px 'Space Grotesk','IBM Plex Sans',sans-serif";
        ctx!.textAlign = "center";
        ctx!.textBaseline = "middle";
        ctx!.fillText(n.gene, n.x, n.y - 2);
        ctx!.fillStyle = `rgba(${rgb[0]},${rgb[1]},${rgb[2]},0.75)`;
        ctx!.font = "9px 'IBM Plex Mono','Consolas',monospace";
        ctx!.fillText(isUp ? "restore" : "suppress", n.x, n.y + 10);
      }

      // Core compound node — cyan
      const pulse = 0.3 + Math.sin(t * 1.4) * 0.15;
      const coreGrd = ctx!.createRadialGradient(cx, cy, 0, cx, cy, 55);
      coreGrd.addColorStop(0, "rgba(34,211,238,0.28)");
      coreGrd.addColorStop(1, "rgba(2,12,15,0)");
      ctx!.fillStyle = coreGrd;
      ctx!.beginPath();
      ctx!.arc(cx, cy, 55, 0, Math.PI * 2);
      ctx!.fill();
      ctx!.strokeStyle = `rgba(34,211,238,${pulse})`;
      ctx!.lineWidth = 0.5;
      ctx!.beginPath();
      ctx!.arc(cx, cy, 44, 0, Math.PI * 2);
      ctx!.stroke();
      ctx!.fillStyle = "rgba(34,211,238,0.1)";
      ctx!.beginPath();
      ctx!.arc(cx, cy, 44, 0, Math.PI * 2);
      ctx!.fill();
      ctx!.fillStyle = "#eef2ff";
      ctx!.font = "bold 12px 'Space Grotesk','IBM Plex Sans',sans-serif";
      ctx!.textAlign = "center";
      ctx!.textBaseline = "middle";
      ctx!.fillText(compound, cx, cy - 6);
      ctx!.fillStyle = "#f0abfc";
      ctx!.font = "500 11px 'IBM Plex Mono','Consolas',monospace";
      ctx!.fillText(score.toFixed(2), cx, cy + 10);

      raf = requestAnimationFrame(frame);
    }

    frame();

    function onResize() {
      const r = canvas!.parentElement!.getBoundingClientRect();
      w = r.width;
      h = Math.max(r.height, 280);
      canvas!.width = w;
      canvas!.height = h;
    }

    window.addEventListener("resize", onResize);
    return () => { cancelAnimationFrame(raf); window.removeEventListener("resize", onResize); };
  }, [genes, compound, score]);

  return <canvas ref={ref} style={{ width: "100%", height: "100%", display: "block" }} />;
}
