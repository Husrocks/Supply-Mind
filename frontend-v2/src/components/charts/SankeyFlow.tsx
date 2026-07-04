import { memo, useMemo } from 'react';
import { Sankey, Tooltip, Layer, Rectangle, ResponsiveContainer } from 'recharts';
import type { SupplierRisk, DemandForecast, SupplyFlow } from '../../types';
import { riskScoreColor } from '../../utils/risk';
import { useInView } from '../../hooks/useInView';
import { Info } from 'lucide-react';
import { GlassCard } from '../ui/GlassCard';

interface SankeyFlowProps {
  suppliers: SupplierRisk[];
  forecasts: DemandForecast[];
  supplyFlows?: SupplyFlow[];
}

export const SankeyFlow = memo(function SankeyFlow({ suppliers, forecasts, supplyFlows }: SankeyFlowProps) {
  const { ref, inView } = useInView();

  const { nodes, links } = useMemo(() => {
    const nodeNames: string[] = [];
    const nodeIndex = new Map<string, number>();
    const getIdx = (name: string) => {
      if (!nodeIndex.has(name)) {
        nodeIndex.set(name, nodeNames.length);
        nodeNames.push(name);
      }
      return nodeIndex.get(name)!;
    };

    const linkList: { source: number; target: number; value: number; risk: number }[] = [];

    const flows = supplyFlows?.length
      ? supplyFlows
      : suppliers.map((s, i) => {
          const sku = forecasts[i % Math.max(forecasts.length, 1)];
          return {
            supplier_id: s.supplier_id,
            supplier_name: s.supplier_name,
            category: sku?.category ?? sku?.sku_id.split('_')[0] ?? 'General',
            warehouse: 'Central Distribution Hub',
            volume: Math.max(1, Math.round(s.concentration_ratio * 100)),
            risk_score: s.risk_score,
          };
        });

    for (const flow of flows) {
      const si = getIdx(flow.supplier_name);
      const ci = getIdx(flow.category);
      const wi = getIdx(flow.warehouse);
      linkList.push({ source: si, target: ci, value: flow.volume, risk: flow.risk_score });
      linkList.push({ source: ci, target: wi, value: flow.volume, risk: flow.risk_score });
    }

    return {
      nodes: nodeNames.map((name) => ({ name })),
      links: linkList,
    };
  }, [suppliers, forecasts, supplyFlows]);

  const data = useMemo(() => ({ nodes, links }), [nodes, links]);

  return (
    <GlassCard accent="cyan">
        <h3 className="text-base font-semibold text-ink mb-1 flex items-center gap-2">
        Supply Flow
        <span title="Visualizes how products move from your Suppliers, through product Categories, and into your Warehouses. Thicker lines mean more volume." className="flex items-center">
          <Info size={16} className="text-muted hover:text-indigo-400 cursor-help transition-colors" />
        </span>
      </h3>
      <p className="text-xs text-muted mb-4">Supplier → category → warehouse (volume from API supply_flows)</p>
      <div ref={ref}>
      {inView && links.length > 0 ? (
        <div className="h-[280px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <Sankey
              data={data}
              nodePadding={24}
              margin={{ left: 8, right: 8, top: 8, bottom: 8 }}
              node={(props) => {
                const { x, y, width, height, index, payload } = props;
                const label = (payload as { name: string }).name;
                return (
                  <Layer key={`node-${index}`}>
                    <Rectangle x={x} y={y} width={width} height={height} fill="#334155" fillOpacity={0.9} radius={4} />
                    {height > 12 && (
                      <text x={x + width / 2} y={y + height / 2} textAnchor="middle" dominantBaseline="middle" fill="#e2e8f0" fontSize={9}>
                        {label.length > 10 ? label.slice(0, 8) + '..' : label}
                      </text>
                    )}
                  </Layer>
                );
              }}
              link={(props) => {
                const { sourceX, targetX, sourceY, targetY, sourceControlX, targetControlX, linkWidth, index, payload } = props;
                const risk = (payload as { risk?: number }).risk ?? 0.5;
                return (
                  <Layer key={`link-${index}`}>
                    <path
                      d={`M${sourceX},${sourceY} C${sourceControlX},${sourceY} ${targetControlX},${targetY} ${targetX},${targetY}`}
                      fill="none"
                      stroke={riskScoreColor(risk)}
                      strokeWidth={Math.max(1, linkWidth)}
                      strokeOpacity={0.45}
                    />
                  </Layer>
                );
              }}
            >
              <Tooltip
                contentStyle={{ background: '#0f172a', border: '1px solid rgba(148,163,184,0.2)', borderRadius: 12, fontSize: 12, color: '#e2e8f0' }}
                itemStyle={{ color: '#cbd5e1' }}
              />
            </Sankey>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="h-[280px] flex items-center justify-center text-muted text-sm">No flow data</div>
      )}
      </div>
    </GlassCard>
  );
});
