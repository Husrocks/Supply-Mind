import { memo, useRef } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import type { SupplierRisk } from '../../types';
import { riskScoreColor } from '../../utils/risk';
import { Sparkline } from '../charts/Sparkline';
import { GlassCard } from '../ui/GlassCard';

interface SupplierTableProps {
  suppliers: SupplierRisk[];
  skuSparklines?: Record<string, number[]>;
  onSelect?: (supplier: SupplierRisk) => void;
}

export const SupplierTable = memo(function SupplierTable({
  suppliers,
  skuSparklines,
  onSelect,
}: SupplierTableProps) {
  const parentRef = useRef<HTMLDivElement>(null);

  const rowVirtualizer = useVirtualizer({
    count: suppliers.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 48, // typical height of a row
    overscan: 5,
  });

  return (
    <GlassCard accent="indigo" className="!p-0 overflow-hidden">
      <div className="p-6 pb-3">
        <h3 className="text-base font-semibold text-ink">Supplier Risk Table</h3>
        <p className="text-xs text-muted">Select a supplier to view detailed metrics and mitigation controls</p>
      </div>

      {/* Mobile Stacked Card Layout */}
      <div className="block sm:hidden px-4 pb-4 space-y-3">
        {suppliers.map((s) => {
          const trend = skuSparklines?.[s.supplier_id];
          return (
            <div
              key={s.supplier_id}
              className="p-4 rounded-xl bg-slate-900/60 border border-hairline hover:bg-slate-800/40 cursor-pointer active:scale-[0.99] transition-transform"
              onClick={() => onSelect?.(s)}
            >
              <div className="flex justify-between items-start mb-2">
                <h4 className="font-semibold text-ink text-sm truncate max-w-[70%]" title={s.supplier_name}>
                  {s.supplier_name}
                </h4>
                <span className="text-[10px] text-muted font-mono">{s.supplier_id}</span>
              </div>
              <div className="grid grid-cols-3 gap-2 items-center text-xs mt-3">
                <div>
                  <div className="text-[10px] text-muted uppercase">Risk</div>
                  <div className="font-mono font-bold mt-0.5" style={{ color: riskScoreColor(s.risk_score) }}>
                    {(s.risk_score * 100).toFixed(0)}%
                  </div>
                </div>
                <div>
                  <div className="text-[10px] text-muted uppercase">Tier</div>
                  <div className="text-body capitalize mt-0.5">{s.risk_tier}</div>
                </div>
                <div className="flex flex-col items-end">
                  <div className="text-[10px] text-muted uppercase mb-1">Trend</div>
                  <Sparkline data={trend ?? []} color={riskScoreColor(s.risk_score)} width={60} height={14} />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Desktop/Tablet Grid-based Virtualized Layout */}
      <div className="hidden sm:block w-full">
        {/* Table Header */}
        <div className="grid grid-cols-12 px-6 py-3 text-xs font-semibold text-muted border-t border-hairline bg-slate-900/40 select-none">
          <div className="col-span-5">Supplier</div>
          <div className="col-span-2">Risk</div>
          <div className="col-span-2">Tier</div>
          <div className="col-span-3">Trend</div>
        </div>

        {/* Scrollable container with fixed height */}
        <div
          ref={parentRef}
          className="overflow-y-auto max-h-[350px] w-full relative"
        >
          <div
            style={{
              height: `${rowVirtualizer.getTotalSize()}px`,
              width: '100%',
              position: 'relative',
            }}
          >
            {rowVirtualizer.getVirtualItems().map((virtualRow) => {
              const s = suppliers[virtualRow.index];
              const trend = skuSparklines?.[s.supplier_id];
              return (
                <div
                  key={s.supplier_id}
                  onClick={() => onSelect?.(s)}
                  className="grid grid-cols-12 px-6 py-3 items-center hover:bg-slate-800/30 cursor-pointer border-t border-hairline text-sm absolute top-0 left-0 w-full"
                  style={{
                    height: `${virtualRow.size}px`,
                    transform: `translateY(${virtualRow.start}px)`,
                  }}
                >
                  <div className="col-span-5 text-ink font-medium truncate pr-4" title={s.supplier_name}>
                    {s.supplier_name}
                  </div>
                  <div className="col-span-2 font-mono tabular-nums" style={{ color: riskScoreColor(s.risk_score) }}>
                    {(s.risk_score * 100).toFixed(0)}%
                  </div>
                  <div className="col-span-2 text-body capitalize">{s.risk_tier}</div>
                  <div className="col-span-3">
                    <Sparkline data={trend ?? []} color={riskScoreColor(s.risk_score)} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </GlassCard>
  );
});

export default SupplierTable;
