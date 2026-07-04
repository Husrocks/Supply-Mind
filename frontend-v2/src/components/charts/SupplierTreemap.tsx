import { memo, useMemo, useState } from 'react';
import { Treemap, ResponsiveContainer, Tooltip } from 'recharts';
import type { SupplierRisk } from '../../types';
import { riskScoreColor } from '../../utils/risk';
import { useInView } from '../../hooks/useInView';
import { usePrefersReducedMotion } from '../../hooks/usePrefersReducedMotion';
import { Info } from 'lucide-react';
import { GlassCard } from '../ui/GlassCard';

interface SupplierTreemapProps {
  suppliers: SupplierRisk[];
  onSelectSupplier?: (supplier: SupplierRisk) => void;
}

function TreemapCell(props: {
  x?: number; y?: number; width?: number; height?: number;
  name?: string; risk?: number; id?: string;
  onSelect: (id: string) => void;
}) {
  const { x = 0, y = 0, width = 0, height = 0, name, risk = 0, id, onSelect } = props;
  if (width < 4 || height < 4) {
    return <g />;
  }
  return (
    <g>
      <rect
        x={x} y={y} width={width} height={height}
        fill={riskScoreColor(risk)} fillOpacity={0.75}
        stroke="#0f172a" strokeWidth={2}
        style={{ cursor: 'pointer' }}
        onClick={() => id && onSelect(id)}
      />
      {width > 28 && height > 16 && (
        <text 
          x={x + 4} 
          y={y + 12} 
          fill="#0f172a" 
          fillOpacity={0.85} 
          fontSize={9} 
          fontWeight="600" 
          style={{ pointerEvents: 'none' }}
        >
          {String(name).slice(0, Math.max(3, Math.floor((width - 8) / 5.5)))}
        </text>
      )}
    </g>
  );
}

export const SupplierTreemap = memo(function SupplierTreemap({ suppliers, onSelectSupplier }: SupplierTreemapProps) {
  const { ref, inView } = useInView();
  const reduced = usePrefersReducedMotion();
  const [selected, setSelected] = useState<string | null>(null);

  const data = useMemo(() =>
    suppliers.map((s) => ({
      name: s.supplier_name,
      size: Math.max(1, Math.round(s.concentration_ratio * 100)),
      risk: s.risk_score,
      id: s.supplier_id,
    })),
  [suppliers]);

  const filtered = selected ? data.filter((d) => d.id === selected) : data;

  const handleSelect = (id: string) => {
    setSelected(id);
    const s = suppliers.find(sup => sup.supplier_id === id);
    if (s && onSelectSupplier) {
      onSelectSupplier(s);
    }
  };

  return (
    <GlassCard accent="amber">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-base font-semibold text-ink flex items-center gap-2">
          Risk Concentration
          <span title="Shows which suppliers you rely on the most. Bigger boxes mean you buy more from them. Red boxes mean they are currently high risk!" className="flex items-center">
            <Info size={16} className="text-muted hover:text-indigo-400 cursor-help transition-colors" />
          </span>
        </h3>
          <p className="text-xs text-muted">Size = concentration_ratio · color = risk_score</p>
        </div>
        {selected && (
          <button type="button" onClick={() => setSelected(null)} className="text-xs text-accent-cyan">
            Reset
          </button>
        )}
      </div>
      <div ref={ref} className="h-[260px]">
        {inView && (
          <ResponsiveContainer width="100%" height="100%">
            <Treemap
              data={filtered}
              dataKey="size"
              aspectRatio={4 / 3}
              stroke="#0f172a"
              isAnimationActive={!reduced}
              content={(props) => <TreemapCell {...props} onSelect={handleSelect} />}
            >
              <Tooltip
                contentStyle={{ background: '#0f172a', border: '1px solid rgba(148,163,184,0.2)', borderRadius: 12, color: '#e2e8f0' }}
                itemStyle={{ color: '#cbd5e1' }}
                formatter={(_v, _n, item) => [`${((item.payload?.risk as number) * 100).toFixed(0)}% risk`, 'Score']}
              />
            </Treemap>
          </ResponsiveContainer>
        )}
      </div>
    </GlassCard>
  );
});
