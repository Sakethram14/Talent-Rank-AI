import { clsx, initials, avatarGradient } from "@/lib/format";

export function Avatar({ name, seed, size = 40 }: { name: string; seed: string; size?: number }) {
  return (
    <div
      className="rounded-xl grid place-items-center text-white font-semibold ring-1 ring-white/10 shrink-0"
      style={{ width: size, height: size, background: avatarGradient(seed), fontSize: size * 0.35 }}
      aria-hidden
    >
      {initials(name)}
    </div>
  );
}

export function ScoreBar({ label, value, max = 100 }: { label: string; value: number; max?: number }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-zinc-400">{label}</span>
        <span className="text-zinc-100 font-mono">{Math.round(value)}</span>
      </div>
      <div className="h-1.5 w-full bg-zinc-800/80 rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-accent to-indigo-400 rounded-full transition-[width] duration-700"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export function Card({ className, children }: { className?: string; children: React.ReactNode }) {
  return (
    <div className={clsx("bg-surface ring-1 ring-white/5 rounded-2xl border border-white/5", className)}>
      {children}
    </div>
  );
}

export function SectionTitle({ children, sub }: { children: React.ReactNode; sub?: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between mb-3">
      <h3 className="text-sm font-medium text-zinc-300">{children}</h3>
      {sub && <span className="text-[11px] text-zinc-500 font-mono">{sub}</span>}
    </div>
  );
}

export function Chip({ children, tone = "default" }: { children: React.ReactNode; tone?: "default" | "good" | "bad" | "warn" | "accent" }) {
  const cls = {
    default: "bg-white/[0.04] text-zinc-300 ring-white/10",
    good: "bg-emerald-500/10 text-emerald-400 ring-emerald-500/20",
    bad: "bg-rose-500/10 text-rose-400 ring-rose-500/20",
    warn: "bg-amber-500/10 text-amber-400 ring-amber-500/20",
    accent: "bg-accent/10 text-accent ring-accent/20",
  }[tone];
  return <span className={clsx("inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-medium ring-1", cls)}>{children}</span>;
}

/** Pure SVG radar chart for the 4 main score dimensions. */
export function RadarChart({
  values,
  labels,
  size = 260,
}: {
  values: number[]; // 0-100
  labels: string[];
  size?: number;
}) {
  const cx = size / 2, cy = size / 2;
  const r = size / 2 - 28;
  const n = values.length;
  const angle = (i: number) => (Math.PI * 2 * i) / n - Math.PI / 2;
  const point = (v: number, i: number) => {
    const rad = (v / 100) * r;
    return [cx + rad * Math.cos(angle(i)), cy + rad * Math.sin(angle(i))];
  };
  const poly = values.map((v, i) => point(v, i).join(",")).join(" ");
  const rings = [0.25, 0.5, 0.75, 1];

  return (
    <svg viewBox={`0 0 ${size} ${size}`} className="w-full h-auto">
      {rings.map((f, i) => (
        <polygon
          key={i}
          points={Array.from({ length: n }, (_, k) => point(100 * f, k).join(",")).join(" ")}
          fill="none"
          stroke="rgba(255,255,255,0.06)"
          strokeWidth={1}
        />
      ))}
      {Array.from({ length: n }, (_, i) => {
        const [x, y] = point(100, i);
        return <line key={i} x1={cx} y1={cy} x2={x} y2={y} stroke="rgba(255,255,255,0.05)" />;
      })}
      <polygon points={poly} fill="rgba(79,70,229,0.25)" stroke="#4f46e5" strokeWidth={1.5} />
      {values.map((v, i) => {
        const [x, y] = point(v, i);
        return <circle key={i} cx={x} cy={y} r={3} fill="#4f46e5" />;
      })}
      {labels.map((l, i) => {
        const [x, y] = point(118, i);
        return (
          <text key={l} x={x} y={y} fontSize={10} fill="#9ca3b8" textAnchor="middle" dominantBaseline="middle" style={{ fontFamily: "DM Sans" }}>
            {l}
          </text>
        );
      })}
    </svg>
  );
}

/** Concentric ring used for the headline overall score. */
export function ScoreRing({ value, label = "Rank", size = 128 }: { value: number; label?: string; size?: number }) {
  const stroke = 8;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const off = c * (1 - Math.max(0, Math.min(100, value)) / 100);
  return (
    <div className="relative grid place-items-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} stroke="rgba(255,255,255,0.06)" strokeWidth={stroke} fill="none" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          stroke="url(#g)"
          strokeWidth={stroke}
          fill="none"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={off}
          style={{ transition: "stroke-dashoffset 800ms cubic-bezier(0.16,1,0.3,1)" }}
        />
        <defs>
          <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#4f46e5" />
            <stop offset="100%" stopColor="#a78bfa" />
          </linearGradient>
        </defs>
      </svg>
      <div className="absolute inset-0 grid place-items-center text-center">
        <div>
          <div className="font-display text-3xl font-semibold text-zinc-100">{Math.round(value)}</div>
          <div className="text-[10px] text-zinc-500 uppercase tracking-widest font-bold">{label}</div>
        </div>
      </div>
    </div>
  );
}
