import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { lovable } from "@/integrations/lovable/index";
import { useAuth } from "@/hooks/use-auth";

export const Route = createFileRoute("/auth")({
  head: () => ({
    meta: [
      { title: "Sign in — TalentRank AI" },
      { name: "description", content: "Sign in to TalentRank AI with Google to access the recruitment intelligence workspace." },
    ],
  }),
  component: AuthPage,
});

function AuthPage() {
  const navigate = useNavigate();
  const { session, loading, signInMock, signInGooglePopup, isFirebaseConfigured } = useAuth();
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!loading && session) {
      navigate({ to: "/dashboard", replace: true });
    }
  }, [loading, session, navigate]);

  const signIn = async () => {
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
    <div className="min-h-dvh bg-base text-zinc-200 grid lg:grid-cols-2">
      {/* Left brand panel */}
      <div className="hidden lg:flex relative flex-col justify-between p-12 overflow-hidden border-r border-white/5">
        <div
          className="absolute inset-0 opacity-60"
          style={{
            background:
              "radial-gradient(800px 500px at 20% 10%, rgba(79,70,229,0.35), transparent 60%), radial-gradient(700px 400px at 80% 90%, rgba(167,139,250,0.25), transparent 60%)",
          }}
          aria-hidden
        />
        <div className="relative flex items-center gap-3">
          <div className="size-10 rounded-xl bg-accent grid place-items-center ring-1 ring-white/10 shadow-lg shadow-accent/30">
            <span className="font-display font-semibold text-white">TR</span>
          </div>
          <div>
            <div className="font-display text-lg text-zinc-100">TalentRank AI</div>
            <div className="text-[10px] uppercase tracking-widest text-zinc-500">Explainable Intelligence</div>
          </div>
        </div>

        <div className="relative space-y-6">
          <h2 className="font-display text-4xl text-zinc-100 leading-tight max-w-md text-balance">
            Recruitment intelligence that shows its work.
          </h2>
          <p className="text-zinc-400 max-w-md">
            Rank 100k candidates against any job description in seconds. Every score traces back to evidence — skills, signals,
            and behavior.
          </p>
          <ul className="space-y-2 text-sm text-zinc-400">
            <li className="flex items-center gap-2"><span className="size-1.5 rounded-full bg-accent" /> Hybrid retrieval (FAISS + BM25 + RRF)</li>
            <li className="flex items-center gap-2"><span className="size-1.5 rounded-full bg-accent" /> Honeypot contradiction detection</li>
            <li className="flex items-center gap-2"><span className="size-1.5 rounded-full bg-accent" /> Hidden gem discovery</li>
          </ul>
        </div>

        <div className="relative text-xs text-zinc-600">© 2026 TalentRank AI</div>
      </div>

      {/* Right sign-in */}
      <div className="flex items-center justify-center p-8">
        <div className="w-full max-w-sm space-y-8 animate-in-up">
          <div className="space-y-2">
            <h1 className="font-display text-2xl text-zinc-100">Sign in to your workspace</h1>
            <p className="text-sm text-zinc-400">Use your Google account to access TalentRank AI.</p>
          </div>

          <div className="space-y-3">
            <button
              onClick={signIn}
              disabled={busy}
              className="w-full inline-flex items-center justify-center gap-3 bg-white text-zinc-900 px-4 py-3 rounded-lg text-sm font-medium hover:bg-zinc-100 transition-colors disabled:opacity-60"
            >
              <GoogleMark />
              {busy ? "Opening Google…" : "Continue with Google"}
            </button>

            <button
              onClick={signInMock}
              className="w-full inline-flex items-center justify-center gap-3 bg-zinc-900 border border-white/10 text-zinc-300 px-4 py-3 rounded-lg text-sm font-medium hover:bg-zinc-800 transition-colors"
            >
              Developer Bypass (Mock Sign In)
            </button>
          </div>

          <div className="text-xs text-zinc-500 leading-relaxed">
            By continuing you agree to our terms and privacy policy. We use Google to verify your identity — no password needed.
          </div>

          <div className="pt-6 border-t border-white/5 text-xs text-zinc-500">
            New here?{" "}
            <span className="text-zinc-300">A workspace is created automatically the first time you sign in.</span>
          </div>
        </div>
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
