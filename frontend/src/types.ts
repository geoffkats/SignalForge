export type GeneEffectPrediction = {
  gene: string;
  direction: "up" | "down" | "neutral";
  up_probability: number;
  down_probability: number;
  confidence: number;
  rationale: string;
};

export type GeneEffectResponse = {
  model_version: string;
  predictions: GeneEffectPrediction[];
  audit_id: string;
};

export type RankedCompound = {
  compound_id: string;
  compound_name: string;
  smiles: string;
  reversal_score: number;
  explanation: string;
};

export type ReverseSignatureResponse = {
  model_version: string;
  results: RankedCompound[];
  audit_id: string;
};

export type MetaResponse = {
  app_name: string;
  model_version: string;
  training_status: string;
  training_metrics: Record<string, number>;
  metrics_source: string | null;
  security_modes: string[];
  pipeline_stages: string[];
};