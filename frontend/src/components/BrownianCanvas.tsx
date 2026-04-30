import { useEffect, useRef } from "react";

export default function BrownianCanvas() {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let w = window.innerWidth;
    let h = window.innerHeight;
    canvas.width = w;
    canvas.height = h;

    // Cosmic Bioluminescence palette: Electric Cyan · Plasma Magenta · Amethyst
    const PALETTES: Array<[number, number, number]> = [
      [34, 211, 238],   // Electric Cyan
      [232, 121, 249],  // Plasma Magenta
      [139, 92, 246],   // Amethyst Violet
    ];

    type Dot = {
      x: number; y: number; vx: number; vy: number;
      rgb: [number, number, number]; r: number; phase: number; spd: number;
    };

    const dots: Dot[] = Array.from({ length: 80 }, () => ({
      x: Math.random() * w,
      y: Math.random() * h,
      vx: (Math.random() - 0.5) * 0.45,
      vy: (Math.random() - 0.5) * 0.45,
      rgb: PALETTES[Math.floor(Math.random() * PALETTES.length)]!,
      r: Math.random() * 2.2 + 0.6,
      phase: Math.random() * Math.PI * 2,
      spd: Math.random() * 0.24 + 0.06,
    }));

    let t = 0;
    let raf: number;

    function frame() {
      t += 0.006;
      ctx!.clearRect(0, 0, w, h);

      for (const d of dots) {
        const angle =
          Math.sin(t * d.spd + d.phase) * Math.PI * 2 +
          Math.cos(t * d.spd * 0.6 + d.phase) * Math.PI;
        d.vx += Math.cos(angle) * 0.006;
        d.vy += Math.sin(angle) * 0.006;
        d.vx *= 0.984;
        d.vy *= 0.984;
        d.x += d.vx;
        d.y += d.vy;
        if (d.x < 0) { d.x = 0; d.vx = Math.abs(d.vx); }
        if (d.x > w) { d.x = w; d.vx = -Math.abs(d.vx); }
        if (d.y < 0) { d.y = 0; d.vy = Math.abs(d.vy); }
        if (d.y > h) { d.y = h; d.vy = -Math.abs(d.vy); }
      }

      // Draw connection lines between close particles
      for (let i = 0; i < dots.length; i++) {
        for (let j = i + 1; j < dots.length; j++) {
          const a = dots[i]!;
          const b = dots[j]!;
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 130) {
            const alpha = (1 - dist / 130) * 0.06;
            ctx!.strokeStyle = `rgba(${a.rgb[0]},${a.rgb[1]},${a.rgb[2]},${alpha})`;
            ctx!.lineWidth = 0.5;
            ctx!.beginPath();
            ctx!.moveTo(a.x, a.y);
            ctx!.lineTo(b.x, b.y);
            ctx!.stroke();
          }
        }
      }

      // Draw glow halo then solid dot
      for (const d of dots) {
        const grd = ctx!.createRadialGradient(d.x, d.y, 0, d.x, d.y, d.r * 5);
        grd.addColorStop(0, `rgba(${d.rgb[0]},${d.rgb[1]},${d.rgb[2]},0.18)`);
        grd.addColorStop(1, `rgba(${d.rgb[0]},${d.rgb[1]},${d.rgb[2]},0)`);
        ctx!.fillStyle = grd;
        ctx!.beginPath();
        ctx!.arc(d.x, d.y, d.r * 5, 0, Math.PI * 2);
        ctx!.fill();

        ctx!.fillStyle = `rgba(${d.rgb[0]},${d.rgb[1]},${d.rgb[2]},0.55)`;
        ctx!.beginPath();
        ctx!.arc(d.x, d.y, d.r, 0, Math.PI * 2);
        ctx!.fill();
      }

      raf = requestAnimationFrame(frame);
    }

    frame();

    function onResize() {
      w = window.innerWidth;
      h = window.innerHeight;
      canvas!.width = w;
      canvas!.height = h;
    }

    window.addEventListener("resize", onResize);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
    };
  }, []);

  return <canvas ref={ref} className="brownian-canvas" aria-hidden="true" />;
}
