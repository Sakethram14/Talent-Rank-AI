import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ConfigWeights } from "@/lib/types";
import { Card, SectionTitle } from "@/components/ui-primitives";
import { toast } from "sonner";

export const Route = createFileRoute("/_authenticated/config")({
  head: () => ({ meta: [{ title: "Config Sandbox — TalentRank AI" }, { name: "description", content: "Tune dimension weights and watch rankings recalibrate in real time." }] }),
  component: ConfigPage,
});

type W = keyof ConfigWeights;
const DEFAULT: ConfigWeights = { semantic_weight: 0.4, structured_weight: 0.3, behavioral_weight: 0.2, recency_weight: 0.1 };

const PRESETS: Record<string, ConfigWeights> = {
  Balanced: DEFAULT,
  Fresher: { semantic_weight: 0.4, structured_weight: 0.5, behavioral_weight: 0.1, recency_weight: 0 },
  Experienced: { semantic_weight: 0.2, structured_weight: 0.2, behavioral_weight: 0.4, recency_weight: 0.2 }
};

function ConfigPage() {
  const { data, isLoading } = useQuery({ queryKey: ["config"], queryFn: api.getConfig });
  const [w, setW] = useState<ConfigWeights>(DEFAULT);
  
  useEffect(() => {
    if (data && data.ranking_weights) {
      setW(data.ranking_weights as any);
    }
  }, [data]);

  const updateConfig = useMutation({
    mutationFn: api.updateConfig,
    onSuccess: () => {
      toast.success("Weights applied successfully!");
    },
    onError: (err) => {
      toast.error("Failed to update weights", { description: String(err) });
    }
  });

  const total = Object.values(w).reduce((a, b) => a + b, 0);
  const totalPercent = Math.round(total * 100);
  return (
    <div className="max-w-[1100px] mx-auto p-8 space-y-6">
      <div>
        <h1 className="font-display text-3xl font-medium text-zinc-100">Configuration Sandbox</h1>
        <p className="text-zinc-400 mt-1 text-sm">Adjust how the ranker weights each dimension. Changes are submitted to <span className="font-mono text-zinc-200">POST /config/weights</span> when applied.</p>
      </div>

      <Card className="p-6">
        <SectionTitle>Preconfigured Options</SectionTitle>
        <div className="flex gap-3 mt-4 mb-6">
          {Object.entries(PRESETS).map(([name, weights]) => (
            <button
              key={name}
              onClick={() => setW(weights)}
              className="px-4 py-2 rounded-md text-sm border border-white/10 text-zinc-200 hover:bg-white/[0.04] transition-colors"
            >
              {name}
            </button>
          ))}
        </div>

        <SectionTitle sub={`total ${totalPercent}%`}>Dimension Weights</SectionTitle>
        <div className="space-y-5 mt-4">
          {isLoading ? (
            <div className="text-zinc-400">Loading config...</div>
          ) : (
            (Object.keys(w) as W[]).map((k) => (
              <div key={k}>
                <div className="flex justify-between text-xs mb-2">
                  <span className="text-zinc-300 capitalize">{k.replace("_weight", "")}</span>
                  <span className="text-zinc-100 font-mono">{Math.round(w[k] * 100)}%</span>
                </div>
                <input
                  type="range" min={0} max={100} value={Math.round(w[k] * 100)}
                  onChange={(e) => setW({ ...w, [k]: Number(e.target.value) / 100 })}
                  className="w-full accent-indigo-500"
                  aria-label={`${k} weight`}
                />
              </div>
            ))
          )}
        </div>
        <div className="mt-6 flex justify-end gap-2">
          <button onClick={() => setW(DEFAULT)} className="px-3 py-1.5 rounded-md text-xs bg-white/[0.04] text-zinc-300 hover:bg-white/[0.08]">Reset</button>
          <button onClick={() => updateConfig.mutate(w)} disabled={updateConfig.isPending} className="px-4 py-1.5 rounded-md text-xs bg-accent text-white font-medium hover:bg-accent/90 disabled:opacity-50">
            {updateConfig.isPending ? "Applying..." : "Apply weights"}
          </button>
        </div>
      </Card>
    </div>
  );
}
