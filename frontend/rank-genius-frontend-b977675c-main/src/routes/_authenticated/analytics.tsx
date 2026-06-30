import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, SectionTitle } from "@/components/ui-primitives";

export const Route = createFileRoute("/_authenticated/analytics")({
  head: () => ({ meta: [{ title: "Analytics — TalentRank AI" }, { name: "description", content: "Distributions across experience, skills, companies and behavior." }] }),
  component: AnalyticsPage,
});

function Bar({ label, value, max }: { label: string; value: number; max: number }) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs"><span className="text-zinc-400">{label}</span><span className="text-zinc-200 font-mono">{value.toLocaleString()}</span></div>
      <div className="h-2 bg-white/5 rounded-full overflow-hidden"><div className="h-full bg-accent" style={{ width: `${(value / max) * 100}%` }} /></div>
    </div>
  );
}

function AnalyticsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["analytics"],
    queryFn: api.distributions
  });

  if (isLoading || !data) {
    return <div className="max-w-[1400px] mx-auto p-8 text-zinc-400">Loading distributions...</div>;
  }

  const expMax = Math.max(...data.experience.map(b => b.count), 1);
  const sklMax = Math.max(...data.skills.map(b => b.count), 1);
  return (
    <div className="max-w-[1400px] mx-auto p-8 space-y-6">
      <div>
        <h1 className="font-display text-3xl font-medium text-zinc-100">Analytics</h1>
        <p className="text-zinc-400 mt-1 text-sm">Distributions across the indexed candidate pool.</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="p-6">
          <SectionTitle>Experience distribution</SectionTitle>
          <div className="space-y-3 mt-4">{data.experience.map(b => <Bar key={b.label} label={b.label} value={b.count} max={expMax} />)}</div>
        </Card>
        <Card className="p-6">
          <SectionTitle>Top technologies</SectionTitle>
          <div className="space-y-3 mt-4">{data.skills.map(b => <Bar key={b.label} label={b.label} value={b.count} max={sklMax} />)}</div>
        </Card>
      </div>
    </div>
  );
}
