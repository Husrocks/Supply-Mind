import { useState, useActionState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import {
  CheckCircle2, Clock, AlertTriangle, XCircle, PlayCircle, BarChart3, Loader2, Plus
} from 'lucide-react';
import toast from 'react-hot-toast';
import clsx from 'clsx';
import {
  useOnboarding,
  useOnboardSupplier,
  useStartProbationMutation,
  useEvaluateOnboardingMutation,
} from '../hooks/useDashboardQueries';
import { GlassCard } from '../components/ui/GlassCard';
import { ViewSkeleton } from '../components/ui/ViewSkeleton';
import { Stagger, StaggerItem } from '../components/motion/Stagger';
import { EmptyState } from '../components/EmptyState';
import { queryKeys } from '../api/queries';
import type { SupplierOnboarding as OnboardingRecord, RiskAccent } from '../types';

// ── Status helpers ────────────────────────────────────────────────────────────

const STATUS_CONF: Record<string, { label: string; accent: RiskAccent; Icon: React.ElementType }> = {
  PENDING_REVIEW: { label: 'Pending Review', accent: 'amber', Icon: Clock },
  IN_PROBATION:   { label: 'In Probation',   accent: 'cyan',  Icon: BarChart3 },
  APPROVED:       { label: 'Approved',        accent: 'emerald', Icon: CheckCircle2 },
  REJECTED:       { label: 'Rejected',        accent: 'rose',  Icon: XCircle },
};

// ── Metric bar ────────────────────────────────────────────────────────────────

function MetricBar({
  label,
  value,
  threshold,
  invertBad = false,
}: {
  label: string;
  value: number;
  threshold: number;
  invertBad?: boolean;
}) {
  const pct = Math.min(100, Math.max(0, value * 100));
  const bad = invertBad ? value < threshold : value > threshold;
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-muted">{label}</span>
        <span className={clsx('font-mono tabular-nums font-medium', bad ? 'text-risk-high' : 'text-risk-low')}>
          {pct.toFixed(1)}%
          <span className="text-muted font-normal ml-1">(threshold {(threshold * 100).toFixed(0)}%)</span>
        </span>
      </div>
      <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div
          className={clsx('h-full rounded-full transition-all', bad ? 'bg-risk-high' : 'bg-risk-low')}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

// ── Progress ring ─────────────────────────────────────────────────────────────

function ProgressRing({ pct, daysLeft, status }: { pct: number; daysLeft: number | null; status: string }) {
  const r = 30;
  const circ = 2 * Math.PI * r;
  const offset = circ - (pct / 100) * circ;

  const strokeColor =
    status === 'APPROVED' ? '#10b981' :
    status === 'REJECTED' ? '#f43f5e' :
    status === 'IN_PROBATION' ? '#22d3ee' :
    '#f59e0b';

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width={76} height={76}>
        <circle cx={38} cy={38} r={r} fill="none" stroke="rgba(148,163,184,0.15)" strokeWidth={7} />
        <circle
          cx={38} cy={38} r={r} fill="none"
          stroke={strokeColor}
          strokeWidth={7}
          strokeDasharray={circ}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform="rotate(-90 38 38)"
          style={{ transition: 'stroke-dashoffset 0.6s ease' }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-xs font-mono font-bold text-ink">{pct.toFixed(0)}%</span>
        <span className="text-[9px] text-muted">{daysLeft != null ? `${Math.max(0, daysLeft)}d left` : 'Not started'}</span>
      </div>
    </div>
  );
}

function OnboardingCard({ record, onAction }: { record: OnboardingRecord; onAction: () => void }) {
  const [loading, setLoading] = useState(false);
  const conf = STATUS_CONF[record.status] ?? STATUS_CONF.PENDING_REVIEW;
  const Icon = conf.Icon;

  const startMutation = useStartProbationMutation();
  const evaluateMutation = useEvaluateOnboardingMutation();

  const handleStartProbation = async () => {
    setLoading(true);
    startMutation.mutate(record.id, {
      onSuccess: () => {
        toast.success(`90-day probation started for ${record.supplier_name}`);
        onAction();
        setLoading(false);
      },
      onError: (err: any) => {
        toast.error(err.response?.data?.detail ?? 'Failed to start probation');
        setLoading(false);
      }
    });
  };

  const handleEvaluate = async () => {
    setLoading(true);
    evaluateMutation.mutate(record.id, {
      onSuccess: (res: any) => {
        if (res.status !== record.status) {
          toast.success(`Status updated: ${record.status} → ${res.status}`);
        } else {
          toast(`No threshold triggered — status unchanged (${record.status})`);
        }
        onAction();
        setLoading(false);
      },
      onError: (err: any) => {
        toast.error(err.response?.data?.detail ?? 'Evaluation failed');
        setLoading(false);
      }
    });
  };

  return (
    <GlassCard accent={conf.accent}>
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-4">
        <div>
          <p className="text-[11px] text-muted uppercase tracking-wider">{record.supplier_id}</p>
          <h3 className="text-base font-semibold text-ink">{record.supplier_name}</h3>
        </div>
        <span className={clsx(
          'inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border font-medium shrink-0',
          record.status === 'APPROVED' && 'bg-emerald-900/20 text-risk-low border-emerald-700/30',
          record.status === 'REJECTED' && 'bg-rose-900/20 text-risk-high border-rose-700/30',
          record.status === 'IN_PROBATION' && 'bg-cyan-900/20 text-accent-cyan border-cyan-700/30',
          record.status === 'PENDING_REVIEW' && 'bg-amber-900/20 text-risk-medium border-amber-700/30',
        )}>
          <Icon size={11} />
          {conf.label}
        </span>
      </div>

      {/* Probation ring + auto-threshold alerts */}
      <div className="flex items-center gap-4 mb-4">
        <ProgressRing pct={record.probation_progress_pct} daysLeft={record.days_remaining} status={record.status} />
        <div className="flex-1 space-y-2">
          {record.auto_approve_threshold_met && (
            <div className="flex items-center gap-1.5 text-xs text-risk-low bg-emerald-900/20 border border-emerald-700/30 rounded-lg px-3 py-1.5">
              <CheckCircle2 size={12} /> Auto-approve thresholds met
            </div>
          )}
          {record.auto_reject_threshold_triggered && (
            <div className="flex items-center gap-1.5 text-xs text-risk-high bg-rose-900/20 border border-rose-700/30 rounded-lg px-3 py-1.5">
              <AlertTriangle size={12} /> Auto-reject threshold triggered
            </div>
          )}
          {!record.auto_approve_threshold_met && !record.auto_reject_threshold_triggered && record.status === 'IN_PROBATION' && (
            <p className="text-xs text-muted">Probation ongoing — thresholds not yet met</p>
          )}
        </div>
      </div>

      {/* Probation metrics */}
      {record.status !== 'PENDING_REVIEW' && record.probation_po_count > 0 && (
        <div className="space-y-3 mb-4">
          <MetricBar
            label="On-time delivery rate"
            value={record.probation_on_time_rate}
            threshold={0.85}
            invertBad={false}
          />
          <MetricBar
            label="PO rejection rate"
            value={record.probation_rejection_rate}
            threshold={0.03}
            invertBad
          />
          <p className="text-[10px] text-muted mt-1">Based on {record.probation_po_count} POs during probation</p>
        </div>
      )}
      {record.status === 'IN_PROBATION' && record.probation_po_count === 0 && (
        <p className="text-xs text-muted mb-4">No POs recorded yet during probation period.</p>
      )}

      {/* Meta */}
      <div className="grid grid-cols-2 gap-2 text-xs text-muted mb-4">
        <span>Applied: {new Date(record.application_date).toLocaleDateString()}</span>
        {record.probation_start_date && (
          <span>Probation start: {new Date(record.probation_start_date).toLocaleDateString()}</span>
        )}
        {record.geographic_risk_region && <span>Region: {record.geographic_risk_region}</span>}
        <span>Reference check: <span className={clsx('font-medium', record.reference_check_status === 'PASSED' ? 'text-risk-low' : record.reference_check_status === 'FAILED' ? 'text-risk-high' : 'text-risk-medium')}>{record.reference_check_status}</span></span>
      </div>

      {/* Actions */}
      <div className="flex gap-2 pt-3 border-t border-hairline">
        {record.status === 'PENDING_REVIEW' && (
          <button
            onClick={handleStartProbation}
            disabled={loading}
            className="btn-primary !h-8 !text-xs flex-1 flex items-center justify-center gap-1.5"
          >
            {loading ? <Loader2 size={12} className="animate-spin" /> : <PlayCircle size={12} />}
            Start 90-day probation
          </button>
        )}
        {record.status === 'IN_PROBATION' && (
          <button
            onClick={handleEvaluate}
            disabled={loading}
            className="btn-secondary !h-8 !text-xs flex-1 flex items-center justify-center gap-1.5"
          >
            {loading ? <Loader2 size={12} className="animate-spin" /> : <BarChart3 size={12} />}
            Evaluate thresholds
          </button>
        )}
      </div>
    </GlassCard>
  );
}

function NewSupplierForm({ onSuccess }: { onSuccess: () => void }) {
  const [open, setOpen] = useState(false);
  const onboardMutation = useOnboardSupplier();

  const [_, formAction, isPending] = useActionState(
    async (_prevState: any, formData: FormData) => {
      const supplier_id = formData.get('supplier_id') as string;
      const supplier_name = formData.get('supplier_name') as string;
      const geographic_risk_region = formData.get('geographic_risk_region') as string;

      if (!supplier_id || !supplier_name) {
        toast.error('Supplier ID and name are required');
        return { error: 'Required fields missing' };
      }

      try {
        await onboardMutation.mutateAsync({
          supplier_id,
          supplier_name,
          geographic_risk_region: geographic_risk_region || undefined,
        });
        toast.success(`Onboarding application created for ${supplier_name}`);
        setOpen(false);
        onSuccess();
        return { error: null, success: true };
      } catch (err: any) {
        const errorMsg = err.response?.data?.detail ?? 'Failed to submit application';
        toast.error(errorMsg);
        return { error: errorMsg };
      }
    },
    null
  );

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="btn-primary !h-9 !text-xs flex items-center gap-1.5"
      >
        <Plus size={14} /> Onboard New Supplier
      </button>
    );
  }

  return (
    <form action={formAction} className="p-5 glass-card flex flex-col gap-3">
      <h3 className="text-sm font-semibold text-ink">New Supplier Application</h3>
      
      <div>
        <label className="text-xs text-muted mb-1 block">Supplier ID *</label>
        <input
          name="supplier_id"
          className="w-full bg-slate-800/60 border border-slate-600/50 rounded-xl px-3 py-2 text-sm text-ink placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-shadow"
          placeholder="e.g. SUP-0099"
          required
        />
      </div>

      <div>
        <label className="text-xs text-muted mb-1 block">Supplier Name *</label>
        <input
          name="supplier_name"
          className="w-full bg-slate-800/60 border border-slate-600/50 rounded-xl px-3 py-2 text-sm text-ink placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-shadow"
          placeholder="e.g. Beijing Parts Co."
          required
        />
      </div>

      <div>
        <label className="text-xs text-muted mb-1 block">Risk Region</label>
        <input
          name="geographic_risk_region"
          className="w-full bg-slate-800/60 border border-slate-600/50 rounded-xl px-3 py-2 text-sm text-ink placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-shadow"
          placeholder="APAC / EMEA / AMER"
        />
      </div>

      <div className="flex gap-2 mt-1">
        <button type="submit" disabled={isPending} className="btn-primary !h-8 !text-xs flex-1 flex items-center justify-center gap-1.5">
          {isPending && <Loader2 size={12} className="animate-spin" />}
          Submit Application
        </button>
        <button type="button" onClick={() => setOpen(false)} className="btn-secondary !h-8 !text-xs flex-1">Cancel</button>
      </div>
    </form>
  );
}

