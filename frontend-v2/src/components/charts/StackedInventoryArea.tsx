import { memo, useMemo } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import type { InventorySku } from '../../types';
import { useInView } from '../../hooks/useInView';
import { usePrefersReducedMotion } from '../../hooks/usePrefersReducedMotion';
import { GlassCard } from '../ui/GlassCard';

const AREA_COLORS = ['#06b6d4', '#22d3ee', '#10b981', '#f59e0b', '#f43f5e'];

interface StackedInventoryAreaProps {
  skus: InventorySku[];
  topN?: number;
}

export const StackedInventoryArea = memo(function StackedInventoryArea({ skus, topN = 5 }: StackedInventoryAreaProps) {
  const { ref, inView } = useInView();
  const reduced = usePrefersReducedMotion();

  const { chartData, keys } = useMemo(() => {
    const critical = [...skus]
      .sort((a, b) => a.days_to_stockout - b.days_to_stockout)
      .slice(0, topN);
    const dateSet = new Set<string>();
    critical.forEach((s) => s.forecast_history.forEach((h) => dateSet.add(h.date)));
    const dates = [...dateSet].sort();
    const keys = critical.map((s) => s.sku_id);
    const chartData = dates.map((date) => {
      const row: Record<string, string | number> = { date };
      critical.forEach((s) => {
        const pt = s.forecast_history.find((h) => h.date === date);
        row[s.sku_id] = pt?.actual ?? pt?.p50 ?? 0;
      });
      return row;
    });
    return { chartData, keys };
  }, [skus, topN]);

  return (
    <GlassCard accent="emerald">
      <h3 className="text-base font-semibold text-ink mb-1">Multi-SKU Inventory Trend</h3>
      <p className="text-xs text-muted mb-4">Stacked from /inventory/risk-heatmap forecast_history</p>
      <div ref={ref} className="h-[260px]">
        {inView && chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.12)" />
              <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 9 }} minTickGap={32} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} />
              <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid rgba(148,163,184,0.2)', borderRadius: 12 }} />
              <Legend wrapperStyle={{ fontSize: 10 }} />
              {keys.map((k, i) => (
                <Area
                  key={k}
                  type="monotone"
                  dataKey={k}
                  stackId="1"
                  stroke={AREA_COLORS[i % AREA_COLORS.length]}
                  fill={AREA_COLORS[i % AREA_COLORS.length]}
                  fillOpacity={0.35}
                  isAnimationActive={!reduced}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-full flex items-center justify-center text-muted text-sm">No inventory history</div>
        )}
      </div>
    </GlassCard>
  );
});
