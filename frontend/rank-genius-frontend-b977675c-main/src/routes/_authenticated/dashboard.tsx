import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, SectionTitle } from "@/components/ui-primitives";

import { useAuth } from "@/hooks/use-auth";

export const Route = createFileRoute("/_authenticated/dashboard")({
  head: () => ({
    meta: [
      { title: "Dashboard — TalentRank AI" },
      { name: "description", content: "Live recruitment intelligence overview: pool size, AI candidates, honeypots detected, and recent rankings." },
    ],
  }),
  component: DashboardPage,
});

function fmt(n: number): string {
  return n.toLocaleString();
}

function MetricCard({ label, value, delta, hint }: { label: string; value: string; delta?: string; hint?: string }) {
  return (
    <Card className="p-5 animate-in-up">
      <div className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">{label}</div>
      <div className="mt-3 flex items-baseline gap-2">
        <div className="font-display text-3xl font-semibold text-zinc-100 tabular-nums">{value}</div>
        {delta && <div className="text-xs text-emerald-400 font-medium">{delta}</div>}
      </div>
      {hint && <div className="mt-1 text-xs text-zinc-500">{hint}</div>}
    </Card>
  );
}

function DashboardPage() {
  const { user } = useAuth();
  const { data, isLoading } = useQuery({ queryKey: ["dashboard"], queryFn: api.dashboard });

  const firstName = user?.displayName?.split(" ")[0] || "Sarah";

  return (
    <div className="max-w-[1400px] mx-auto p-8 space-y-8">
      <div className="flex items-end justify-between gap-6 flex-wrap">
        <div>
          <h1 className="font-display text-4xl font-medium text-zinc-100 leading-tight">Welcome back, {firstName}</h1>
          <p className="text-zinc-400 mt-2">Your intelligence layer is calibrated and online. 100,000 candidates indexed.</p>
        </div>
        <Link
          to="/job-analysis"
          className="inline-flex items-center gap-2 bg-accent text-white px-5 py-2.5 rounded-lg text-sm font-medium ring-1 ring-accent/50 hover:bg-accent/90 transition-colors shadow-lg shadow-accent/20"
        >
          <span className="size-1.5 rounded-full bg-white animate-pulse" />
          Start a new search
        </Link>
      </div>

      {/* Metric grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <MetricCard label="Total Candidates" value={isLoading ? "—" : fmt(data!.total_candidates)} hint="Indexed in vector store" />
        <MetricCard label="AI Candidates" value={isLoading ? "—" : fmt(data!.ai_candidates)} delta="+12.4%" />
        <MetricCard label="Open to Work" value={isLoading ? "—" : fmt(data!.open_to_work)} delta="+3.1%" />
        <MetricCard label="Avg Experience" value={isLoading ? "—" : `${data!.avg_experience} yrs`} />
        <MetricCard label="Honeypots Caught" value={isLoading ? "—" : fmt(data!.honeypots_detected)} hint="Contradiction-flagged" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2 p-6">
          <SectionTitle sub="updated live">Recent Rankings</SectionTitle>
          <div className="divide-y divide-white/5">
            {(data?.recent_rankings ?? []).map((r) => (
              <Link
                key={r.id}
                to="/rankings"
                className="flex items-center justify-between py-3 group"
              >
                <div className="min-w-0">
                  <div className="text-sm text-zinc-100 font-medium truncate group-hover:text-accent transition-colors">{r.jd_title}</div>
                  <div className="text-xs text-zinc-500">{r.candidates} candidates · {r.ts}</div>
                </div>
                <div className="text-zinc-600 group-hover:text-accent transition-colors">→</div>
              </Link>
            ))}
          </div>
        </Card>

        <Card className="p-6">
          <SectionTitle>System Performance</SectionTitle>
          <div className="space-y-5 mt-4">
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-zinc-400">P95 Latency</span>
                <span className="text-zinc-100 font-mono">{data?.performance.latency_ms ?? "—"} ms</span>
              </div>
              <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                <div className="h-full bg-emerald-500/80 w-[32%]" />
              </div>
            </div>
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-zinc-400">Throughput</span>
                <span className="text-zinc-100 font-mono">{data?.performance.throughput_qps ?? "—"} qps</span>
              </div>
              <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                <div className="h-full bg-accent w-[71%]" />
              </div>
            </div>

            <div className="pt-4 border-t border-white/5 space-y-2 text-xs text-zinc-400">
              <div className="flex justify-between"><span>FAISS Index</span><span className="text-emerald-400">Healthy</span></div>
              <div className="flex justify-between"><span>BM25 Index</span><span className="text-emerald-400">Healthy</span></div>
              <div className="flex justify-between"><span>Embedding Model</span><span className="text-zinc-200 font-mono">all-MiniLM-L6-v2</span></div>
              <div className="flex justify-between"><span>Hybrid Fusion</span><span className="text-zinc-200 font-mono">RRF k=60</span></div>
            </div>
          </div>
        </Card>
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { to: "/job-analysis", title: "Analyze a Job Description", body: "Paste a JD and surface top candidates from 100k in seconds." },
          { to: "/hidden-gems", title: "Discover Hidden Gems", body: "High-signal candidates that traditional ATS miss." },
          { to: "/honeypots", title: "Inspect the Honeypot Wall", body: "Candidates flagged by our contradiction-detection layer." },
        ].map((a) => (
          <Link key={a.to} to={a.to} className="group">
            <Card className="p-5 h-full hover:ring-accent/40 hover:bg-surface/80 transition-all">
              <div className="text-sm font-medium text-zinc-100 group-hover:text-accent transition-colors">{a.title}</div>
              <div className="mt-1 text-xs text-zinc-500 text-pretty">{a.body}</div>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
