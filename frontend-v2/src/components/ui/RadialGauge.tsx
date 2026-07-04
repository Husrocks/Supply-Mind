import { memo } from 'react';
import type { RiskAccent } from '../../types';

interface RadialGaugeProps {
  value: number;
  max?: number;
  label: string;
  suffix?: string;
  accent?: RiskAccent;
  size?: number;
}

const ACCENT_STROKE: Record<RiskAccent, string> = {
  emerald: '#10b981',
  amber: '#f59e0b',
  rose: '#f43f5e',
  indigo: '#6366f1',
  cyan: '#22d3ee',
};

export const RadialGauge = memo(function RadialGauge({
  value,
  max = 100,
  label,
  suffix = '%',
  accent = 'indigo',
  size = 120,
}: RadialGaugeProps) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  const r = (size - 16) / 2;
  const c = 2 * Math.PI * r;
  const offset = c - (pct / 100) * c;

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative flex items-center justify-center">
        <svg width={size} height={size} className="-rotate-90">
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(148,163,184,0.15)" strokeWidth={8} />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke={ACCENT_STROKE[accent]}
            strokeWidth={8}
            strokeDasharray={c}
            strokeDashoffset={offset}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <p className="text-2xl font-mono tabular-nums text-ink font-semibold mt-1">
            {value.toFixed(value < 10 ? 2 : 1)}{suffix}
          </p>
        </div>
      </div>
      <p className="text-xs text-muted font-medium uppercase tracking-wider text-center">{label}</p>
    </div>
  );
});
