/**
 * TalentRank AI API client.
 * Talks to FastAPI backend at VITE_API_BASE_URL (default http://localhost:8000).
 */
import type { ApiResponse, Candidate, DashboardStats, RankRequest, RankResponse, RankingSession, HoneypotListResponse, DistributionData, ConfigWeights } from "./types";

const isServer = typeof window === "undefined";
const BASE = isServer ? "http://127.0.0.1:8000" : "/api_proxy";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
      ...init,
    });
  } catch (err) {
    console.error(`Fetch failed to ${BASE}${path}. Check if backend is running and CORS is allowed.`, err);
    throw new Error(`Failed to fetch from backend. Ensure backend is running and you have restarted your frontend dev server.`);
  }
  
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  const json = (await res.json()) as ApiResponse<T> | T;
  if (json && typeof json === "object" && "data" in (json as ApiResponse<T>)) {
    return (json as ApiResponse<T>).data;
  }
  return json as T;
}

export const api = {
  async dashboard(): Promise<DashboardStats> {
    return request<DashboardStats>("/analytics/dashboard");
  },
  async rank(req: RankRequest): Promise<RankResponse> {
    return request<RankResponse>("/candidates/rank", { method: "POST", body: JSON.stringify(req) });
  },
  async candidate(id: string): Promise<Candidate> {
    return request<Candidate>(`/candidates/${id}`);
  },
  async compare(ids: string[]): Promise<Candidate[]> {
    return request<Candidate[]>("/candidates/compare", { method: "POST", body: JSON.stringify({ candidate_ids: ids }) });
  },
  async session(): Promise<RankingSession> {
    return request<RankingSession>("/sessions/active");
  },
  async honeypots(): Promise<HoneypotListResponse> {
    return request<HoneypotListResponse>("/analytics/honeypots");
  },
  async distributions(): Promise<DistributionData> {
    return request<DistributionData>("/analytics/distributions");
  },
  async getConfig(): Promise<ConfigWeights> {
    return request<ConfigWeights>("/config");
  },
  async updateConfig(weights: ConfigWeights): Promise<{status: string}> {
    return request<{status: string}>("/config/weights", { method: "POST", body: JSON.stringify(weights) });
  },
  async exportCsv(): Promise<string> {
    const res = await fetch(`${BASE}/export/csv`);
    if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
    return res.text();
  }
};
