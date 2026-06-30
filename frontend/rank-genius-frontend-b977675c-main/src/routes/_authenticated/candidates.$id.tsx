import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Avatar, Card, Chip, RadarChart, ScoreBar, ScoreRing, SectionTitle } from "@/components/ui-primitives";
import { recommendationLabel, scoreColor } from "@/lib/format";

export const Route = createFileRoute("/_authenticated/candidates/$id")({
  head: ({ params }) => ({
    meta: [
      { title: `Candidate ${params.id} — TalentRank AI` },
      { name: "description", content: "Explainable candidate profile with score breakdown, evidence objects, career trajectory, skills match and AI reasoning." },
    ],
  }),
  component: CandidatePage,
});

function CandidatePage() {
  const { id } = Route.useParams();
  const { data: c, isLoading } = useQuery({ queryKey: ["candidate", id], queryFn: () => api.candidate(id) });

  if (isLoading || !c) {
    return <div className="max-w-[1400px] mx-auto p-8 text-zinc-400">Loading candidate…</div>;
  }

  const rec = c.recommendation ? recommendationLabel(c.recommendation) : { cls: "border-white/10 text-zinc-400 bg-white/5", label: "Unranked" };
  const hasScores = c.scores != null;
  const isRanked = c.overall_score != null;

  return (
    <div className="max-w-[1400px] mx-auto p-8 flex gap-8 items-start">
      {/* Main column */}
      <div className="flex-[2] min-w-0 space-y-6">
        {/* Identity */}
        <section className="flex items-start justify-between gap-6 animate-in-up">
          <div className="flex items-start gap-5 min-w-0">
            <Avatar name={c.name} seed={c.avatar_seed} size={72} />
            <div className="min-w-0">
              <h1 className="font-display text-4xl font-medium text-zinc-100 text-balance leading-tight truncate">{c.name}</h1>
              <p className="text-zinc-400 mt-1.5 text-base">{c.current_role} · {c.current_company} · {c.location}</p>
              <div className="flex flex-wrap gap-2 mt-3">
                <Chip tone="accent">{c.years_experience} yrs experience</Chip>
                {c.availability === "open_to_work" && <Chip tone="good">Open to work</Chip>}
                {c.availability === "passive" && <Chip>Passive</Chip>}
                {(c.risk_score ?? 0) > 40 && <Chip tone="warn">Tenure volatility</Chip>}
                {c.honeypot && <Chip tone="bad">Honeypot flagged</Chip>}
                <Chip>Notice {c.notice_period_days}d</Chip>
              </div>
            </div>
          </div>
          {isRanked ? (
            <ScoreRing value={c.overall_score!} />
          ) : (
            <div className="flex flex-col items-center justify-center size-20 rounded-full border border-white/10 bg-white/5">
              <span className="text-xs font-medium text-zinc-500 uppercase tracking-wide">Unranked</span>
            </div>
          )}
        </section>

        {/* Bento */}
        <div className="grid grid-cols-2 gap-4">
          <Card className="p-6">
            <SectionTitle sub="0–100">Competency Surface</SectionTitle>
            {hasScores ? (
              <RadarChart
                values={[c.scores!.semantic, c.scores!.behavior, c.scores!.career, c.scores!.skill]}
                labels={["Semantic", "Behavior", "Career", "Skill"]}
                size={260}
              />
            ) : (
              <div className="h-[260px] flex items-center justify-center">
                <span className="text-sm text-zinc-500 italic">No competency data available.</span>
              </div>
            )}
          </Card>

          <Card className="p-6 flex flex-col">
            <SectionTitle sub={c.confidence != null ? `conf ${Math.round(c.confidence * 100)}%` : "no confidence score"}>Dimension Breakdown</SectionTitle>
            {hasScores ? (
              <div className="space-y-4 mt-2">
                <ScoreBar label="Semantic Match" value={c.scores!.semantic} />
                <ScoreBar label="Career Velocity" value={c.scores!.career} />
                <ScoreBar label="Behavioral Fit" value={c.scores!.behavior} />
                <ScoreBar label="Skill Depth" value={c.scores!.skill} />
                <ScoreBar label="Availability" value={c.scores!.availability} />
                <ScoreBar label="Risk (inverted)" value={100 - (c.scores!.risk)} />
              </div>
            ) : (
              <div className="flex-1 flex items-center justify-center">
                <span className="text-sm text-zinc-500 italic">Dimension breakdown requires an active ranking session.</span>
              </div>
            )}
          </Card>

          {/* Career timeline */}
          <Card className="col-span-2 p-6">
            <SectionTitle>Professional Trajectory</SectionTitle>
            <ol className="space-y-6 relative before:absolute before:left-2 before:top-2 before:bottom-2 before:w-px before:bg-white/10">
              {c.career.map((e, i) => (
                <li key={i} className="relative pl-8">
                  <div className={`absolute left-1.5 top-1.5 size-1.5 rounded-full ${i === 0 ? "bg-accent ring-4 ring-accent/20" : "bg-zinc-700"}`} />
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="text-sm font-medium text-zinc-100">{e.role}</div>
                      <div className="text-xs text-zinc-500">{e.company} · {e.start}–{e.end ?? "Present"}</div>
                    </div>
                    {i === 0 && <span className="text-[10px] px-2 py-0.5 bg-white/5 text-zinc-300 rounded border border-white/10">Current</span>}
                  </div>
                  {e.highlights?.length ? <p className="mt-2 text-sm text-zinc-400 text-pretty">{e.highlights.join(" · ")}</p> : null}
                </li>
              ))}
            </ol>
          </Card>

          {/* Evidence */}
          <div className="col-span-2 space-y-3">
            <SectionTitle sub={`${c.evidence?.length ?? 0} signals`}>Evidence Streams</SectionTitle>
            {c.evidence && c.evidence.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {c.evidence.map((e) => (
                  <Card key={e.id} className="p-4 hover:ring-accent/30 transition-colors">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <div className={`size-1.5 rounded-full ${e.type === "risk" ? "bg-amber-400" : "bg-accent"}`} />
                        <span className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">{e.type.replace("_", " ")}</span>
                      </div>
                      <span className="text-[10px] font-mono text-zinc-500">w={e.weight.toFixed(2)}</span>
                    </div>
                    <div className="text-sm text-zinc-100 font-medium">{e.title}</div>
                    <div className="text-xs text-zinc-500 mt-1 text-pretty">{e.detail}</div>
                  </Card>
                ))}
              </div>
            ) : (
              <Card className="p-6 flex items-center justify-center">
                <span className="text-sm text-zinc-500 italic">No evidence generated. Candidates must be ranked to extract evidence.</span>
              </Card>
            )}
          </div>
        </div>
      </div>

      {/* Right rail — AI reasoning */}
      <aside className="flex-1 min-w-[320px] max-w-[400px] hidden lg:block">
        <Card className="p-6 sticky top-24">
          <div className="flex items-center gap-3 mb-5">
            <div className="size-6 rounded bg-accent/20 grid place-items-center">
              <div className="size-2.5 border-2 border-accent rounded-sm" />
            </div>
            <h2 className="font-display font-medium text-lg text-zinc-100">AI Reasoning</h2>
          </div>

          <div className="bg-accent/5 p-4 rounded-xl border border-accent/10 mb-5">
            {isRanked ? (
              <p className="text-[13px] text-zinc-100 leading-relaxed text-pretty">
                {c.name} scored <span className="text-accent font-semibold">{c.overall_score}</span> with{" "}
                <span className="text-accent font-semibold">{Math.round(c.confidence! * 100)}%</span> confidence. Hybrid retrieval surfaced this profile via strong semantic alignment on{" "}
                <span className="text-zinc-100">{c.matched_skills.slice(0, 3).join(", ")}</span>.
              </p>
            ) : (
              <p className="text-[13px] text-zinc-400 italic leading-relaxed text-pretty">
                Profile loaded from the global pool. Run a ranking session to generate AI reasoning for this candidate.
              </p>
            )}
          </div>

          <div className="space-y-5">
            <div>
              <h4 className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider mb-3">Skill Alignment</h4>
              {isRanked ? (
                <div className="flex flex-wrap gap-1.5">
                  {c.matched_skills.map((s) => <Chip key={s} tone="good">+ {s}</Chip>)}
                  {c.missing_skills.map((s) => <Chip key={s} tone="warn">− {s}</Chip>)}
                </div>
              ) : (
                <div className="text-xs text-zinc-500">Not assessed against a JD.</div>
              )}
            </div>

            <div>
              <h4 className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider mb-3">Strengths</h4>
              {c.strengths && c.strengths.length > 0 ? (
                <ul className="space-y-2">
                  {c.strengths.map((s, i) => (
                    <li key={i} className="flex gap-3 text-xs leading-relaxed">
                      <div className="size-1.5 rounded-full bg-accent mt-1.5 shrink-0" />
                      <span className="text-zinc-300">{s}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="text-xs text-zinc-500">No strengths extracted.</div>
              )}
            </div>

            {(c.risk_flags?.length ?? 0) > 0 && (
              <div>
                <h4 className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider mb-3">Risk Flags</h4>
                <ul className="space-y-2">
                  {c.risk_flags!.map((s, i) => (
                    <li key={i} className="flex gap-3 text-xs leading-relaxed">
                      <div className="size-1.5 rounded-full bg-amber-400 mt-1.5 shrink-0" />
                      <span className="text-zinc-300">{s}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="pt-5 border-t border-white/5">
              <div className="bg-zinc-900/80 p-4 rounded-xl ring-1 ring-white/5">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-xs font-semibold text-zinc-100">Recommendation</h4>
                  <span className={`px-2 py-0.5 rounded border text-[10px] font-medium ${rec.cls}`}>{rec.label}</span>
                </div>
                <p className="text-xs text-zinc-400 mb-4 text-pretty">{c.recommendation_text ?? "No recommendation available for unranked profiles."}</p>
                <Link
                  to="/compare"
                  className="w-full inline-flex justify-center bg-white/[0.04] hover:bg-white/[0.08] text-zinc-100 py-2 rounded-lg text-xs font-medium transition-colors"
                >
                  Add to comparison
                </Link>
              </div>
            </div>
          </div>
        </Card>
      </aside>
    </div>
  );
}
