import { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  ComposedChart, Line, Area, ReferenceLine,
} from 'recharts';
import { Info } from 'lucide-react';
import clsx from 'clsx';
import { useInventory, useRiskContext } from '../hooks/useDashboardQueries';
import { useInView } from '../hooks/useInView';
import { usePrefersReducedMotion } from '../hooks/usePrefersReducedMotion';
import { GlassCard } from '../components/ui/GlassCard';
import { ViewSkeleton } from '../components/ui/ViewSkeleton';
import { RadialGauge } from '../components/ui/RadialGauge';
import { LeadTimeHistogram } from '../components/charts/LeadTimeHistogram';
import { StackedInventoryArea } from '../components/charts/StackedInventoryArea';
import { Sparkline } from '../components/charts/Sparkline';
import { Stagger, StaggerItem } from '../components/motion/Stagger';
import type { InventorySku } from '../types';

export function InventoryHeatmap() {
  const { data: skus = [], isLoading } = useInventory();
  const { data: riskCtx } = useRiskContext();
  const [selectedSku, setSelectedSku] = useState<InventorySku | null>(null);
  const { ref: chartRef, inView } = useInView();
  const reduced = usePrefersReducedMotion();

  const getColor = (status: string) => {
    if (status === 'CRITICAL') return '#f43f5e';
    if (status === 'ELEVATED') return '#f59e0b';
    return '#10b981';
  };

  const safetyBuffer = useMemo(() => {
    if (!selectedSku) return null;
    const days = selectedSku.days_to_stockout;
    return Math.min(100, (days / 28) * 100);
  }, [selectedSku]);

  if (isLoading) {
    return <ViewSkeleton />;
  }

  return (
    <div className="h-full overflow-y-auto p-5 lg:p-6">
      <Stagger className="max-w-content mx-auto space-y-5">
        <StaggerItem>
          <h1 className="text-xl font-semibold text-ink">Inventory Risk Heatmap</h1>
          <p className="text-sm text-body mt-1">/inventory/risk-heatmap</p>
        </StaggerItem>

        <StaggerItem>
          <GlassCard accent="indigo">
            <h2 className="text-base font-semibold flex items-center gap-2 mb-4">
              Risk matrix
              <Info size={14} className="text-muted" />
            </h2>
            <div ref={chartRef} className="h-[360px]">
              {inView && (
                <ResponsiveContainer width="100%" height="100%">
                  <ScatterChart margin={{ top: 16, right: 16, bottom: 16, left: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.12)" />
                    <XAxis type="number" dataKey="days_to_stockout" name="Days" unit=" d" stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                    <YAxis type="number" dataKey="uncertainty_spread" name="Uncertainty" stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                    <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid rgba(148,163,184,0.2)', borderRadius: 12 }} />
                    <ReferenceLine x={14} stroke="#f43f5e" strokeDasharray="4 4" />
                    {skus.map((sku: InventorySku, i: number) => (
                      <Scatter key={i} name={sku.sku_id} data={[sku]} fill={getColor(sku.status)} onClick={() => setSelectedSku(sku)} />
                    ))}
                  </ScatterChart>
                </ResponsiveContainer>
              )}
            </div>
          </GlassCard>
        </StaggerItem>

        <StaggerItem className="grid lg:grid-cols-2 gap-4">
          <StackedInventoryArea skus={skus} />
          <LeadTimeHistogram suppliers={riskCtx?.supplier_risks ?? []} />
        </StaggerItem>

        {selectedSku && (
          <StaggerItem>
            <motion.div
              initial={reduced ? false : { opacity: 0, y: 16, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ duration: 0.25, ease: 'easeOut' }}
              className="relative z-10"
            >
              <GlassCard accent="amber">
                <div className="flex flex-wrap justify-between gap-4 mb-4">
                  <div>
                    <h3 className="text-lg font-semibold text-ink">{selectedSku.sku_id}</h3>
                    <p className="text-sm text-body">Inventory: <span className="font-mono tabular-nums">{selectedSku.current_inventory}</span></p>
                  </div>
                  <div className="flex items-center gap-6">
                    {safetyBuffer !== null && (
                      <RadialGauge value={safetyBuffer} label="Safety buffer" accent="emerald" />
                    )}
                    <span className={clsx('text-xs font-semibold uppercase px-3 py-1 rounded-full border border-hairline',
                      selectedSku.status === 'CRITICAL' ? 'text-risk-high' : selectedSku.status === 'ELEVATED' ? 'text-risk-medium' : 'text-risk-low'
                    )}>{selectedSku.status}</span>
                  </div>
                </div>
                <div className="flex items-center gap-3 mb-3 text-xs text-muted">
                  <span>Inventory trend</span>
                  <Sparkline
                    data={selectedSku.forecast_history.filter((h) => h.actual !== null).map((h) => h.actual as number)}
                    color="#10b981"
                    width={120}
                    height={28}
                  />
                </div>
                <div className="h-[280px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={selectedSku.forecast_history}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.12)" />
                      <XAxis dataKey="date" stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                      <YAxis stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                      <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid rgba(148,163,184,0.2)', borderRadius: 12 }} />
                      <Area type="monotone" dataKey="p95" fill="rgba(99,102,241,0.06)" stroke="none" isAnimationActive={!reduced} />
                      <Area type="monotone" dataKey="p05" fill="#020617" stroke="none" isAnimationActive={!reduced} />
                      <Line type="monotone" dataKey="actual" stroke="#10b981" strokeWidth={2} dot={{ r: 2 }} isAnimationActive={!reduced} />
                      <Line type="monotone" dataKey="p50" stroke="#6366f1" strokeDasharray="4 4" strokeWidth={2} dot={false} isAnimationActive={!reduced} />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              </GlassCard>
            </motion.div>
          </StaggerItem>
        )}
      </Stagger>
    </div>
  );
}

export default InventoryHeatmap;
