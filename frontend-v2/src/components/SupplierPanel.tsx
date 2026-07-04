import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Cell, Tooltip } from 'recharts';
import { Loader2, AlertCircle, CheckCircle, X, ArrowUpRight, ArrowDownRight, Truck, Percent, DollarSign } from 'lucide-react';
import toast from 'react-hot-toast';
import { triggerAgentAnalysis } from '../api/client';

interface ShapDriver {
  feature: string;
  impact: number;
  direction: 'increases_risk' | 'decreases_risk';
  value?: number;
}

interface SupplierDetail {
  supplier_id: string;
  supplier_name?: string;
  risk_score: number;
  risk_tier?: string;
  geopolitical_factor?: number;
  lead_time_variance?: number;
  quality_failure_rate?: number;
  concentration_ratio?: number;
  reasoning?: string;
  shap_drivers?: ShapDriver[];
  avg_lead_time_days?: number;
  on_time_delivery_pct?: number;
  po_acceptance_rate?: number;
  unit_cost_estimate?: number;
}

interface SupplierPanelProps {
  supplier: SupplierDetail | null;
  onClose: () => void;
  isOpen: boolean;
}

export function SupplierPanel({ supplier, onClose, isOpen }: SupplierPanelProps) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen && panelRef.current) {
      panelRef.current.focus();
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
        return;
      }

      if (e.key === 'Tab') {
        if (!panelRef.current) return;
        const focusableElements = panelRef.current.querySelectorAll(
          'a[href], area[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), button:not([disabled]), iframe, object, embed, [tabindex="0"], [contenteditable]'
        );
        if (focusableElements.length === 0) return;
        const firstElement = focusableElements[0] as HTMLElement;
        const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement;

        if (e.shiftKey) {
          if (document.activeElement === firstElement) {
            lastElement.focus();
            e.preventDefault();
          }
        } else {
          if (document.activeElement === lastElement) {
            firstElement.focus();
            e.preventDefault();
          }
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!supplier) return null;

  const getRiskDetails = (score: number) => {
    if (score < 0.4) return { color: 'text-semantic-up', label: 'Low Risk' };
    if (score <= 0.7) return { color: 'text-accent-yellow', label: 'Elevated Risk' };
    return { color: 'text-semantic-down', label: 'Critical Risk' };
  };

  const risk = getRiskDetails(supplier.risk_score);

  // Prefer real SHAP drivers from ML pipeline; fall back to structural risk factors
  const chartData = (supplier.shap_drivers && supplier.shap_drivers.length > 0)
    ? supplier.shap_drivers.map(d => ({
        name: d.feature.replace(/_/g, ' '),
        impact: Math.abs(d.impact),
        direction: d.direction,
      }))
    : [
        { name: 'Geopolitical Risk', impact: supplier.geopolitical_factor ?? 0, direction: 'increases_risk' as const },
        { name: 'Lead Time Variance', impact: supplier.lead_time_variance ?? 0, direction: 'increases_risk' as const },
        { name: 'Quality Failure', impact: supplier.quality_failure_rate ?? 0, direction: 'increases_risk' as const },
        { name: 'Concentration Ratio', impact: supplier.concentration_ratio ?? 0, direction: 'increases_risk' as const },
      ].filter((d): d is { name: string; impact: number; direction: 'increases_risk' } =>
        typeof d.impact === 'number' && !Number.isNaN(d.impact) && d.impact > 0
      );

  const isRealShap = !!(supplier.shap_drivers && supplier.shap_drivers.length > 0);

  const handleTriggerAgent = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await triggerAgentAnalysis(supplier.supplier_id);
      setResult(data);
      toast.success('Agent analysis triggered successfully');
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to dispatch agent analysis';
      setError(errorMsg);
      toast.error(`Analysis error: ${errorMsg}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/40 z-40 cursor-pointer"
          />

          <motion.div
            ref={panelRef}
            tabIndex={-1}
            role="dialog"
            aria-modal="true"
            aria-label={`${supplier.supplier_name || 'Supplier'} Details`}
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed right-0 top-0 bottom-0 w-full max-w-[420px] glass-card !rounded-none border-l border-hairline shadow-none p-6 sm:p-8 flex flex-col overflow-y-auto z-50 focus:outline-none"
          >
            <div className="flex justify-between items-start mb-8">
              <div>
                <span className="badge-pill text-[10px]">Supplier</span>
                <h3 className="text-lg font-semibold text-ink mt-2">
                  {supplier.supplier_name || `Supplier ${supplier.supplier_id}`}
                </h3>
                <span className="text-xs font-mono text-muted">{supplier.supplier_id}</span>
              </div>
              <button
                onClick={onClose}
                className="p-2 hover:bg-surface-strong rounded-full text-muted hover:text-ink transition-colors"
              >
                <X size={18} />
              </button>
            </div>

            <div className="mb-6 p-5 rounded-xl border border-hairline bg-surface-soft flex items-center justify-between">
              <div>
                <span className="text-xs text-muted font-medium">Risk Score</span>
                <div className="font-mono text-3xl text-ink mt-1">
                  {(supplier.risk_score * 100).toFixed(1)}%
                </div>
              </div>
              <span className={`text-sm font-semibold ${risk.color}`}>
                {risk.label}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3 mb-6">
              {[
                { icon: Truck, label: 'Avg Lead Time', value: supplier.avg_lead_time_days != null ? `${supplier.avg_lead_time_days.toFixed(1)} days` : '—' },
                { icon: Percent, label: 'On-Time Rate', value: supplier.on_time_delivery_pct != null ? `${(supplier.on_time_delivery_pct * 100).toFixed(0)}%` : '—' },
                { icon: DollarSign, label: 'Unit Cost', value: supplier.unit_cost_estimate != null ? `$${supplier.unit_cost_estimate.toFixed(2)}` : '—' },
                { icon: Percent, label: 'Quality Failure', value: supplier.quality_failure_rate != null ? `${(supplier.quality_failure_rate * 100).toFixed(1)}%` : '—' },
              ].map(({ icon: Icon, label, value }) => (
                <div key={label} className="p-3 bg-canvas rounded-xl border border-hairline flex items-center gap-3">
                  <Icon size={16} className="text-muted shrink-0" />
                  <div>
                    <div className="text-[10px] text-muted font-medium uppercase">{label}</div>
                    <div className="text-sm font-mono font-medium text-ink">{value}</div>
                  </div>
                </div>
              ))}
            </div>

            <div className="mb-6">
              <h4 className="text-xs font-semibold text-muted uppercase tracking-wider mb-3 flex items-center gap-2">
                SHAP Impact
                {isRealShap && (
                  <span className="text-[10px] bg-emerald-900/30 text-risk-low border border-emerald-700/30 rounded-full px-2 py-0.5 font-normal normal-case">
                    Real LightGBM
                  </span>
                )}
                {!isRealShap && (
                  <span className="text-[10px] bg-slate-800/60 text-muted border border-slate-700/30 rounded-full px-2 py-0.5 font-normal normal-case">
                    Structural fallback
                  </span>
                )}
              </h4>
              <div className="h-44 border border-hairline rounded-xl p-4 bg-surface-soft">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={chartData}
                    layout="vertical"
                    margin={{ top: 5, right: 5, left: 10, bottom: 5 }}
                  >
                    <XAxis type="number" hide domain={[0, 1]} />
                    <YAxis
                      dataKey="name"
                      type="category"
                      axisLine={false}
                      tickLine={false}
                      tick={{ fill: '#7c828a', fontSize: 10 }}
                      width={100}
                    />
                    <Tooltip
                      contentStyle={{ background: '#ffffff', border: '1px solid #dee1e6', borderRadius: '12px' }}
                      labelStyle={{ color: '#0a0b0d', fontSize: 11 }}
                      itemStyle={{ color: '#5b616e', fontSize: 11 }}
                      formatter={(val: any) => [`${(Number(val) * 100).toFixed(1)}%`, 'Weight']}
                    />
                    <Bar dataKey="impact" radius={[0, 4, 4, 0]} barSize={10}>
                      {chartData.map((entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={entry.direction === 'increases_risk' ? '#cf202f' : '#05b169'}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="space-y-2 mb-6">
              <h4 className="text-xs font-semibold text-muted uppercase tracking-wider mb-2">
                Risk Attribution
              </h4>
              {chartData.map((d, index) => {
                const increases = d.direction === 'increases_risk';
                const percent = Math.min(100, Math.max(0, d.impact * 100));
                return (
                  <div key={index} className="p-3 border border-hairline rounded-xl flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex justify-between items-center text-xs text-ink font-medium mb-1.5">
                        <span>{d.name}</span>
                        <span className={`font-mono ${increases ? 'text-semantic-down' : 'text-semantic-up'}`}>
                          {(d.impact * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="w-full h-1.5 bg-surface-strong rounded-pill overflow-hidden">
                        <div
                          className={`h-full rounded-pill ${increases ? 'bg-semantic-down' : 'bg-semantic-up'}`}
                          style={{ width: `${percent}%` }}
                        />
                      </div>
                    </div>
                    <div className="ml-3 shrink-0">
                      {increases ? (
                        <ArrowUpRight size={14} className="text-semantic-down" />
                      ) : (
                        <ArrowDownRight size={14} className="text-semantic-up" />
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {supplier.reasoning && (
              <div className="mb-6 p-4 rounded-xl bg-surface-soft border border-hairline text-sm text-body leading-relaxed">
                {supplier.reasoning}
              </div>
            )}

            <div className="mt-auto pt-6 border-t border-hairline">
              <button
                onClick={handleTriggerAgent}
                disabled={loading}
                className="btn-primary w-full"
              >
                {loading ? (
                  <>
                    <Loader2 className="animate-spin" size={18} />
                    <span>Analyzing...</span>
                  </>
                ) : (
                  <span>Trigger Agent Analysis</span>
                )}
              </button>

              {error && (
                <div className="mt-4 p-3 border border-hairline rounded-xl text-semantic-down text-xs flex items-start gap-2 bg-surface-soft">
                  <AlertCircle size={16} className="mt-0.5 shrink-0" />
                  <p>{error}</p>
                </div>
              )}

              {result && (
                <div className="mt-4 p-4 border border-hairline rounded-xl flex items-start gap-2 bg-surface-soft">
                  <CheckCircle size={16} className="text-semantic-up mt-0.5 shrink-0" />
                  <div>
                    <h4 className="text-semantic-up font-semibold text-xs">Agent cycle completed</h4>
                    <p className="text-[11px] text-body mt-1">
                      Generated <span className="font-semibold text-ink">{result.actions_generated}</span> action(s). Thread: <span className="font-mono text-ink">{result.thread_id}</span>
                    </p>
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
