import { memo } from 'react';
import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react';
import clsx from 'clsx';
import { useCountUp } from '../../hooks/useCountUp';
import { GlassCard } from '../ui/GlassCard';
import type { RiskAccent } from '../../types';

export interface BenchmarkMetric {
  label: string;
  current: number;
  previous: number | null;
  format?: (v: number) => string;
  invertDelta?: boolean;
}

function BenchmarkCard({ m }: { m: BenchmarkMetric }) {
  const animated = useCountUp(m.current);
  const hasDelta = m.previous !== null && m.previous !== 0;
  const delta = hasDelta ? ((m.current - m.previous!) / m.previous!) * 100 : 0;
  const up = delta > 0;
  const bad = m.invertDelta ? up : !up;
  const accent: RiskAccent = !hasDelta ? 'indigo' : bad && delta !== 0 ? 'rose' : delta !== 0 ? 'emerald' : 'indigo';

  return (
    <GlassCard accent={accent} className="min-w-0">
      <p className="text-[11px] text-muted uppercase tracking-wider truncate" title={m.label}>{m.label}</p>
      <p className="text-[clamp(1.25rem,4vw,1.5rem)] font-mono tabular-nums text-ink mt-1 leading-none truncate" title={(m.format ?? ((v) => v.toFixed(0)))(animated)}>
        {(m.format ?? ((v) => v.toFixed(0)))(animated)}
      </p>
      {hasDelta ? (
        <div className={clsx('flex items-center gap-1 mt-2 text-xs font-medium truncate', bad ? 'text-risk-high' : 'text-risk-low')}>
          {delta >= 0 ? <ArrowUpRight size={12} className="shrink-0" /> : <ArrowDownRight size={12} className="shrink-0" />}
          <span className="tabular-nums">{Math.abs(delta).toFixed(1)}%</span>
          <span className="text-muted hidden sm:inline">vs prior</span>
        </div>
      ) : (
        <div className="flex items-center gap-1 mt-2 text-xs text-muted truncate">
          <Minus size={12} className="shrink-0" />
          <span>Snapshot</span>
        </div>
      )}
    </GlassCard>
  );
}

interface ComparisonCardsProps {
  metrics: BenchmarkMetric[];
}

export const ComparisonCards = memo(function ComparisonCards({ metrics }: ComparisonCardsProps) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {metrics.map((m) => (
        <BenchmarkCard key={m.label} m={m} />
      ))}
    </div>
  );
});
