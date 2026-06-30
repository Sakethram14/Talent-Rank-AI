import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { useAuth } from "@/hooks/use-auth";

export const Route = createFileRoute("/callback")({
  component: CallbackPage,
});

function CallbackPage() {
  const navigate = useNavigate();
  const { session, loading } = useAuth();

  useEffect(() => {
    if (!loading) {
      if (session) {
        navigate({ to: "/dashboard", replace: true });
      } else {
        navigate({ to: "/auth", replace: true });
      }
    }
  }, [loading, session, navigate]);

  return (
    <div className="min-h-dvh bg-base flex items-center justify-center text-zinc-400">
      <div className="text-center space-y-3">
        <div className="animate-spin size-6 border-2 border-accent border-t-transparent rounded-full mx-auto" />
        <div className="text-sm animate-pulse">Completing Google Sign-in…</div>
      </div>
    </div>
  );
}
