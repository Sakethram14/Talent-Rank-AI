import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Candidate } from "@/lib/types";
import { Avatar, Card, Chip, ScoreBar, SectionTitle } from "@/components/ui-primitives";
import { recommendationLabel, scoreColor } from "@/lib/format";

export const Route = createFileRoute("/_authenticated/compare")({
  head: () => ({
    meta: [
      { title: "Compare Candidates — TalentRank AI" },
      { name: "description", content: "Side-by-side AI-driven comparison of selected candidates: scores, skills, risk and recommendation." },
    ],
  }),
  component: ComparePage,
});

function readIds(): string[] {
  if (typeof window === "undefined") return [];
  try { return JSON.parse(sessionStorage.getItem("tr:compare") ?? "[]") as string[]; } catch { return []; }
}

function ComparePage() {
  const [ids, setIds] = useState<string[]>(readIds);

  const { data, isLoading } = useQuery({
    queryKey: ["compare", ids],
    queryFn: () => api.compare(ids),
    enabled: ids.length > 0,
  });

  if (ids.length === 0) {
    return (
      <div className="max-w-[1400px] mx-auto p-8 text-center mt-12 space-y-4">
        <h2 className="font-display text-2xl font-medium text-zinc-100">No candidates selected</h2>
        <p className="text-zinc-400">Go to the rankings page and select candidates to compare.</p>
        <Link to="/rankings" className="px-4 py-2 mt-2 bg-accent text-white text-sm font-medium rounded-lg hover:bg-accent/90 inline-block">Go to Rankings</Link>
      </div>
    );
  }

  if (isLoading || !data) {
    return <div className="max-w-[1400px] mx-auto p-8 text-zinc-400">Loading comparison…</div>;
  }

  const winner = [...data].sort((a, b) => (b.overall_score ?? 0) - (a.overall_score ?? 0))[0];

  return (
    <div className="max-w-[1400px] mx-auto p-8 space-y-6">
      <div>
        <h1 className="font-display text-3xl font-medium text-zinc-100">Compare</h1>
        <p className="text-zinc-400 mt-1 text-sm">Side-by-side analysis · {winner.overall_score != null ? <><span className="text-emerald-400">{winner.name}</span> ranks highest</> : "Candidates are unranked"}</p>
      </div>

      <div className={`grid gap-4`} style={{ gridTemplateColumns: `repeat(${data.length}, minmax(0, 1fr))` }}>
        {data.map((c) => <CompareColumn key={c.id} c={c} isWinner={c.id === winner.id && c.overall_score != null} />)}
      </div>

      <Card className="p-6">
        <SectionTitle>Dimension Breakdown</SectionTitle>
        <div className="space-y-5">
          {(["semantic","skill","career","behavior","availability"] as const).map((dim) => {
            const max = Math.max(...data.map((d) => d.scores?.[dim] ?? 0));
            return (
              <div key={dim}>
                <div className="text-xs text-zinc-400 capitalize mb-2">{dim}</div>
                <div className="grid gap-2" style={{ gridTemplateColumns: `repeat(${data.length}, minmax(0, 1fr))` }}>
                  {data.map((c) => (
                    <div key={c.id}>
                      <div className="flex justify-between text-[11px] mb-1">
                        <span className="text-zinc-500 truncate">{c.name}</span>
                        <span className={c.scores?.[dim] === max && max > 0 ? "text-emerald-400 font-mono" : "text-zinc-400 font-mono"}>{c.scores?.[dim] ?? "—"}</span>
                      </div>
                      <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                        <div className={`h-full ${c.scores?.[dim] === max && max > 0 ? "bg-emerald-400" : "bg-accent"}`} style={{ width: `${c.scores?.[dim] ?? 0}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
}

function CompareColumn({ c, isWinner }: { c: Candidate; isWinner: boolean }) {
  const rec = c.recommendation ? recommendationLabel(c.recommendation) : { cls: "border-white/10 text-zinc-400 bg-white/5", label: "Unranked" };
  return (
    <Card className={`p-5 ${isWinner ? "ring-emerald-500/30 ring-2" : ""}`}>
      <div className="flex items-center gap-3">
        <Avatar name={c.name} seed={c.avatar_seed} size={44} />
        <div className="min-w-0">
          <Link to="/candidates/$id" params={{ id: c.id }} className="text-zinc-100 font-medium hover:text-accent transition-colors block truncate">{c.name}</Link>
          <div className="text-xs text-zinc-500 truncate">{c.headline}</div>
        </div>
      </div>
      <div className="mt-4 flex items-baseline justify-between">
        <div className={`font-display text-4xl font-semibold ${c.overall_score != null ? scoreColor(c.overall_score) : "text-zinc-500"}`}>{c.overall_score ?? "—"}</div>
        <span className={`px-2 py-0.5 rounded border text-[10px] font-medium ${rec.cls}`}>{rec.label}</span>
      </div>
      <div className="mt-4 space-y-2 text-xs text-zinc-400">
        <div className="flex justify-between"><span>Experience</span><span className="text-zinc-200">{c.years_experience} yrs</span></div>
        <div className="flex justify-between"><span>Risk</span><span className="text-zinc-200">{c.risk_score ?? "—"}</span></div>
        <div className="flex justify-between"><span>Notice</span><span className="text-zinc-200">{c.notice_period_days}d</span></div>
      </div>
      <div className="mt-4 flex flex-wrap gap-1">
        {c.matched_skills.slice(0, 4).map((s) => <Chip key={s} tone="accent">{s}</Chip>)}
      </div>
    </Card>
  );
}
