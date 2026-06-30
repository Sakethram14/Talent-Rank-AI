import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, Chip, SectionTitle } from "@/components/ui-primitives";
import { toast } from "sonner";

export const Route = createFileRoute("/_authenticated/job-analysis")({
  head: () => ({
    meta: [
      { title: "Job Analysis — TalentRank AI" },
      { name: "description", content: "Paste a job description and let the intelligence layer extract skills, requirements, and behavioral expectations." },
    ],
  }),
  component: JobAnalysisPage,
});

const SAMPLE_JD = `Senior Machine Learning Engineer — RAG Systems

We're hiring a Senior ML Engineer to lead our retrieval-augmented generation stack.

Responsibilities:
- Design and ship production-grade RAG pipelines with embeddings, vector search (FAISS), and re-ranking
- Build evaluation harnesses for LLM systems and own offline metrics
- Partner with platform engineers on scalable Python services

Requirements:
- 5+ years building ML systems in production
- Strong Python and PyTorch
- Deep familiarity with embeddings, LLMs, FAISS / vector retrieval
- Experience with Distributed Systems, Kafka, Kubernetes
- Bias for action, ownership, and clear written communication`;

type Stage = { id: string; label: string; detail: string };
const STAGES: Stage[] = [
  { id: "parse", label: "Parsing job description", detail: "Tokenizing, normalizing requirements" },
  { id: "extract", label: "Extracting skills & requirements", detail: "NER + structured competency mapping" },
  { id: "embed", label: "Generating query embedding", detail: "all-MiniLM-L6-v2 → 384d" },
  { id: "dense", label: "Dense retrieval over 100k candidates", detail: "FAISS HNSW top-1000" },
  { id: "lexical", label: "Lexical retrieval", detail: "BM25 top-1000" },
  { id: "fuse", label: "Hybrid fusion", detail: "Reciprocal Rank Fusion (k=60)" },
  { id: "rank", label: "Ranking & explainability", detail: "Score breakdown + evidence objects" },
];

function JobAnalysisPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [jd, setJd] = useState("");
  const [stageIdx, setStageIdx] = useState(-1);

  const rank = useMutation({
    mutationFn: async (payload: string) => {
      // Drive the pipeline animation
      for (let i = 0; i < STAGES.length; i++) {
        setStageIdx(i);
        await new Promise((res) => setTimeout(res, 280 + Math.random() * 220));
      }
      const r = await api.rank({ job_description: payload, top_k: 50 });
      try {
        sessionStorage.setItem("tr:lastRank", JSON.stringify(r));
      } catch (e) {
        console.warn("Could not save to sessionStorage (likely quota exceeded). Proceeding anyway.", e);
      }
      return r;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries();
      if (typeof window !== "undefined" && data) {
        try {
          const recent = localStorage.getItem("tr:recentSearches");
          const list = recent ? JSON.parse(recent) : [];
          const newSearch = {
            id: data.session_id,
            timestamp: data.timestamp || new Date().toISOString(),
            job_description: data.job_description,
            candidates_count: data.candidates ? data.candidates.length : 0,
            full_data: data,
          };
          const updated = [newSearch, ...list.filter((s: any) => s.job_description !== data.job_description)].slice(0, 10);
          localStorage.setItem("tr:recentSearches", JSON.stringify(updated));
        } catch (e) {
          console.warn("Could not save to recent searches:", e);
        }
      }
      navigate({ to: "/rankings" });
    },
    onError: (err) => {
      console.error("Analysis Error:", err);
      toast.error("Analysis failed", { description: err instanceof Error ? err.message : String(err) });
      setStageIdx(-1);
    },
  });

  const running = rank.isPending;

  return (
    <div className="max-w-[1400px] mx-auto p-8 grid grid-cols-1 lg:grid-cols-5 gap-6">
      <div className="lg:col-span-3 space-y-4">
        <div>
          <h1 className="font-display text-3xl font-medium text-zinc-100">Job Analysis</h1>
          <p className="text-zinc-400 mt-2">Paste a job description. The intelligence layer extracts the skill graph and ranks 100,000 candidates in seconds.</p>
        </div>

        <Card className="overflow-hidden">
          <div className="flex items-center justify-between px-4 py-2.5 border-b border-white/5 bg-white/[0.02]">
            <div className="text-xs text-zinc-500 font-mono">job_description.md</div>
            <button
              type="button"
              onClick={() => setJd(SAMPLE_JD)}
              className="text-xs text-accent hover:text-indigo-300 transition-colors"
            >
              Load sample JD
            </button>
          </div>
          <textarea
            value={jd}
            onChange={(e) => setJd(e.target.value)}
            placeholder="Paste a job description here. We support markdown, plain text, or a recruiter brief…"
            rows={18}
            className="w-full bg-transparent text-sm text-zinc-100 font-mono p-5 outline-none resize-y placeholder:text-zinc-600"
          />
        </Card>

        <div className="flex items-center justify-between">
          <div className="text-xs text-zinc-500">{jd.trim().split(/\s+/).filter(Boolean).length} words</div>
          <button
            onClick={() => rank.mutate(jd.trim() || SAMPLE_JD)}
            disabled={running}
            className="inline-flex items-center gap-2 bg-accent text-white px-5 py-2.5 rounded-lg text-sm font-medium ring-1 ring-accent/50 hover:bg-accent/90 disabled:opacity-50 transition-colors shadow-lg shadow-accent/20"
          >
            {running ? "Analyzing…" : "Analyze & Rank"}
          </button>
        </div>
      </div>

      <div className="lg:col-span-2 space-y-4">
        <Card className="p-6">
          <SectionTitle sub={running ? "running" : "idle"}>Intelligence Pipeline</SectionTitle>
          <ol className="mt-4 space-y-3">
            {STAGES.map((s, i) => {
              const state = !running ? "idle" : i < stageIdx ? "done" : i === stageIdx ? "active" : "pending";
              return (
                <li key={s.id} className="flex items-start gap-3">
                  <div className="mt-1 size-2 rounded-full shrink-0"
                    style={{
                      background:
                        state === "done" ? "#10b981" : state === "active" ? "#4f46e5" : "rgba(255,255,255,0.15)",
                      boxShadow: state === "active" ? "0 0 0 4px rgba(79,70,229,0.2)" : "none",
                    }}
                  />
                  <div className="flex-1 min-w-0">
                    <div className={`text-xs font-medium ${state === "pending" ? "text-zinc-500" : "text-zinc-100"}`}>{s.label}</div>
                    <div className="text-[11px] text-zinc-500">{s.detail}</div>
                  </div>
                  {state === "active" && <span className="text-[10px] text-accent font-mono">…</span>}
                  {state === "done" && <span className="text-[10px] text-emerald-400 font-mono">ok</span>}
                </li>
              );
            })}
          </ol>
        </Card>

        <Card className="p-6">
          <SectionTitle>What we look for</SectionTitle>
          <div className="space-y-3 text-xs text-zinc-400">
            <div>
              <div className="text-zinc-300 font-medium mb-1">Skills</div>
              <div className="flex flex-wrap gap-1.5">
                {["Python","PyTorch","LLMs","FAISS","Kubernetes","Distributed Systems"].map((s) => <Chip key={s} tone="accent">{s}</Chip>)}
              </div>
            </div>
            <div>
              <div className="text-zinc-300 font-medium mb-1">Behavioral</div>
              <div className="flex flex-wrap gap-1.5">
                {["Ownership","Bias for action","Cross-functional"].map((s) => <Chip key={s}>{s}</Chip>)}
              </div>
            </div>
            <div className="pt-2 border-t border-white/5 text-[11px] text-zinc-500">
              Skills are extracted live from the JD on submit. This panel is illustrative.
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
