import { memo } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Line } from 'recharts';
import { Info } from 'lucide-react';
import type { DemandForecast } from '../../types';
import { useInView } from '../../hooks/useInView';
import { usePrefersReducedMotion } from '../../hooks/usePrefersReducedMotion';
import { GlassCard } from '../ui/GlassCard';

interface DemandForecastChartProps {
  forecasts: DemandForecast[];
}

export const DemandForecastChart = memo(function DemandForecastChart({ forecasts }: DemandForecastChartProps) {
  const { ref, inView } = useInView();
  const reduced = usePrefersReducedMotion();

  const data = forecasts.map((f) => ({
    name: f.sku_id,
    p50: f.forecast_units,
    p05: f.confidence_lower,
    p95: f.confidence_upper,
    actual: f.actual_units,
  }));

  return (
    <GlassCard accent="indigo">
      <h3 className="text-base font-semibold text-ink mb-1 flex items-center gap-2">
        Demand Forecast
        <span title="Predicts how many units of each product customers will buy soon. The shaded blue area shows the range of possible demand so you can prepare buffer stock." className="flex items-center">
          <Info size={16} className="text-muted hover:text-indigo-400 cursor-help transition-colors" />
        </span>
      </h3>
      <p className="text-xs text-muted mb-4">P05–P95 band from demand_forecasts confidence bounds</p>
      <div ref={ref} className="h-[260px]">
        {inView && data.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.12)" />
              <XAxis 
                dataKey="name" 
                tick={{ fill: '#94a3b8', fontSize: 9 }} 
                tickFormatter={(val) => String(val).replace(/_evaluation|_validation/gi, '').split('_').slice(0, 3).join('_')}
              />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} />
              <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid rgba(148,163,184,0.2)', borderRadius: 12 }} />
              <Area type="monotone" dataKey="p95" stroke="none" fill="#06b6d4" fillOpacity={0.15} isAnimationActive={!reduced} />
              <Area type="monotone" dataKey="p05" stroke="none" fill="#020617" fillOpacity={1} isAnimationActive={!reduced} />
              <Line type="monotone" dataKey="p50" stroke="#06b6d4" strokeWidth={2} dot={{ r: 3 }} isAnimationActive={!reduced} />
              <Line type="monotone" dataKey="actual" stroke="#10b981" strokeWidth={2} dot={{ r: 3 }} isAnimationActive={!reduced} />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-full flex items-center justify-center text-muted text-sm">No forecast data</div>
        )}
      </div>
    </GlassCard>
  );
});
