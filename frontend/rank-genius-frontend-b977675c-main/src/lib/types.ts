// Mirrors the TalentRank AI backend response shapes.

export interface ResponseMetadata {
  processing_time_ms: number;
  total_results: number | null;
  version: string;
}

export interface ApiResponse<T> {
  data: T;
  metadata: ResponseMetadata;
  errors: unknown[] | null;
}

export interface ScoreBreakdown {
  semantic: number;
  behavior: number;
  career: number;
  skill: number;
  risk: number;
  availability: number;
}

export interface EvidenceObject {
  id: string;
  type: "skill_match" | "career_signal" | "behavioral" | "risk" | "education" | "project";
  title: string;
  detail: string;
  weight: number; // 0-1
  source?: string;
}

export interface CareerEntry {
  company: string;
  role: string;
  start: string;
  end: string | null;
  highlights?: string[];
}

export interface Candidate {
  id: string;
  name: string;
  headline: string;
  location: string;
  years_experience: number;
  current_company: string;
  current_role: string;
  email?: string;
  avatar_seed: string;

  overall_score: number | null; // 0-100
  confidence: number | null; // 0-1
  risk_score: number | null; // 0-100 (higher = riskier)
  scores: ScoreBreakdown | null;

  matched_skills: string[];
  missing_skills: string[];
  all_skills: string[];

  strengths: string[] | null;
  weaknesses: string[] | null;
  risk_flags: string[] | null;

  availability: "open_to_work" | "passive" | "not_looking";
  notice_period_days: number;
  recommendation: "fast_track" | "strong_match" | "consider" | "review" | "reject" | null;
  recommendation_text: string | null;

  honeypot: boolean;
  honeypot_reasons?: string[] | null;

  hidden_gem_score?: number | null;
  career: CareerEntry[];
  education: { school: string; degree: string; year: number }[];
  evidence: EvidenceObject[] | null;
}

export interface RankRequest {
  job_description: string;
  top_k?: number;
}

export interface RankResponse {
  session_id: string;
  timestamp: string;
  job_description: string;
  candidates: Candidate[];
  total_pool: number;
  extracted: {
    skills: string[];
    min_years: number;
    education: string[];
    behavioral: string[];
  };
  analytics: Record<string, any>;
  hidden_gems: Candidate[];
  honeypots: Candidate[];
}

export interface DashboardStats {
  total_candidates: number;
  ai_candidates: number;
  open_to_work: number;
  avg_experience: number;
  honeypots_detected: number;
  recent_rankings: { id: string; jd_title: string; candidates: number; ts: string }[];
  performance: { latency_ms: number; throughput_qps: number };
}

export interface RankingSession extends RankResponse {}

export interface HoneypotCandidate {
  candidate_id: string;
  reasons: string[];
  honeypot_score: number;
}

export interface HoneypotListResponse {
  honeypots: HoneypotCandidate[];
}

export interface HistogramBin {
  label: string;
  count: number;
}

export interface DistributionData {
  skills: HistogramBin[];
  experience: HistogramBin[];
  company_size: HistogramBin[];
  education: HistogramBin[];
}

export interface ConfigWeights {
  semantic_weight: number;
  structured_weight: number;
  behavioral_weight: number;
  recency_weight: number;
}
