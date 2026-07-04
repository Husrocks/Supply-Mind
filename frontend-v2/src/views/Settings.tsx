import { useState, useEffect, useActionState } from 'react';
import { useSettings, useUpdateSettingsMutation } from '../hooks/useDashboardQueries';
import { Save, Loader2, ShieldCheck, Mail, DollarSign, Hourglass } from 'lucide-react';
import toast from 'react-hot-toast';
import { GlassCard } from '../components/ui/GlassCard';
import { ViewSkeleton } from '../components/ui/ViewSkeleton';
import { Stagger, StaggerItem } from '../components/motion/Stagger';

export function Settings() {
  const { data: initialSettings, isLoading, refetch } = useSettings();
  const [form, setForm] = useState({
    risk_high_threshold: 0.75,
    risk_critical_threshold: 0.85,
    stockout_warning_days: 14,
    autonomous_budget_usd: 85000,
    anomaly_reconstruction_percentile: 95,
    manager_email: '',
  });

  const updateSettingsMutation = useUpdateSettingsMutation();

  const [_, formAction, isPending] = useActionState(
    async () => {
      try {
        await updateSettingsMutation.mutateAsync(form);
        toast.success('Configuration settings updated successfully');
        refetch();
        return { error: null, success: true };
      } catch (err: any) {
        const detail = err.response?.data?.detail || err.message || 'Failed to save settings';
        toast.error(`Update failed: ${detail}`);
        return { error: detail };
      }
    },
    null
  );

  useEffect(() => {
    if (initialSettings) {
      setForm({
        risk_high_threshold: initialSettings.risk_high_threshold,
        risk_critical_threshold: initialSettings.risk_critical_threshold,
        stockout_warning_days: initialSettings.stockout_warning_days,
        autonomous_budget_usd: initialSettings.autonomous_budget_usd,
        anomaly_reconstruction_percentile: initialSettings.anomaly_reconstruction_percentile,
        manager_email: initialSettings.manager_email,
      });
    }
  }, [initialSettings]);

  if (isLoading) {
    return <ViewSkeleton />;
  }

  return (
    <div className="h-full overflow-y-auto p-5 lg:p-6">
      <Stagger className="max-w-xl mx-auto space-y-6">
        <StaggerItem>
          <h1 className="text-xl font-semibold text-ink">System Configuration</h1>
          <p className="text-sm text-body mt-1">Manage risk rules, budget levels, and alert thresholds.</p>
        </StaggerItem>

        <StaggerItem>
          <form action={formAction} className="space-y-4">
            <GlassCard accent="indigo" className="space-y-5">
              <h2 className="text-sm font-semibold text-ink uppercase tracking-wider mb-4 border-b border-hairline pb-2 flex items-center gap-2">
                <ShieldCheck size={16} className="text-accent-indigo" /> Risk Scorer Thresholds
              </h2>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                <div>
                  <div className="flex justify-between items-center mb-1.5">
                    <label className="text-xs font-semibold text-body">
                      Elevated Risk Level
                    </label>
                    <span className="text-xs font-mono font-bold text-primary">{Math.round(form.risk_high_threshold * 100)}%</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.01"
                    className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-primary focus:outline-none focus:ring-2 focus:ring-primary/40"
                    value={form.risk_high_threshold}
                    onChange={(e) => setForm({ ...form, risk_high_threshold: parseFloat(e.target.value) })}
                    required
                  />
                  <p className="text-[10px] text-muted mt-1.5">Probability boundary for elevated warning (0.0 to 1.0)</p>
                </div>
                
                <div>
                  <div className="flex justify-between items-center mb-1.5">
                    <label className="text-xs font-semibold text-body">
                      Critical Risk Level
                    </label>
                    <span className="text-xs font-mono font-bold text-primary">{Math.round(form.risk_critical_threshold * 100)}%</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.01"
                    className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-primary focus:outline-none focus:ring-2 focus:ring-primary/40"
                    value={form.risk_critical_threshold}
                    onChange={(e) => setForm({ ...form, risk_critical_threshold: parseFloat(e.target.value) })}
                    required
                  />
                  <p className="text-[10px] text-muted mt-1.5">Probability boundary for critical action (0.0 to 1.0)</p>
                </div>
              </div>
            </GlassCard>

            <GlassCard accent="cyan" className="space-y-5">
              <h2 className="text-sm font-semibold text-ink uppercase tracking-wider mb-4 border-b border-hairline pb-2 flex items-center gap-2">
                <Hourglass size={16} className="text-accent-cyan" /> Operations & Inventory Rules
              </h2>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                <div>
                  <label className="text-xs font-medium text-body block mb-1.5 flex items-center gap-1.5">
                    Stockout Alert Warning Period
                  </label>
                  <input
                    type="number"
                    min="1"
                    className="w-full h-10 px-3 bg-slate-900/60 border border-hairline rounded-xl text-ink font-mono text-sm outline-none focus:outline-none focus:ring-2 focus:ring-cyan/50 focus:border-cyan transition-shadow"
                    value={form.stockout_warning_days}
                    onChange={(e) => setForm({ ...form, stockout_warning_days: parseInt(e.target.value) })}
                    required
                  />
                  <p className="text-[10px] text-muted mt-1">Days remaining before raising a warning flag</p>
                </div>

                <div>
                  <div className="flex justify-between items-center mb-1.5">
                    <label className="text-xs font-semibold text-body">
                      LSTM Anomaly Percentile
                    </label>
                    <span className="text-xs font-mono font-bold text-cyan">{form.anomaly_reconstruction_percentile}th</span>
                  </div>
                  <input
                    type="range"
                    min="1"
                    max="100"
                    step="1"
                    className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan focus:outline-none focus:ring-2 focus:ring-cyan/40"
                    value={form.anomaly_reconstruction_percentile}
                    onChange={(e) => setForm({ ...form, anomaly_reconstruction_percentile: parseInt(e.target.value) })}
                    required
                  />
                  <p className="text-[10px] text-muted mt-1.5">Percentile for LSTM-AE reconstruction threshold (1 to 100)</p>
                </div>
              </div>
            </GlassCard>

            <GlassCard accent="rose" className="space-y-5">
              <h2 className="text-sm font-semibold text-ink uppercase tracking-wider mb-4 border-b border-hairline pb-2 flex items-center gap-2">
                <DollarSign size={16} className="text-risk-high" /> Budget & Notification Limits
              </h2>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-medium text-body block mb-1.5 flex items-center gap-1.5">
                    Autonomous Budget Limit ($)
                  </label>
                  <input
                    type="number"
                    min="0"
                    className="w-full h-10 px-3 bg-slate-900/60 border border-hairline rounded-xl text-ink font-mono text-sm outline-none focus:outline-none focus:ring-2 focus:ring-rose/50 focus:border-rose transition-shadow"
                    value={form.autonomous_budget_usd}
                    onChange={(e) => setForm({ ...form, autonomous_budget_usd: parseFloat(e.target.value) })}
                    required
                  />
                  <p className="text-[10px] text-muted mt-1">Maximum cost before requiring manual intervention</p>
                </div>

                <div>
                  <label className="text-xs font-medium text-body block mb-1.5 flex items-center gap-1.5">
                    <Mail size={12} /> Escalation Email
                  </label>
                  <input
                    type="email"
                    className="w-full h-10 px-3 bg-slate-900/60 border border-hairline rounded-xl text-ink text-sm outline-none focus:outline-none focus:ring-2 focus:ring-rose/50 focus:border-rose transition-shadow"
                    value={form.manager_email}
                    onChange={(e) => setForm({ ...form, manager_email: e.target.value })}
                    required
                  />
                  <p className="text-[10px] text-muted mt-1">Email address to receive policy recommendations</p>
                </div>
              </div>
            </GlassCard>

            <div className="flex justify-end gap-3 pt-2">
              <button
                type="submit"
                disabled={isPending}
                className="btn-primary !h-10 px-6 flex items-center gap-2"
              >
                {isPending ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
                Save Changes
              </button>
            </div>
          </form>
        </StaggerItem>
      </Stagger>
    </div>
  );
}

export default Settings;
