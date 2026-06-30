import { Link, useNavigate, useRouterState } from "@tanstack/react-router";
import { type ReactNode, useState } from "react";
import { clsx } from "@/lib/format";
import { useAuth } from "@/hooks/use-auth";

type NavItem = { to: string; label: string; group: string };

const NAV: NavItem[] = [
  { group: "Intelligence", to: "/dashboard", label: "Dashboard" },
  { group: "Intelligence", to: "/job-analysis", label: "Job Analysis" },
  { group: "Intelligence", to: "/rankings", label: "Rankings" },
  { group: "Intelligence", to: "/compare", label: "Compare" },
  { group: "Talent Pools", to: "/hidden-gems", label: "Hidden Gems" },
  { group: "Talent Pools", to: "/honeypots", label: "Honeypots" },
  { group: "Analytics", to: "/analytics", label: "Analytics" },
  { group: "System", to: "/config", label: "Config Sandbox" },
  { group: "System", to: "/export", label: "Export Center" },
];

function NavGroup({ title, items, currentPath }: { title: string; items: NavItem[]; currentPath: string }) {
  return (
    <div className="space-y-1">
      <div className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider mb-3 px-3">{title}</div>
      {items.map((it) => {
        const active = currentPath === it.to || currentPath.startsWith(it.to + "/");
        return (
          <Link
            key={it.to}
            to={it.to}
            className={clsx(
              "flex items-center gap-3 px-3 py-2 text-sm rounded-md transition-colors",
              active ? "text-zinc-100 bg-white/5 ring-1 ring-white/5" : "text-zinc-400 hover:text-zinc-100 hover:bg-white/[0.03]",
            )}
          >
            <span className={clsx("size-1.5 rounded-full transition-colors", active ? "bg-accent" : "bg-zinc-700")} />
            {it.label}
          </Link>
        );
      })}
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const [demo, setDemo] = useState(false);
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

  const groups = Array.from(new Set(NAV.map((n) => n.group)));
  const initial = (user?.displayName ?? "U").slice(0, 1).toUpperCase();

  return (
    <div className="flex h-dvh bg-base text-zinc-300 font-sans selection:bg-accent/30 selection:text-zinc-100">
      <nav className="w-64 border-r border-white/5 flex flex-col shrink-0 bg-base">
        <Link to="/dashboard" className="p-6 flex items-center gap-3">
          <div className="size-8 rounded-lg bg-accent flex items-center justify-center ring-1 ring-white/10 shadow-lg shadow-accent/20">
            <span className="font-display font-semibold text-white text-sm">TR</span>
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-display font-medium text-zinc-100 tracking-tight leading-tight">TalentRank AI</div>
            <div className="text-[10px] text-zinc-500 uppercase tracking-widest">Explainable XAI</div>
          </div>
        </Link>

        <div className="flex-1 overflow-y-auto px-4 pb-4 space-y-6">
          {groups.map((g) => (
            <NavGroup key={g} title={g} items={NAV.filter((n) => n.group === g)} currentPath={pathname} />
          ))}
        </div>

        <div className="p-4 border-t border-white/5">
          <Link
            to="/workspace"
            className="flex items-center gap-3 px-3 py-2 rounded-md bg-white/[0.03] hover:bg-white/[0.06] transition-colors w-full"
          >
            {user?.photoURL ? (
              <img src={user.photoURL} alt="" className="size-8 rounded-full" />
            ) : (
              <div className="size-8 rounded-full bg-gradient-to-br from-indigo-500 to-fuchsia-500 grid place-items-center text-xs font-semibold text-white">
                {initial}
              </div>
            )}
            <div className="flex-1 min-w-0 text-left">
              <div className="text-xs font-medium text-zinc-100 truncate">{user?.displayName ?? "—"}</div>
              <div className="text-[10px] text-zinc-500 truncate">{user?.email ?? "Open workspace"}</div>
            </div>
          </Link>
        </div>
      </nav>

      <main className="flex-1 flex flex-col min-w-0 bg-base/50">
        <header className="h-16 border-b border-white/5 flex items-center justify-between px-8 sticky top-0 bg-base/80 backdrop-blur-md z-20">
          <Breadcrumb pathname={pathname} />
          <div className="flex items-center gap-3">
            <button
              onClick={() => setDemo((v) => !v)}
              className={clsx(
                "flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium ring-1 transition-colors",
                demo ? "bg-accent/15 text-accent ring-accent/30" : "bg-white/[0.03] text-zinc-400 ring-white/5 hover:text-zinc-100",
              )}
            >
              <span className={clsx("size-1.5 rounded-full", demo ? "bg-accent animate-pulse" : "bg-zinc-600")} />
              Judge Demo Mode
            </button>
            <div className="flex items-center gap-2 bg-amber-500/10 px-3 py-1.5 rounded-full ring-1 ring-amber-500/30">
              <div className="size-2 rounded-full bg-amber-400" />
              <span className="text-xs font-medium text-amber-300">Demo data</span>
            </div>
            <button
              onClick={async () => { await signOut(); navigate({ to: "/", replace: true }); }}
              className="text-xs text-zinc-400 hover:text-zinc-100 px-2 py-1.5"
            >
              Sign out
            </button>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto">{children}</div>
      </main>
    </div>
  );
}

function Breadcrumb({ pathname }: { pathname: string }) {
  const map: Record<string, string> = {
    "/dashboard": "Dashboard",
    "/job-analysis": "Job Analysis",
    "/rankings": "Rankings",
    "/compare": "Compare",
    "/hidden-gems": "Hidden Gems",
    "/honeypots": "Honeypots",
    "/analytics": "Analytics",
    "/config": "Configuration Sandbox",
    "/export": "Export Center",
    "/workspace": "Workspace",
  };
  const top = Object.keys(map).find((k) => pathname === k || pathname.startsWith(k + "/")) ?? "/dashboard";
  const isCandidate = pathname.startsWith("/candidates/");
  return (
    <div className="flex items-center gap-3 text-sm">
      <span className="text-zinc-500">{isCandidate ? "Rankings" : map[top]}</span>
      {isCandidate && (
        <>
          <span className="text-zinc-700">/</span>
          <span className="text-zinc-100 font-medium">Candidate Detail</span>
        </>
      )}
    </div>
  );
}
