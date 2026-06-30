import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Avatar, Card, Chip, SectionTitle } from "@/components/ui-primitives";

export const Route = createFileRoute("/_authenticated/honeypots")({
  head: () => ({ meta: [{ title: "Honeypot Wall — TalentRank AI" }, { name: "description", content: "Candidates rejected by the contradiction-detection layer." }] }),
  component: HoneypotsPage,
});

function HoneypotsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["honeypots"],
    queryFn: async () => {
      // The honeypots API endpoint is dedicated to this
      const res = await api.honeypots();
      
      // We also need candidate details, so let's get the session
      const session = await api.session();
      return session.honeypots || session.candidates.filter(c => c.honeypot);
    },
  });

  if (isLoading) return <div className="max-w-[1400px] mx-auto p-8 text-zinc-400">Loading honeypots...</div>;
  if (error) return (
    <div className="max-w-[1400px] mx-auto p-8 text-center mt-12 space-y-4">
      <h2 className="font-display text-2xl font-medium text-zinc-100">No active session</h2>
      <p className="text-zinc-400">Run a Job Analysis first to see honeypot rejections.</p>
      <Link to="/job-analysis" className="px-4 py-2 mt-2 bg-accent text-white text-sm font-medium rounded-lg hover:bg-accent/90 inline-block">Start Analysis</Link>
    </div>
  );

  return (
    <div className="max-w-[1400px] mx-auto p-8 space-y-6">
      <div>
        <h1 className="font-display text-3xl font-medium text-zinc-100">Honeypot Wall</h1>
        <p className="text-zinc-400 mt-1 text-sm">Profiles rejected by the AI's contradiction layer. Every rejection is explained.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {(data ?? []).map((c) => (
          <Card key={c.id} className="p-5 ring-rose-500/15">
            <div className="flex items-start gap-3">
              <Avatar name={c.name} seed={c.avatar_seed} size={44} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <div className="text-zinc-100 font-medium truncate">{c.name}</div>
                  <Chip tone="bad">Rejected</Chip>
                </div>
                <div className="text-xs text-zinc-500 truncate">{c.headline}</div>
              </div>
            </div>
            <div className="mt-4 space-y-2">
              {(c.honeypot_reasons ?? []).map((r, i) => (
                <div key={i} className="flex gap-3 text-xs text-zinc-300">
                  <div className="size-1.5 rounded-full bg-rose-400 mt-1.5 shrink-0" />
                  <span>{r}</span>
                </div>
              ))}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
