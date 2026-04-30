import type { GeneEffectResponse } from "../types";
import { confidenceTone } from "../utils";

interface PredictionSurfaceProps {
  predictionResponse: GeneEffectResponse | null;
  wetLabMode: boolean;
}

export default function PredictionSurface({ predictionResponse, wetLabMode }: PredictionSurfaceProps) {
  if (!predictionResponse) {
    return <p className="empty-state">No assay has run yet. Submit the current panel to populate the readout matrix.</p>;
  }

  if (!wetLabMode) {
    return (
      <div className="sf-gene-grid">
        {predictionResponse.predictions.map((prediction) => (
          <article key={prediction.gene} className="sf-card sf-card-data">
            <div className="sf-scan-line" />
            <div className="sf-card-top">
              <div>
                <strong className="sf-gene">{prediction.gene}</strong>
                <p className="sf-rationale">{prediction.rationale}</p>
              </div>
              <span className={`sf-pill sf-pill-${prediction.direction}`}>{prediction.direction}</span>
            </div>
            <div className="sf-bars">
              <div className="sf-bar-row">
                <span className="sf-bar-label">Up-regulation</span>
                <div className="sf-bar-track">
                  <span className="sf-bar-fill sf-bar-fill-amber" style={{ width: `${prediction.up_probability * 100}%` }} />
                </div>
                <span className="sf-bar-value">{prediction.up_probability.toFixed(2)}</span>
              </div>
              <div className="sf-bar-row">
                <span className="sf-bar-label">Down-regulation</span>
                <div className="sf-bar-track">
                  <span className="sf-bar-fill sf-bar-fill-violet" style={{ width: `${prediction.down_probability * 100}%` }} />
                </div>
                <span className="sf-bar-value">{prediction.down_probability.toFixed(2)}</span>
              </div>
            </div>
            <div className="sf-card-foot">
              <span className={`sf-confidence sf-confidence-${confidenceTone(prediction.confidence)}`}>
                confidence {prediction.confidence.toFixed(2)}
              </span>
            </div>
          </article>
        ))}
      </div>
    );
  }

  return (
    <div className="sf-gene-grid sf-gene-grid-wet">
      {predictionResponse.predictions.map((prediction) => (
        <article key={prediction.gene} className={`sf-card sf-card-wet sf-card-wet-${prediction.direction}`}>
          <div className="sf-wet-copy">
            <span className="sf-label">Gene node</span>
            <strong>{prediction.gene}</strong>
            <p>{prediction.direction} signal in simulated wet-lab view</p>
          </div>
          <div className="sf-wet-ring">
            <span>{prediction.confidence.toFixed(2)}</span>
          </div>
        </article>
      ))}
    </div>
  );
}
