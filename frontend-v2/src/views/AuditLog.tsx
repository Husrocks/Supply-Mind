import { useRef, useState } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { Clock, FileX, Zap, Calendar, MousePointer, BarChart2, Trash2 } from 'lucide-react';
import clsx from 'clsx';
import { useAllActions, useDeleteAction } from '../hooks/useDashboardQueries';
import { ViewSkeleton } from '../components/ui/ViewSkeleton';
import { ActionTierDonut } from '../components/charts/ActionTierDonut';
import { EmptyState } from '../components/EmptyState';
import { GlassCard } from '../components/ui/GlassCard';
import { Stagger, StaggerItem } from '../components/motion/Stagger';
import type { AgentAction } from '../types';

// ── Helpers ───────────────────────────────────────────────────────────────────

function statusConfig(status: string): { label: string; className: string } {
  switch (status.toUpperCase()) {
    case 'EXECUTED':
      return { label: 'Executed', className: 'text-risk-low' };
    case 'APPROVED':
      return { label: 'Approved', className: 'text-accent-cyan' };
    case 'REJECTED':
      return { label: 'Rejected', className: 'text-risk-high' };
    case 'PENDING':
    default:
      return { label: 'Pending', className: 'text-risk-medium' };
  }
}

const TRIGGER_ICONS: Record<string, React.ElementType> = {
  MANUAL: MousePointer,
  SCHEDULED: Calendar,
  EVENT: Zap,
  THRESHOLD: BarChart2,
};

function TriggerBadge({ triggerType }: { triggerType?: string }) {
  const key = (triggerType ?? 'MANUAL').toUpperCase();
  const Icon = TRIGGER_ICONS[key] ?? MousePointer;
  return (
    <span className="inline-flex items-center gap-1 text-[10px] font-medium text-muted bg-slate-800/60 border border-slate-700/50 rounded-full px-2 py-0.5">
      <Icon size={10} />
      {key}
    </span>
  );
}

// ── Virtual List ─────────────────────────────────────────────────────────────

function VirtualAuditList({ logs }: { logs: AgentAction[] }) {
  const parentRef = useRef<HTMLDivElement>(null);
  const [expandedIds, setExpandedIds] = useState<Record<string, boolean>>({});
  const { mutate: deleteAction, isPending: isDeleting } = useDeleteAction();

  const virtualizer = useVirtualizer({
    count: logs.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 160,
    overscan: 5,
  });

  return (
    <div ref={parentRef} className="h-[520px] overflow-y-auto">
      <div style={{ height: virtualizer.getTotalSize(), position: 'relative' }}>
        {virtualizer.getVirtualItems().map((item) => {
          const log = logs[item.index];
          const sc = statusConfig(log.status);
          return (
            <div
              key={log.action_id}
              ref={virtualizer.measureElement}
              data-index={item.index}
              className="absolute left-0 w-full px-1"
              style={{ transform: `translateY(${item.start}px)` }}
            >
              <GlassCard accent="indigo" className="!p-4 mb-3">
                {/* Header row: status + trigger badge + timestamp */}
                <div className="flex flex-wrap justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <span className={clsx('text-xs font-semibold uppercase', sc.className)}>
                      {sc.label}
                    </span>
                    <TriggerBadge triggerType={log.trigger_type} />
                  </div>
                  <span className="text-xs text-muted flex items-center gap-1">
                    <Clock size={12} />{new Date(log.created_at).toLocaleString()}
                  </span>
                </div>

                <h3 className="text-sm font-semibold text-ink">{log.action_type.replace(/_/g, ' ')}</h3>
                
                <div className="text-xs text-body mt-2">
                  <p className={clsx(expandedIds[log.action_id] ? 'block' : 'line-clamp-2')}>
                    {log.reasoning}
                  </p>
                  {log.reasoning && log.reasoning.length > 120 && (
                    <button
                      onClick={() => {
                        setExpandedIds(prev => ({
                          ...prev,
                          [log.action_id]: !prev[log.action_id]
                        }));
                      }}
                      className="text-[10px] text-accent-indigo hover:underline mt-1 font-medium block"
                    >
                      {expandedIds[log.action_id] ? 'Show less' : 'Read full justification'}
                    </button>
                  )}
                </div>

                {/* Footer row: supplier, SKU, cost, confidence */}
                <div className="flex flex-wrap gap-3 text-[11px] text-muted mt-3">
                  <span>Supplier: <span className="text-body font-medium">{log.supplier_id}</span></span>
                  <span>SKU: <span className="text-body font-medium">{log.sku_id}</span></span>
                  {(log.estimated_impact?.cost_delta ?? 0) > 0 && (
                    <span className="font-mono text-body">${log.estimated_impact.cost_delta!.toLocaleString()}</span>
                  )}
                  {log.confidence_score != null ? (
                    <span className="ml-auto flex items-center gap-3 font-medium">
                      <span>
                        Confidence:{' '}
                        <span className={clsx('font-mono tabular-nums', log.confidence_score >= 0.75 ? 'text-risk-low' : log.confidence_score >= 0.55 ? 'text-risk-medium' : 'text-risk-high')}>
                          {(log.confidence_score * 100).toFixed(0)}%
                        </span>
                      </span>
                      <button
                        onClick={() => deleteAction(log.action_id)}
                        disabled={isDeleting}
                        className="text-risk-high opacity-50 hover:opacity-100 transition-opacity"
                        title="Delete log"
                      >
                        <Trash2 size={13} />
                      </button>
                    </span>
                  ) : (
                    <div className="ml-auto flex items-center">
                      <button
                        onClick={() => deleteAction(log.action_id)}
                        disabled={isDeleting}
                        className="text-risk-high opacity-50 hover:opacity-100 transition-opacity"
                        title="Delete log"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  )}
                </div>
              </GlassCard>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── View ──────────────────────────────────────────────────────────────────────

export function AuditLog() {
  const { data: actions = [], isLoading } = useAllActions();

  if (isLoading) {
    return <ViewSkeleton />;
  }

  const sorted = [...actions].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );

  return (
    <div className="h-full overflow-y-auto p-5 lg:p-6">
      <Stagger className="max-w-content mx-auto space-y-5">
        <StaggerItem>
          <h1 className="text-xl font-semibold text-ink">Agent Audit Log</h1>
          <p className="text-sm text-body mt-1">/agent/actions — full action history</p>
        </StaggerItem>

        <StaggerItem>
          <ActionTierDonut actions={actions} />
        </StaggerItem>

        {sorted.length === 0 ? (
          <EmptyState icon={<FileX size={28} />} title="Audit log empty" description="No actions logged yet." />
        ) : (
          <StaggerItem>
            <VirtualAuditList logs={sorted} />
          </StaggerItem>
        )}
      </Stagger>
    </div>
  );
}

export default AuditLog;
