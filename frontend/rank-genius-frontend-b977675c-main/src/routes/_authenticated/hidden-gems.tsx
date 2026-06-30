import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Avatar, Card, Chip, SectionTitle } from "@/components/ui-primitives";

export const Route = createFileRoute("/_authenticated/hidden-gems")({
  head: () => ({ meta: [{ title: "Hidden Gems — TalentRank AI" }, { name: "description", content: "High-signal candidates that traditional ATS systems miss." }] }),
  component: HiddenGemsPage,
});

function HiddenGemsPage() {
  const { data, isLoading, error } = useQuery({ 
    queryKey: ["hidden-gems"], 
    queryFn: async () => {
      const session = await api.session();
      return session.hidden_gems || session.candidates.filter(c => c.hidden_gem_score != null);
    }
  });

  if (isLoading) return <div className="max-w-[1400px] mx-auto p-8 text-zinc-400">Loading hidden gems...</div>;
  if (error) return (
    <div className="max-w-[1400px] mx-auto p-8 text-center mt-12 space-y-4">
      <h2 className="font-display text-2xl font-medium text-zinc-100">No active session</h2>
      <p className="text-zinc-400">Run a Job Analysis first to find hidden gems.</p>
      <Link to="/job-analysis" className="px-4 py-2 mt-2 bg-accent text-white text-sm font-medium rounded-lg hover:bg-accent/90 inline-block">Start Analysis</Link>
    </div>
  );
  return (
    <div className="max-w-[1400px] mx-auto p-8 space-y-6">
      <div>
        <h1 className="font-display text-3xl font-medium text-zinc-100">Hidden Gems</h1>
        <p className="text-zinc-400 mt-1 text-sm">High technical quality, low recruiter visibility. The intelligence layer flagged these candidates as under-discovered.</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {(data ?? []).map((c) => (
          <Link key={c.id} to="/candidates/$id" params={{ id: c.id }}>
            <Card className="p-5 hover:ring-accent/40 transition-all group h-full">
              <div className="flex items-center gap-3">
                <Avatar name={c.name} seed={c.avatar_seed} size={40} />
                <div className="min-w-0">
                  <div className="text-zinc-100 font-medium group-hover:text-accent transition-colors truncate">{c.name}</div>
                  <div className="text-xs text-zinc-500 truncate">{c.headline}</div>
                </div>
              </div>
              <p className="mt-4 text-xs text-zinc-400 text-pretty">
                Strong open-source signals on <span className="text-zinc-200">{c.matched_skills[0]}</span> · low recruiter outreach over the last 90 days.
              </p>
              <div className="mt-3 flex items-center justify-between">
                <Chip tone="accent">Gem score {c.hidden_gem_score ?? (c.overall_score != null ? Math.round(70 + c.overall_score / 4) : 70)}</Chip>
                <span className="text-xs text-zinc-500">Open to work</span>
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
