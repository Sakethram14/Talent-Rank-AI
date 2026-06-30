export function clsx(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

export function scoreColor(score: number): string {
  if (score >= 85) return "text-emerald-400";
  if (score >= 70) return "text-indigo-300";
  if (score >= 55) return "text-amber-400";
  return "text-rose-400";
}

export function scoreBg(score: number): string {
  if (score >= 85) return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
  if (score >= 70) return "bg-indigo-500/10 text-indigo-300 border-indigo-500/20";
  if (score >= 55) return "bg-amber-500/10 text-amber-400 border-amber-500/20";
  return "bg-rose-500/10 text-rose-400 border-rose-500/20";
}

export function initials(name: string): string {
  return name.split(/\s+/).map((p) => p[0]).slice(0, 2).join("").toUpperCase();
}

export function avatarGradient(seed: string): string {
  let h = 0;
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) >>> 0;
  const a = h % 360;
  const b = (a + 60) % 360;
  return `linear-gradient(135deg, hsl(${a} 70% 35%), hsl(${b} 70% 25%))`;
}

export function recommendationLabel(r: string): { label: string; cls: string } {
  switch (r) {
    case "fast_track": return { label: "Fast-track", cls: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" };
    case "strong_match": return { label: "Strong match", cls: "bg-indigo-500/10 text-indigo-300 border-indigo-500/20" };
    case "consider": return { label: "Consider", cls: "bg-amber-500/10 text-amber-400 border-amber-500/20" };
    case "review": return { label: "Review", cls: "bg-zinc-500/10 text-zinc-300 border-zinc-500/20" };
    case "reject": return { label: "Reject", cls: "bg-rose-500/10 text-rose-400 border-rose-500/20" };
    default: return { label: r, cls: "bg-zinc-500/10 text-zinc-300 border-zinc-500/20" };
  }
}
