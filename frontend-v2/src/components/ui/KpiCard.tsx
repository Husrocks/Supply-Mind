import { memo } from 'react';
import { ArrowDownRight, ArrowUpRight, Minus, Info } from 'lucide-react';
import clsx from 'clsx';
import { useCountUp } from '../../hooks/useCountUp';
import type { RiskAccent } from '../../types';

interface KpiCardProps {
  label: string;
  value: number;
  format?: (v: number) => string;
  delta?: number | null;
  deltaLabel?: string;
  accent?: RiskAccent;
  onClick?: () => void;
  tooltip?: string;
}

export const KpiCard = memo(function KpiCard({
  label,
  value,
  format = (v) => v.toFixed(0),
  delta,
  deltaLabel,
  accent = 'indigo',
  onClick,
  tooltip,
}: KpiCardProps) {
  const animated = useCountUp(value);
  const hasDelta = delta !== null && delta !== undefined && !Number.isNaN(delta);
  const up = hasDelta && delta > 0;
  const down = hasDelta && delta < 0;

  return (
    <div 
      className={clsx(
        'glass-card min-w-0 transition-transform duration-200', 
        `glass-card--${accent}`,
        onClick && 'cursor-pointer hover:-translate-y-1 hover:shadow-lg'
      )}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      <div className="flex justify-between items-start mb-2">
        <p className="text-xs font-medium text-body uppercase tracking-wider truncate flex-1" title={label}>
          {label}
        </p>
        {tooltip && (
          <span title={tooltip} className="ml-2 flex-shrink-0">
            <Info size={14} className="text-muted hover:text-indigo-400 cursor-help transition-colors" />
          </span>
        )}
      </div>
      <p className="text-[clamp(1.5rem,4.5vw,1.875rem)] font-mono tabular-nums text-ink tracking-tight leading-none my-1 truncate" title={format(animated)}>{format(animated)}</p>
      {hasDelta && (
        <div className={clsx('flex items-center gap-1 mt-2 text-xs font-medium', up ? 'text-risk-high' : down ? 'text-risk-low' : 'text-body')}>
          {up ? <ArrowUpRight size={14} /> : down ? <ArrowDownRight size={14} /> : <Minus size={14} />}
          <span className="tabular-nums">{Math.abs(delta).toFixed(1)}%</span>
          {deltaLabel && <span className="text-muted ml-1">{deltaLabel}</span>}
        </div>
      )}
    </div>
  );
});