// ── View ──────────────────────────────────────────────────────────────────────

const STATUS_FILTERS = ['ALL', 'PENDING_REVIEW', 'IN_PROBATION', 'APPROVED', 'REJECTED'] as const;

export function SupplierOnboarding() {
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const queryClient = useQueryClient();
  const { data: records = [], isLoading } = useOnboarding(statusFilter === 'ALL' ? undefined : statusFilter);

  const refresh = () => queryClient.invalidateQueries({ queryKey: queryKeys.onboarding });

  if (isLoading) {
    return <ViewSkeleton />;
  }

  return (
    <div className="h-full overflow-y-auto p-5 lg:p-6">
      <Stagger className="max-w-content mx-auto space-y-5">
        <StaggerItem>
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h1 className="text-xl font-semibold text-ink">Supplier Onboarding</h1>
              <p className="text-sm text-body mt-1">90-day probation pipeline · auto-approve/reject thresholds</p>
            </div>
            <NewSupplierForm onSuccess={refresh} />
          </div>
        </StaggerItem>

        {/* Summary chips */}
        <StaggerItem>
          <div className="flex flex-wrap gap-2">
            {STATUS_FILTERS.map((s) => {
              const count = s === 'ALL' ? records.length : records.filter((r: OnboardingRecord) => r.status === s).length;
              return (
                <button
                  key={s}
                  onClick={() => setStatusFilter(s)}
                  className={clsx(
                    'text-xs px-3 py-1.5 rounded-full border font-medium transition-colors',
                    statusFilter === s
                      ? 'bg-accent-indigo text-white border-accent-indigo'
                      : 'border-hairline text-muted hover:text-ink'
                  )}
                >
                  {s.replace('_', ' ')} ({count})
                </button>
              );
            })}
          </div>
        </StaggerItem>

        {records.length === 0 ? (
          <EmptyState
            icon={<BarChart3 size={28} />}
            title="No onboarding records"
            description={statusFilter === 'ALL' ? 'Use the button above to start onboarding a new supplier.' : `No suppliers with status: ${statusFilter}.`}
          />
        ) : (
          <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
            {records.map((r: OnboardingRecord) => (
              <StaggerItem key={r.id}>
                <OnboardingCard record={r} onAction={refresh} />
              </StaggerItem>
            ))}
          </div>
        )}
      </Stagger>
    </div>
  );
}

export default SupplierOnboarding;
