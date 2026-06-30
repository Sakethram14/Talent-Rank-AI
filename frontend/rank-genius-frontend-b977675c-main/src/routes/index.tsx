import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { lovable } from "@/integrations/lovable/index";
import { useAuth } from "@/hooks/use-auth";
import { toast } from "sonner";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "TalentRank AI — Explainable Recruitment Intelligence" },
      {
        name: "description",
        content:
          "Rank 100,000 candidates against any job description in seconds. Hybrid AI retrieval with evidence-backed reasoning, honeypot detection, and hidden gem discovery.",
      },
      { property: "og:title", content: "TalentRank AI — Explainable Recruitment Intelligence" },
      { property: "og:description", content: "Explainable AI for technical recruiting. Evidence-backed candidate rankings in seconds." },
    ],
  }),
  component: LandingPage,
});

function LandingPage() {
  const { session, signInGooglePopup, isFirebaseConfigured } = useAuth();
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);

  const onCTA = async () => {
    if (session) {
      navigate({ to: "/dashboard" });
      return;
    }
    setBusy(true);
    try {
      if (isFirebaseConfigured && signInGooglePopup) {
        await signInGooglePopup();
        navigate({ to: "/dashboard", replace: true });
      } else {
        const result = await lovable.auth.signInWithOAuth("google", {
          redirect_uri: window.location.origin + "/auth",
        });
        if (result.error) {
          toast.error("Sign-in failed", { description: String(result.error) });
          setBusy(false);
          return;
        }
        if (result.redirected) return;
        navigate({ to: "/dashboard", replace: true });
      }
    } catch (e) {
      toast.error("Sign-in failed", { description: e instanceof Error ? e.message : String(e) });
      setBusy(false);
    }
  };

  return (
    <div className="min-h-dvh bg-base text-zinc-200">
      <LandingNav session={!!session} />

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            background:
              "radial-gradient(900px 600px at 50% -10%, rgba(79,70,229,0.35), transparent 60%), radial-gradient(700px 500px at 90% 20%, rgba(167,139,250,0.18), transparent 60%)",
          }}
          aria-hidden
        />
        <div className="relative max-w-6xl mx-auto px-6 pt-28 pb-24 text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/[0.04] ring-1 ring-white/10 text-xs text-zinc-300 mb-8 animate-in-up">
            <span className="size-1.5 rounded-full bg-emerald-400 animate-pulse" />
            100,000 candidates indexed · explainable rankings
          </div>
          <h1 className="font-display text-5xl md:text-7xl font-medium text-zinc-100 tracking-tight leading-[1.05] max-w-4xl mx-auto text-balance animate-in-up">
            Recruitment intelligence <span className="text-accent">that shows its work.</span>
          </h1>
          <p className="mt-6 text-lg text-zinc-400 max-w-2xl mx-auto text-pretty animate-in-up">
            Paste a job description. Get evidence-backed candidate rankings in seconds — every score traces to skills, behavior,
            career signals, and risk flags you can audit.
          </p>
          <div className="mt-10 flex items-center justify-center gap-3 flex-wrap animate-in-up">
            <button
              onClick={onCTA}
              disabled={busy}
              className="inline-flex items-center gap-3 bg-white text-zinc-900 px-5 py-3 rounded-lg text-sm font-medium hover:bg-zinc-100 transition-colors disabled:opacity-60"
            >
              <GoogleMark />
              {session ? "Open workspace" : busy ? "Opening Google…" : "Sign in with Google"}
            </button>
            <a
              href="#product"
              className="inline-flex items-center gap-2 px-5 py-3 rounded-lg text-sm font-medium ring-1 ring-white/10 bg-white/[0.03] text-zinc-200 hover:bg-white/[0.06] transition-colors"
            >
              See how it works
            </a>
          </div>

          {/* Floating screenshot mock */}
          <div className="mt-20 relative max-w-5xl mx-auto animate-in-up">
            <div className="absolute -inset-4 rounded-3xl bg-accent/20 blur-3xl" aria-hidden />
            <AppPreview />
          </div>
        </div>
      </section>

      {/* Product overview */}
      <section id="product" className="max-w-6xl mx-auto px-6 py-24 space-y-16">
        <Header eyebrow="Product" title="Built for recruiters who need to defend every shortlist." subtitle="Not another ATS. An explainable decision-support layer on top of your talent pool." />

        <div className="grid md:grid-cols-3 gap-4">
          {[
            { t: "Rank in seconds", d: "Paste any JD. Hybrid retrieval (semantic + lexical + RRF) returns the top matches from 100k candidates." },
            { t: "Evidence everywhere", d: "Click any score to see the exact skills, projects, and signals that produced it." },
            { t: "Catch the noise", d: "Honeypot detection flags fabricated credentials. Hidden-gem scoring surfaces under-indexed talent." },
          ].map((f) => (
            <div key={f.t} className="rounded-2xl bg-surface ring-1 ring-white/5 p-6">
              <div className="size-8 rounded-lg bg-accent/15 ring-1 ring-accent/30 grid place-items-center text-accent mb-4">●</div>
              <div className="text-zinc-100 font-medium">{f.t}</div>
              <div className="text-sm text-zinc-400 mt-2">{f.d}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Architecture */}
      <section className="max-w-6xl mx-auto px-6 py-24 space-y-12">
        <Header eyebrow="Architecture" title="A purpose-built intelligence pipeline." subtitle="Seven stages, every one auditable." />
        <ArchitectureDiagram />
      </section>

      {/* Feature highlights */}
      <section className="max-w-6xl mx-auto px-6 py-24 space-y-12">
        <Header eyebrow="Capabilities" title="Beyond keyword matching." />
        <div className="grid md:grid-cols-2 gap-4">
          {[
            { t: "Hybrid Retrieval", d: "FAISS dense embeddings fused with BM25 sparse search via Reciprocal Rank Fusion (k=60)." },
            { t: "Explainable Scoring", d: "Six-axis breakdown: semantic, behavioral, career, skill, risk, availability." },
            { t: "Honeypot Wall", d: "Contradiction graph isolates resumes with conflicting timelines, fake employers, or impossible tenure." },
            { t: "Hidden Gems", d: "Surfaces candidates with strong signals but low traditional visibility — the people you'd otherwise miss." },
            { t: "Reasoning Panels", d: "Every ranking ships with an expandable AI rationale you can paste into a hiring memo." },
            { t: "Config Sandbox", d: "Tune scoring weights live and re-rank in place. See how the algorithm changes its mind." },
          ].map((f) => (
            <div key={f.t} className="rounded-2xl bg-surface ring-1 ring-white/5 p-6">
              <div className="text-zinc-100 font-medium">{f.t}</div>
              <div className="text-sm text-zinc-400 mt-1">{f.d}</div>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-4xl mx-auto px-6 py-32 text-center">
        <h2 className="font-display text-4xl text-zinc-100 text-balance">Start ranking candidates in under a minute.</h2>
        <p className="text-zinc-400 mt-4 max-w-xl mx-auto">No credit card. No setup. Sign in with Google and your workspace is ready.</p>
        <button
          onClick={onCTA}
          disabled={busy}
          className="mt-8 inline-flex items-center gap-3 bg-white text-zinc-900 px-5 py-3 rounded-lg text-sm font-medium hover:bg-zinc-100 transition-colors disabled:opacity-60"
        >
          <GoogleMark />
          {session ? "Open workspace" : "Continue with Google"}
        </button>
      </section>

      <footer className="border-t border-white/5">
        <div className="max-w-6xl mx-auto px-6 py-8 flex flex-wrap items-center justify-between gap-4 text-xs text-zinc-500">
          <div className="flex items-center gap-2">
            <div className="size-6 rounded-md bg-accent grid place-items-center text-[10px] font-semibold text-white">TR</div>
            TalentRank AI · Explainable XAI
          </div>
          <div>© 2026 TalentRank AI</div>
        </div>
      </footer>
    </div>
  );
}

function LandingNav({ session }: { session: boolean }) {
  return (
    <header className="sticky top-0 z-30 bg-base/70 backdrop-blur-md border-b border-white/5">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2.5">
          <div className="size-8 rounded-lg bg-accent grid place-items-center ring-1 ring-white/10 shadow-lg shadow-accent/20">
            <span className="font-display font-semibold text-white text-sm">TR</span>
          </div>
          <span className="font-display text-zinc-100 tracking-tight">TalentRank AI</span>
        </Link>
        <nav className="hidden md:flex items-center gap-6 text-sm text-zinc-400">
          <a href="#product" className="hover:text-zinc-100 transition-colors">Product</a>
          <a href="#architecture" className="hover:text-zinc-100 transition-colors">Architecture</a>
          <a href="#capabilities" className="hover:text-zinc-100 transition-colors">Capabilities</a>
        </nav>
        {session ? (
          <Link to="/dashboard" className="text-sm bg-accent text-white px-4 py-2 rounded-lg hover:bg-accent/90 transition-colors">
            Open workspace →
          </Link>
        ) : (
          <Link to="/auth" className="text-sm bg-white text-zinc-900 px-4 py-2 rounded-lg hover:bg-zinc-100 transition-colors">
            Sign in
          </Link>
        )}
      </div>
    </header>
  );
}

function Header({ eyebrow, title, subtitle }: { eyebrow: string; title: string; subtitle?: string }) {
  return (
    <div className="text-center max-w-2xl mx-auto">
      <div className="text-[11px] tracking-widest uppercase text-accent font-semibold">{eyebrow}</div>
      <h2 className="font-display text-3xl md:text-4xl text-zinc-100 mt-3 text-balance">{title}</h2>
      {subtitle && <p className="text-zinc-400 mt-3 text-pretty">{subtitle}</p>}
    </div>
  );
}

function AppPreview() {
  // Stylized app screenshot built in pure SVG/HTML for fidelity & no asset dependency.
  return (
    <div className="relative rounded-2xl overflow-hidden ring-1 ring-white/10 bg-surface shadow-2xl shadow-black/50">
      <div className="h-9 bg-base/80 border-b border-white/5 flex items-center px-3 gap-1.5">
        <div className="size-2.5 rounded-full bg-rose-500/70" />
        <div className="size-2.5 rounded-full bg-amber-400/70" />
        <div className="size-2.5 rounded-full bg-emerald-500/70" />
        <div className="ml-4 text-[10px] text-zinc-500 font-mono">talentrank.ai/rankings</div>
      </div>
      <div className="grid grid-cols-[180px_1fr] min-h-[420px]">
        <div className="border-r border-white/5 p-3 space-y-1.5 bg-base/40">
          {["Dashboard", "Job Analysis", "Rankings", "Compare", "Hidden Gems", "Honeypots", "Analytics"].map((l, i) => (
            <div
              key={l}
              className={`text-xs px-2.5 py-1.5 rounded-md ${i === 2 ? "bg-white/5 text-zinc-100" : "text-zinc-500"}`}
            >
              {l}
            </div>
          ))}
        </div>
        <div className="p-6 space-y-4">
          <div className="text-sm text-zinc-400">Senior ML Engineer · 247 candidates</div>
          <div className="grid grid-cols-4 gap-3">
            {[94, 91, 88, 86].map((s) => (
              <div key={s} className="rounded-lg bg-base/60 ring-1 ring-white/5 p-3">
                <div className="text-[10px] text-zinc-500 uppercase tracking-wider">Score</div>
                <div className="font-display text-2xl text-zinc-100 tabular-nums">{s}</div>
                <div className="h-1 rounded-full bg-white/5 mt-2 overflow-hidden">
                  <div className="h-full bg-accent" style={{ width: `${s}%` }} />
                </div>
              </div>
            ))}
          </div>
          <div className="space-y-2">
            {["Priya N. · Staff ML · Stripe", "Arjun K. · Senior MLE · DeepMind", "Maya S. · ML Lead · Anthropic", "Liam O. · MLE II · Hugging Face"].map((row, i) => (
              <div key={row} className="flex items-center justify-between bg-base/40 rounded-lg p-3 ring-1 ring-white/5">
                <div className="flex items-center gap-3">
                  <div className="size-7 rounded-md bg-gradient-to-br from-indigo-500 to-fuchsia-500" />
                  <div className="text-xs text-zinc-200">{row}</div>
                </div>
                <div className="text-xs font-mono text-accent">{94 - i * 3}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function ArchitectureDiagram() {
  const stages = [
    "JD Intake",
    "Skill Extraction",
    "Hybrid Retrieval",
    "Re-ranking",
    "Behavioral Scoring",
    "Honeypot Filter",
    "Evidence Synthesis",
  ];
  return (
    <div id="architecture" className="rounded-2xl bg-surface ring-1 ring-white/5 p-6 overflow-x-auto">
      <div className="flex items-center gap-3 min-w-max">
        {stages.map((s, i) => (
          <div key={s} className="flex items-center gap-3">
            <div className="px-4 py-3 rounded-xl bg-base/60 ring-1 ring-white/10 text-sm text-zinc-200 whitespace-nowrap">
              <div className="text-[10px] text-zinc-500 uppercase tracking-wider">Stage {i + 1}</div>
              {s}
            </div>
            {i < stages.length - 1 && <div className="text-accent">→</div>}
          </div>
        ))}
      </div>
      <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
        {[
          ["FAISS", "Dense vectors"],
          ["BM25", "Sparse retrieval"],
          ["RRF (k=60)", "Rank fusion"],
          ["all-MiniLM-L6-v2", "Embeddings"],
        ].map(([k, v]) => (
          <div key={k} className="rounded-lg bg-base/40 ring-1 ring-white/5 p-3">
            <div className="text-zinc-300 font-mono">{k}</div>
            <div className="text-zinc-500">{v}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function GoogleMark() {
  return (
    <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden>
      <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.4 29.3 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3 0 5.8 1.1 7.9 3l5.7-5.7C33.9 6.1 29.2 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5z" />
      <path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.7 16.1 19 13 24 13c3 0 5.8 1.1 7.9 3l5.7-5.7C33.9 6.1 29.2 4 24 4 16.3 4 9.6 8.4 6.3 14.7z" />
      <path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.3l-6.2-5.2C29.3 35 26.8 36 24 36c-5.3 0-9.7-3.6-11.3-8.4l-6.5 5C9.5 39.5 16.2 44 24 44z" />
      <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.3-2.3 4.2-4.1 5.5l6.2 5.2C41.4 35.5 44 30.2 44 24c0-1.3-.1-2.4-.4-3.5z" />
    </svg>
  );
}
