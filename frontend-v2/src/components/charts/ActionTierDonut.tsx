import { memo, useMemo } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import type { AgentAction } from '../../types';
import { tierFromStatus } from '../../utils/risk';
import { useInView } from '../../hooks/useInView';
import { usePrefersReducedMotion } from '../../hooks/usePrefersReducedMotion';
import { GlassCard } from '../ui/GlassCard';

const TIER_COLORS: Record<string, string> = {
  'Tier 1': '#10b981',
  'Tier 2': '#f59e0b',
  'Tier 3': '#f43f5e',
};

interface ActionTierDonutProps {
  actions: AgentAction[];
}

export const ActionTierDonut = memo(function ActionTierDonut({ actions }: ActionTierDonutProps) {
  const { ref, inView } = useInView();
  const reduced = usePrefersReducedMotion();

  const data = useMemo(() => {
    const counts = { 'Tier 1': 0, 'Tier 2': 0, 'Tier 3': 0 };
    for (const a of actions) {
      counts[tierFromStatus(a.status)] += 1;
    }
    return Object.entries(counts)
      .filter(([, v]) => v > 0)
      .map(([name, value]) => ({ name, value }));
  }, [actions]);

  return (
    <GlassCard accent="indigo">
      <h3 className="text-base font-semibold text-ink mb-1">Action Tier Distribution</h3>
      <p className="text-xs text-muted mb-4">From /agent/actions status field</p>
      <div ref={ref} className="h-[220px]">
        {inView && data.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={52}
                outerRadius={78}
                paddingAngle={2}
                isAnimationActive={!reduced}
              >
                {data.map((entry) => (
                  <Cell key={entry.name} fill={TIER_COLORS[entry.name]} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid rgba(148,163,184,0.2)', borderRadius: 12 }} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
            </PieChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-full flex items-center justify-center text-muted text-sm">No actions logged</div>
        )}
      </div>
    </GlassCard>
  );
});
