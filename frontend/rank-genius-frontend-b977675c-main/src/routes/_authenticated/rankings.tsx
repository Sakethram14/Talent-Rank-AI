import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Candidate, RankResponse } from "@/lib/types";
import { Avatar, Card, Chip, ScoreBar, SectionTitle } from "@/components/ui-primitives";
import { recommendationLabel, scoreColor } from "@/lib/format";
import { toast } from "sonner";
import { Star } from "lucide-react";

export const Route = createFileRoute("/_authenticated/rankings")({
  head: () => ({
    meta: [
      { title: "Rankings — TalentRank AI" },
      { name: "description", content: "Ranked candidates with score breakdowns, evidence-backed reasoning, and risk flags." },
    ],
  }),
  component: RankingsPage,
});

function RankingsPage() {
  const { data } = useQuery({
    queryKey: ["rankings"],
    queryFn: async () => {
      if (typeof window !== "undefined") {
        const raw = sessionStorage.getItem("tr:lastRank");
        if (raw) {
          try { return JSON.parse(raw) as RankResponse; } catch {}
        }
      }
      return api.session();
    }
  });
  const [q, setQ] = useState("");
  const [view, setView] = useState<"table" | "card">("table");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [isSaved, setIsSaved] = useState(false);
  const [starred, setStarred] = useState<Set<string>>(new Set());

  const filtered = useMemo(() => {
    if (!data) return [];
    const term = q.trim().toLowerCase();
    const validCandidates = data.candidates.filter(c => !c.honeypot);
    if (!term) return validCandidates;
    return validCandidates.filter((c) =>
      [c.name, c.headline, c.current_company, ...c.matched_skills].some((s) => s.toLowerCase().includes(term)),
    );
  }, [data, q]);

  function toggle(id: string) {
    setSelected((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; });
  }

  useEffect(() => {
    if (selected.size > 0) sessionStorage.setItem("tr:compare", JSON.stringify([...selected]));
  }, [selected]);

  useEffect(() => {
    if (!data) return;
    if (typeof window !== "undefined") {
      try {
        const saved = localStorage.getItem("tr:savedSearches");
        const list = saved ? JSON.parse(saved) : [];
        setIsSaved(list.some((s: any) => s.id === data.session_id));

        const starredList = localStorage.getItem("tr:savedCandidates");
        const starredParsed = starredList ? JSON.parse(starredList) : [];
        setStarred(new Set(starredParsed.map((can: any) => can.id)));
      } catch {}
    }
  }, [data]);

  const saveSearch = () => {
    if (!data) return;
    if (typeof window !== "undefined") {
      try {
        const saved = localStorage.getItem("tr:savedSearches");
        const list = saved ? JSON.parse(saved) : [];
        const isAlreadySaved = list.some((s: any) => s.id === data.session_id);
        let updated;
        if (isAlreadySaved) {
          updated = list.filter((s: any) => s.id !== data.session_id);
          setIsSaved(false);
          toast.success("Analysis removed from saved searches");
        } else {
          const newSaved = {
            id: data.session_id,
            timestamp: data.timestamp || new Date().toISOString(),
            job_description: data.job_description,
            candidates_count: data.candidates.length,
            full_data: data,
          };
          updated = [newSaved, ...saved ? JSON.parse(saved) : []];
          setIsSaved(true);
          toast.success("Analysis saved to your workspace!");
        }
        localStorage.setItem("tr:savedSearches", JSON.stringify(updated));
      } catch (e) {
        toast.error("Failed to save analysis");
      }
    }
  };

  const toggleStar = (candidate: Candidate, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (typeof window !== "undefined") {
      try {
        const saved = localStorage.getItem("tr:savedCandidates");
        const list = saved ? JSON.parse(saved) : [];
        const isStarred = list.some((can: any) => can.id === candidate.id);
        let updated;
        if (isStarred) {
          updated = list.filter((can: any) => can.id !== candidate.id);
          setStarred((prev) => { const n = new Set(prev); n.delete(candidate.id); return n; });
          toast.success(`${candidate.name} removed from saved candidates`);
        } else {
          updated = [candidate, ...list];
          setStarred((prev) => { const n = new Set(prev); n.add(candidate.id); return n; });
          toast.success(`${candidate.name} starred!`);
        }
        localStorage.setItem("tr:savedCandidates", JSON.stringify(updated));
      } catch (e) {
        toast.error("Failed to star candidate");
      }
    }
  };

  if (!data) {
    return (
      <div className="max-w-[1400px] mx-auto p-8 flex flex-col items-center justify-center min-h-[50vh] text-center space-y-4">
        <h2 className="font-display text-2xl font-medium text-zinc-100">No Ranking Session Found</h2>
        <p className="text-zinc-400 max-w-md">Upload or paste a Job Description to begin candidate analysis.</p>
        <Link to="/job-analysis" className="px-4 py-2 mt-2 bg-accent text-white text-sm font-medium rounded-lg hover:bg-accent/90">
          Start Analysis
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-[1400px] mx-auto p-8 space-y-6">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-display text-3xl font-medium text-zinc-100">Rankings</h1>
          <p className="text-zinc-400 mt-1 text-sm">
            Top <span className="text-zinc-100 font-medium">{data.candidates.length}</span> of {(data.total_pool ?? 0).toLocaleString()} candidates · skills extracted:{" "}
            {data.extracted?.skills?.slice(0, 4).map((s) => <Chip key={s} tone="accent">{s}</Chip>).reduce<React.ReactNode[]>((acc, el, i) => acc.concat(i ? [" ", el] : [el]), []) ?? "none"}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={saveSearch}
            className={`text-xs font-medium px-3 py-1.5 rounded-md transition-colors ${
              isSaved
                ? "bg-emerald-600/20 text-emerald-400 ring-1 ring-emerald-500/20"
                : "bg-white/[0.03] text-zinc-300 ring-1 ring-white/10 hover:bg-white/[0.06]"
            }`}
          >
            {isSaved ? "Saved Search" : "Save Search"}
          </button>
          
          <div className="bg-white/[0.03] ring-1 ring-white/5 rounded-md p-0.5 flex">
            {(["table", "card"] as const).map((v) => (
              <button
                key={v}
                onClick={() => setView(v)}
                className={`px-3 py-1 text-xs rounded ${view === v ? "bg-white/10 text-zinc-100" : "text-zinc-400"}`}
              >
                {v === "table" ? "Table" : "Cards"}
              </button>
            ))}
          </div>
          {selected.size > 1 && (
            <Link
              to="/compare"
              className="text-xs font-medium bg-accent text-white px-3 py-1.5 rounded-md hover:bg-accent/90"
            >
              Compare {selected.size}
            </Link>
          )}
        </div>
      </div>

      <Card className="p-3 flex items-center gap-3">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search by name, skill, company…"
          className="flex-1 bg-transparent outline-none text-sm text-zinc-100 placeholder:text-zinc-500 px-2 py-1.5"
        />
        <span className="text-[11px] text-zinc-500 font-mono">{filtered.length} results</span>
      </Card>

      {view === "table" ? (
        <Card className="overflow-hidden">
          <table className="w-full text-sm">
            <thead className="text-[11px] uppercase text-zinc-500 tracking-wider">
              <tr className="border-b border-white/5">
                <th className="text-left px-4 py-3 w-8" />
                <th className="text-center px-4 py-3 w-8"><Star className="size-3.5 mx-auto text-zinc-500" /></th>
                <th className="text-left px-4 py-3">Candidate</th>
                <th className="text-left px-4 py-3">Match</th>
                <th className="text-left px-4 py-3">Scores</th>
                <th className="text-left px-4 py-3">Skills</th>
                <th className="text-right px-4 py-3">Verdict</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((c) => (
                <RankingRow 
                  key={c.id} 
                  c={c} 
                  selected={selected.has(c.id)} 
                  onToggle={() => toggle(c.id)} 
                  isStarred={starred.has(c.id)}
                  onToggleStar={(e) => toggleStar(c, e)}
                />
              ))}
            </tbody>
          </table>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map((c) => (
            <CandidateCard 
              key={c.id} 
              c={c} 
              isStarred={starred.has(c.id)}
              onToggleStar={(e) => toggleStar(c, e)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function RankingRow({ 
  c, 
  selected, 
  onToggle,
  isStarred,
  onToggleStar
}: { 
  c: Candidate; 
  selected: boolean; 
  onToggle: () => void;
  isStarred: boolean;
  onToggleStar: (e: React.MouseEvent) => void;
}) {
  const rec = c.recommendation ? recommendationLabel(c.recommendation) : { cls: "border-white/10 text-zinc-400 bg-white/5", label: "Unranked" };
  const hasScores = c.scores != null;
  return (
    <tr className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
      <td className="px-4 py-3">
        <input type="checkbox" checked={selected} onChange={onToggle} className="accent-indigo-500" aria-label={`Select ${c.name}`} />
      </td>
      <td className="px-4 py-3 text-center">
        <button onClick={onToggleStar} className="text-zinc-500 hover:text-amber-400 transition-colors p-1" aria-label={`Star ${c.name}`}>
          <Star className={`size-4 ${isStarred ? "fill-amber-400 text-amber-400" : ""}`} />
        </button>
      </td>
      <td className="px-4 py-3">
        <Link to="/candidates/$id" params={{ id: c.id }} className="flex items-center gap-3 group">
          <Avatar name={c.name} seed={c.avatar_seed} size={36} />
          <div className="min-w-0">
            <div className="text-zinc-100 font-medium truncate group-hover:text-accent transition-colors">{c.name}</div>
            <div className="text-xs text-zinc-500 truncate">{c.headline} · {c.location}</div>
          </div>
        </Link>
      </td>
      <td className="px-4 py-3">
        <div className={`font-display text-xl font-semibold tabular-nums ${c.overall_score != null ? scoreColor(c.overall_score) : "text-zinc-500"}`}>{c.overall_score ?? "—"}</div>
        <div className="text-[10px] text-zinc-500 font-mono">conf {c.confidence != null ? Math.round(c.confidence * 100) + "%" : "—"}</div>
      </td>
      <td className="px-4 py-3 min-w-[180px]">
        {hasScores ? (
          <div className="space-y-1.5">
            <Mini label="sem" v={c.scores!.semantic} />
            <Mini label="skl" v={c.scores!.skill} />
            <Mini label="car" v={c.scores!.career} />
          </div>
        ) : (
          <div className="text-[10px] text-zinc-600 font-mono italic">No breakdown</div>
        )}
      </td>
      <td className="px-4 py-3">
        <div className="flex flex-wrap gap-1 max-w-[260px]">
          {c.matched_skills.slice(0, 4).map((s) => <Chip key={s} tone="accent">{s}</Chip>)}
        </div>
      </td>
      <td className="px-4 py-3 text-right">
        <span className={`inline-flex items-center px-2 py-0.5 rounded border text-[11px] font-medium ${rec.cls}`}>{rec.label}</span>
      </td>
    </tr>
  );
}

function Mini({ label, v }: { label: string; v: number }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-zinc-500 font-mono w-6">{label}</span>
      <div className="flex-1 h-1 bg-white/5 rounded-full overflow-hidden">
        <div className="h-full bg-accent" style={{ width: `${v}%` }} />
      </div>
      <span className="text-[10px] text-zinc-400 font-mono w-6 text-right">{v}</span>
    </div>
  );
}

function CandidateCard({ 
  c,
  isStarred,
  onToggleStar
}: { 
  c: Candidate;
  isStarred: boolean;
  onToggleStar: (e: React.MouseEvent) => void;
}) {
  const rec = c.recommendation ? recommendationLabel(c.recommendation) : { cls: "border-white/10 text-zinc-400 bg-white/5", label: "Unranked" };
  const hasScores = c.scores != null;
  return (
    <Link to="/candidates/$id" params={{ id: c.id }}>
      <Card className="p-5 h-full hover:ring-accent/40 transition-all group">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <Avatar name={c.name} seed={c.avatar_seed} size={44} />
            <div>
              <div className="text-zinc-100 font-medium group-hover:text-accent transition-colors">{c.name}</div>
              <div className="text-xs text-zinc-500">{c.current_role}</div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button onClick={onToggleStar} className="text-zinc-500 hover:text-amber-400 transition-colors p-1" aria-label={`Star ${c.name}`}>
              <Star className={`size-4.5 ${isStarred ? "fill-amber-400 text-amber-400" : ""}`} />
            </button>
            <div className={`font-display text-2xl font-semibold ${c.overall_score != null ? scoreColor(c.overall_score) : "text-zinc-500"}`}>{c.overall_score ?? "—"}</div>
          </div>
        </div>
        <div className="mt-4 space-y-2">
          <ScoreBar label="Semantic" value={hasScores ? c.scores!.semantic : 0} />
          <ScoreBar label="Skill" value={hasScores ? c.scores!.skill : 0} />
        </div>
        <div className="mt-4 flex items-center justify-between">
          <div className="flex flex-wrap gap-1">{c.matched_skills.slice(0, 3).map((s) => <Chip key={s} tone="accent">{s}</Chip>)}</div>
          <span className={`px-2 py-0.5 rounded border text-[10px] font-medium ${rec.cls}`}>{rec.label}</span>
        </div>
      </Card>
    </Link>
  );
}
