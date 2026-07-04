import { memo, useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import type { SupplierRisk } from '../../types';
import { binLeadTimeDays } from '../../utils/risk';
import { useInView } from '../../hooks/useInView';
import { usePrefersReducedMotion } from '../../hooks/usePrefersReducedMotion';
import { GlassCard } from '../ui/GlassCard';

const BIN_ORDER = ['0–7 days', '8–14 days', '15–21 days', '22–28 days', '29+ days'];

interface LeadTimeHistogramProps {
  suppliers: SupplierRisk[];
}

export const LeadTimeHistogram = memo(function LeadTimeHistogram({ suppliers }: LeadTimeHistogramProps) {
  const { ref, inView } = useInView();
  const reduced = usePrefersReducedMotion();

  const data = useMemo(() => {
    const bins = new Map(BIN_ORDER.map((b) => [b, 0]));
    for (const s of suppliers) {
      const days = s.avg_lead_time_days ?? Math.round(s.lead_time_variance * 35 + 7);
      const bin = binLeadTimeDays(days);
      bins.set(bin, (bins.get(bin) ?? 0) + 1);
    }
    return BIN_ORDER.map((name) => ({ name, count: bins.get(name) ?? 0 }));
  }, [suppliers]);

  return (
    <GlassCard accent="amber">
      <h3 className="text-base font-semibold text-ink mb-1">Lead Time Distribution</h3>
      <p className="text-xs text-muted mb-4">Binned from avg_lead_time_days (API field)</p>
      <div ref={ref} className="h-[220px]">
        {inView && (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.12)" vertical={false} />
              <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 10 }} />
              <YAxis allowDecimals={false} tick={{ fill: '#94a3b8', fontSize: 10 }} />
              <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid rgba(148,163,184,0.2)', borderRadius: 12 }} />
              <Bar dataKey="count" radius={[4, 4, 0, 0]} isAnimationActive={!reduced}>
                {data.map((_, i) => (
                  <Cell key={i} fill="#f59e0b" fillOpacity={0.85} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </GlassCard>
  );
});
