import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useAuth } from "@/hooks/use-auth";
import { Card, SectionTitle, Chip } from "@/components/ui-primitives";
import { useEffect, useState } from "react";

export const Route = createFileRoute("/_authenticated/workspace")({
  head: () => ({ meta: [{ title: "Workspace — TalentRank AI" }] }),
  component: WorkspacePage,
});

function Section({ title, hint, children }: { title: string; hint?: string; children: React.ReactNode }) {
  return (
    <Card className="p-6">
      <SectionTitle sub={hint}>{title}</SectionTitle>
      {children}
    </Card>
  );
}

function Empty({ label }: { label: string }) {
  return (
    <div className="text-center py-10 text-sm text-zinc-500 border border-dashed border-white/10 rounded-xl">
      {label}
    </div>
  );
}

function WorkspacePage() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const [savedSearches, setSavedSearches] = useState<any[]>([]);
  const [starredCandidates, setStarredCandidates] = useState<any[]>([]);
  const [recentSearches, setRecentSearches] = useState<any[]>([]);

  useEffect(() => {
    if (typeof window !== "undefined") {
      try {
        const saved = localStorage.getItem("tr:savedSearches");
        if (saved) setSavedSearches(JSON.parse(saved));

        const starred = localStorage.getItem("tr:savedCandidates");
        if (starred) setStarredCandidates(JSON.parse(starred));

        const recent = localStorage.getItem("tr:recentSearches");
        if (recent) setRecentSearches(JSON.parse(recent));
      } catch {}
    }
  }, []);

  const loadSearch = (search: any) => {
    if (typeof window !== "undefined" && search.full_data) {
      sessionStorage.setItem("tr:lastRank", JSON.stringify(search.full_data));
      navigate({ to: "/rankings" });
    }
  };

  return (
    <div className="max-w-[1100px] mx-auto p-8 space-y-6">
      <div className="flex items-end justify-between gap-6 flex-wrap">
        <div>
          <h1 className="font-display text-3xl font-medium text-zinc-100">Your workspace</h1>
          <p className="text-zinc-400 mt-1 text-sm">Profile, saved candidates, search history, and account settings.</p>
        </div>
        <button
          onClick={signOut}
          className="text-sm px-4 py-2 rounded-lg ring-1 ring-white/10 bg-white/[0.03] text-zinc-200 hover:bg-white/[0.06] transition-colors"
        >
          Sign out
        </button>
      </div>

      {/* Profile */}
      <Card className="p-6">
        <div className="flex items-center gap-5">
          {user?.photoURL ? (
            <img src={user.photoURL} alt="" className="size-16 rounded-full ring-1 ring-white/10" />
          ) : (
            <div className="size-16 rounded-full bg-gradient-to-br from-indigo-500 to-fuchsia-500 grid place-items-center text-white text-xl font-semibold">
              {user?.displayName?.[0] ?? "?"}
            </div>
          )}
          <div className="flex-1 min-w-0">
            <div className="text-xl font-medium text-zinc-100 truncate">{user?.displayName}</div>
            <div className="text-sm text-zinc-500 truncate">{user?.email}</div>
            <div className="mt-2 flex gap-2">
              <Chip tone="accent">Recruiter</Chip>
              <Chip>Google · verified</Chip>
            </div>
          </div>
        </div>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Section title="Saved Searches" hint={`${savedSearches.length} saved`}>
          {savedSearches.length === 0 ? (
            <Empty label="Save a job analysis to revisit it later." />
          ) : (
            <div className="space-y-2 mt-3 max-h-[220px] overflow-y-auto pr-1">
              {savedSearches.map((s) => (
                <div
                  key={s.id}
                  onClick={() => loadSearch(s)}
                  className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] border border-white/5 hover:bg-white/[0.05] cursor-pointer transition-colors text-left group"
                >
                  <div className="min-w-0 flex-1 pr-3">
                    <div className="text-sm font-medium text-zinc-200 group-hover:text-accent transition-colors truncate">
                      {s.job_description.split("\n")[0] || "Unnamed Search"}
                    </div>
                    <div className="text-[11px] text-zinc-500 mt-0.5">{new Date(s.timestamp).toLocaleString()}</div>
                  </div>
                  <Chip tone="accent">{s.candidates_count} candidates</Chip>
                </div>
              ))}
            </div>
          )}
        </Section>

        <Section title="Saved Candidates" hint={`${starredCandidates.length} saved`}>
          {starredCandidates.length === 0 ? (
            <Empty label="Star candidates from any ranking to bookmark them." />
          ) : (
            <div className="space-y-2 mt-3 max-h-[220px] overflow-y-auto pr-1">
              {starredCandidates.map((c) => (
                <Link
                  key={c.id}
                  to="/candidates/$id"
                  params={{ id: c.id }}
                  className="flex items-center gap-3 p-3 rounded-lg bg-white/[0.02] border border-white/5 hover:bg-white/[0.05] transition-colors text-left group"
                >
                  <div className="size-8 rounded-full bg-accent/20 grid place-items-center text-accent text-xs font-semibold">
                    {c.name[0]}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-medium text-zinc-200 group-hover:text-accent transition-colors truncate">{c.name}</div>
                    <div className="text-[11px] text-zinc-500 truncate">{c.current_role} · {c.current_company}</div>
                  </div>
                  <div className="text-xs font-semibold text-accent">{c.overall_score}%</div>
                </Link>
              ))}
            </div>
          )}
        </Section>

        <Section title="Recent Searches" hint="last 30 days">
          {recentSearches.length === 0 ? (
            <Empty label="No recent searches yet. Run a job analysis to start." />
          ) : (
            <div className="space-y-2 mt-3 max-h-[220px] overflow-y-auto pr-1">
              {recentSearches.map((s) => (
                <div
                  key={s.id}
                  onClick={() => loadSearch(s)}
                  className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] border border-white/5 hover:bg-white/[0.05] cursor-pointer transition-colors text-left group"
                >
                  <div className="min-w-0 flex-1 pr-3">
                    <div className="text-sm font-medium text-zinc-200 group-hover:text-accent transition-colors truncate">
                      {s.job_description.split("\n")[0] || "Unnamed Search"}
                    </div>
                    <div className="text-[11px] text-zinc-500 mt-0.5">{new Date(s.timestamp).toLocaleString()}</div>
                  </div>
                  <div className="text-[11px] text-zinc-400">{s.candidates_count} candidates</div>
                </div>
              ))}
            </div>
          )}
        </Section>

        <Section title="Export History"><Empty label="Exports you create will appear here." /></Section>
        <Section title="Notifications"><Empty label="You're all caught up." /></Section>
        <Section title="Account Settings">
          <div className="text-sm text-zinc-400 space-y-3">
            <div className="flex justify-between"><span>Display name</span><span className="text-zinc-200">{user?.displayName}</span></div>
            <div className="flex justify-between"><span>Email</span><span className="text-zinc-200">{user?.email}</span></div>
            <div className="flex justify-between"><span>Sign-in method</span><span className="text-zinc-200">Google</span></div>
          </div>
        </Section>
      </div>
    </div>
  );
}
