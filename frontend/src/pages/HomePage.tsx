import { Link } from "react-router-dom";
import { workspaces } from "../constants";

export default function HomePage() {
  const activity = [72, 48, 90, 56, 84, 62, 78, 52, 88, 64, 80, 58];

  return (
    <div className="workspace-grid home-grid">
      <section className="glass-panel home-playground">
        <div className="home-playground-head">
          <p className="eyebrow">SignalForge Playground</p>
          <h1>Tools live here. Pick one and jump in.</h1>
        </div>

        <div className="home-orbital" aria-hidden="true">
          <span className="home-orbit home-orbit-a" />
          <span className="home-orbit home-orbit-b" />
          <span className="home-core" />
          <span className="home-ping home-ping-a" />
          <span className="home-ping home-ping-b" />
        </div>

        <div className="home-activity-strip" aria-label="Live activity">
          {activity.map((level, index) => (
            <span
              key={`${level}-${index}`}
              className="home-activity-bar"
              style={{ height: `${level}%`, animationDelay: `${index * 0.12}s` }}
            />
          ))}
        </div>
      </section>

      <section className="glass-panel home-modules">
        <div className="home-tools-grid">
          {workspaces.map((workspace) => (
            <Link key={workspace.id} to={`/${workspace.id}`} className="home-tool-card module-link-card">
              <div className="home-tool-topline">
                <span className="home-tool-kicker">{workspace.kicker}</span>
                <span className="home-tool-live">
                  <span className="home-live-dot" />
                  live
                </span>
              </div>
              <strong>{workspace.title}</strong>
              <div className="home-tool-meter" aria-hidden="true">
                <span />
              </div>
              <small>{workspace.description}</small>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
