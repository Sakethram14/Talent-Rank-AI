import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { api } from "@/lib/api";
import { Card, Chip, SectionTitle } from "@/components/ui-primitives";

export const Route = createFileRoute("/_authenticated/export")({
  head: () => ({ meta: [{ title: "Export Center — TalentRank AI" }, { name: "description", content: "Validate the shortlist and export final candidate selections to CSV." }] }),
  component: ExportPage,
});

function ExportPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleExport = async () => {
    setLoading(true);
    setError(null);
    try {
      const csvContent = await api.exportCsv();
      const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "talentrank_submission.csv";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      setError(err.message || "Failed to export CSV");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-[1100px] mx-auto p-8 space-y-6">
      <div>
        <h1 className="font-display text-3xl font-medium text-zinc-100">Export Center</h1>
        <p className="text-zinc-400 mt-1 text-sm">Validate the shortlist and submit the final hackathon CSV.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="p-5"><SectionTitle>Format</SectionTitle><div className="font-display text-3xl text-zinc-100">CSV</div><div className="text-xs text-zinc-500">UTF-8 · headers included</div></Card>
      </div>

      <Card className="p-6">
        <SectionTitle>Submission Preview</SectionTitle>
        <pre className="mt-3 text-[11px] text-zinc-300 font-mono bg-base/60 p-4 rounded-lg ring-1 ring-white/5 overflow-x-auto">
{`candidate_id,rank
c_1,1
c_2,2
c_3,3
…`}
        </pre>
        {error && <div className="mt-4 text-rose-400 text-sm">{error}</div>}
        <div className="mt-5 flex items-center justify-between">
          <Chip tone="good">Ready to submit</Chip>
          <button 
            onClick={handleExport}
            disabled={loading}
            className="px-4 py-2 bg-accent text-white text-sm font-medium rounded-lg hover:bg-accent/90 shadow-lg shadow-accent/20 disabled:opacity-50"
          >
            {loading ? "Exporting..." : "Download CSV"}
          </button>
        </div>
      </Card>
    </div>
  );
}
