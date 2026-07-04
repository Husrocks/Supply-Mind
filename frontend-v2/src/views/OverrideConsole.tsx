import { useState } from 'react';
import clsx from 'clsx';
import { CheckCircle, XCircle, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';
import type { AgentAction } from '../types';
import { usePendingActions, useApproveAction, useRejectAction } from '../hooks/useDashboardQueries';
import { EmptyState } from '../components/EmptyState';
import { GlassCard } from '../components/ui/GlassCard';
import { ViewSkeleton } from '../components/ui/ViewSkeleton';
import { Stagger, StaggerItem } from '../components/motion/Stagger';
import { motion, AnimatePresence } from 'framer-motion';
import { usePrefersReducedMotion } from '../hooks/usePrefersReducedMotion';

export function OverrideConsole() {
  const { data: actions = [], isLoading } = usePendingActions();
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [expandedIds, setExpandedIds] = useState<Record<string, boolean>>({});
  const reduced = usePrefersReducedMotion();

  const approveMutation = useApproveAction();
  const rejectMutation = useRejectAction();

  const handleApprove = async (id: string) => {
    setProcessingId(id);
    approveMutation.mutate(
      { actionId: id },
      {
        onSuccess: () => {
          toast.success('Action approved');
          setProcessingId(null);
        },
        onError: (error: any) => {
          toast.error(error.message || 'Approval failed');
          setProcessingId(null);
        },
      }
    );
  };

  const handleReject = async (id: string) => {
    setProcessingId(id);
    rejectMutation.mutate(
      { actionId: id, reason: 'Rejected via Override Console' },
      {
        onSuccess: () => {
          toast.success('Action rejected');
          setProcessingId(null);
        },
        onError: (error: any) => {
          toast.error(error.message || 'Rejection failed');
          setProcessingId(null);
        },
      }
    );
  };

  if (isLoading) {
    return <ViewSkeleton />;
  }

  return (
    <div className="h-full overflow-y-auto p-5 lg:p-6">
      <Stagger className="max-w-content mx-auto space-y-5">
        <StaggerItem>
          <h1 className="text-xl font-semibold text-ink">Intervention Console</h1>
          <p className="text-sm text-body mt-1">/agent/actions?status=PENDING</p>
        </StaggerItem>

        {actions.length === 0 ? (
          <EmptyState icon={<CheckCircle size={28} />} title="System optimal" description="No pending escalations." />
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <AnimatePresence>
              {actions.map((action: AgentAction) => (
                <motion.div
                  key={action.action_id}
                  layout={!reduced}
                  initial={reduced ? false : { opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={reduced ? undefined : { opacity: 0, scale: 0.98 }}
                  transition={{ duration: 0.18 }}
                >
                  <GlassCard accent="amber" className="flex flex-col h-full">
                    <div className="flex justify-between mb-3">
                      <span className="text-xs font-semibold text-risk-medium uppercase">Requires review</span>
                      <span className="text-xs text-muted">{new Date(action.created_at).toLocaleString()}</span>
                    </div>
                    <h3 className="text-base font-semibold text-ink">{action.action_type.replace(/_/g, ' ')}</h3>
                    <p className="text-xs text-muted mt-1">Supplier: {action.supplier_id} · SKU: {action.sku_id}</p>
                    
                    <div className="text-sm text-body mt-3 flex-1">
                      <p className={clsx(expandedIds[action.action_id] ? 'block' : 'line-clamp-3')}>
                        {action.reasoning}
                      </p>
                      {action.reasoning && action.reasoning.length > 180 && (
                        <button
                          onClick={() => setExpandedIds(prev => ({ ...prev, [action.action_id]: !prev[action.action_id] }))}
                          className="text-xs text-accent-indigo hover:underline mt-1 font-medium block"
                        >
                          {expandedIds[action.action_id] ? 'Show less' : 'Read full justification'}
                        </button>
                      )}
                    </div>

                    {action.estimated_impact?.cost_delta !== undefined && (
                      <p className="font-mono text-risk-high text-lg mt-2">${action.estimated_impact.cost_delta.toLocaleString()}</p>
                    )}
                    <div className="flex justify-end gap-3 mt-4 pt-4 border-t border-hairline">
                      <button type="button" onClick={() => handleReject(action.action_id)} disabled={processingId === action.action_id} className="btn-secondary !h-9 text-sm">
                        <XCircle size={14} /> Reject
                      </button>
                      <button type="button" onClick={() => handleApprove(action.action_id)} disabled={processingId === action.action_id} className="btn-primary !h-9 text-sm">
                        {processingId === action.action_id ? <Loader2 className="animate-spin" size={14} /> : <CheckCircle size={14} />}
                        Approve
                      </button>
                    </div>
                  </GlassCard>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </Stagger>
    </div>
  );
}

export default OverrideConsole;
