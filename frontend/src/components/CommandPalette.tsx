import { useEffect, useRef, useState } from "react";

interface CommandAction {
  id: string;
  label: string;
  hint: string;
  run: () => void;
}

interface CommandPaletteProps {
  actions: CommandAction[];
  query: string;
  onQueryChange: (q: string) => void;
  onRun: (action: CommandAction) => void;
  onClose: () => void;
}

export default function CommandPalette({ actions, query, onQueryChange, onRun, onClose }: CommandPaletteProps) {
  const [focusedIndex, setFocusedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const filtered = actions.filter((action) => {
    const q = query.trim().toLowerCase();
    if (!q) return true;
    return `${action.label} ${action.hint}`.toLowerCase().includes(q);
  });

  // Reset focus when filter changes
  useEffect(() => { setFocusedIndex(0); }, [query]);

  // Keyboard navigation
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setFocusedIndex((i) => Math.min(i + 1, filtered.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setFocusedIndex((i) => Math.max(i - 1, 0));
      } else if (e.key === "Enter") {
        const action = filtered[focusedIndex];
        if (action) onRun(action);
      }
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [filtered, focusedIndex, onRun]);

  return (
    <div className="command-palette-backdrop" role="presentation" onClick={onClose}>
      <section
        className="glass-panel command-palette"
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="command-palette-head">
          <span className="docs-label">⌘ Command palette</span>
          <strong>Jump between labs and controls</strong>
        </div>
        <input
          ref={inputRef}
          autoFocus
          className="command-input"
          placeholder="Type a command, workspace, or control…"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          aria-autocomplete="list"
          aria-controls="command-list"
        />
        <div id="command-list" className="command-list" role="listbox">
          {filtered.map((action, i) => (
            <button
              key={action.id}
              type="button"
              role="option"
              aria-selected={i === focusedIndex}
              className={`command-item${i === focusedIndex ? " focused" : ""}`}
              onClick={() => onRun(action)}
              onMouseEnter={() => setFocusedIndex(i)}
            >
              <strong>{action.label}</strong>
              <span>{action.hint}</span>
            </button>
          ))}
          {filtered.length === 0 ? (
            <p className="empty-state">No matching commands.</p>
          ) : null}
        </div>
        <p style={{ marginTop: 12, fontSize: "0.74rem", color: "var(--muted)", fontFamily: "'IBM Plex Mono', monospace" }}>
          ↑ ↓ navigate &nbsp;·&nbsp; ↵ execute &nbsp;·&nbsp; esc dismiss
        </p>
      </section>
    </div>
  );
}
