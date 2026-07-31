import type { GeneEffectResponse, MetaResponse, ReverseSignatureResponse } from "../types";

export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
export const API_DOCS_URL = `${API_BASE}/docs`;
const API_KEY = import.meta.env.VITE_SIGNALFORGE_API_KEY ?? "";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(API_KEY ? { "X-API-Key": API_KEY } : {}),
      ...(options?.headers ?? {}),
    },
  });

  if (!response.ok) {
    let detail = `API request failed with status ${response.status}`;

    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) {
        detail = payload.detail;
      }
    } catch {
      // Fall back to the status message when the response body is not JSON.
    }

    throw new Error(detail);
  }

  return response.json() as Promise<T>;
}

export function fetchMeta(): Promise<MetaResponse> {
  return request<MetaResponse>("/meta");
}

export function predictGeneEffects(smiles: string, genes: string[]): Promise<GeneEffectResponse> {
  return request<GeneEffectResponse>("/predict/gene-effect", {
    method: "POST",
    body: JSON.stringify({ smiles, genes }),
  });
}

export function searchReverseSignature(upGenes: string[], downGenes: string[]): Promise<ReverseSignatureResponse> {
  return request<ReverseSignatureResponse>("/search/reverse-signature", {
    method: "POST",
    body: JSON.stringify({ up_genes: upGenes, down_genes: downGenes, top_k: 20 }),
  });
}