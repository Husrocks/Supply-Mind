import { useMemo, useState } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, Cell, ReferenceLine,
} from 'recharts';
import { TrendingUp, ShieldCheck, AlertTriangle, Loader2, RefreshCw } from 'lucide-react';
import toast from 'react-hot-toast';
import { useModelPerformance, useRetrainStatus } from '../hooks/useDashboardQueries';
import { useInView } from '../hooks/useInView';
import { usePrefersReducedMotion } from '../hooks/usePrefersReducedMotion';
import { GlassCard } from '../components/ui/GlassCard';
import { ViewSkeleton } from '../components/ui/ViewSkeleton';
import { RadialGauge } from '../components/ui/RadialGauge';
import { Stagger, StaggerItem } from '../components/motion/Stagger';
import { apiClient } from '../api/client';
import { useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../api/queries';
import { RetrainLogsModal } from '../components/modals/RetrainLogsModal';
import clsx from 'clsx';

const MODEL_NAMES = ['TFT', 'LightGBM', 'LSTM_AE'] as const;
type ModelName = typeof MODEL_NAMES[number];

const MODEL_LABELS: Record<ModelName, string> = {
  TFT: 'TFT Demand Forecaster',
  LightGBM: 'LightGBM Risk Classifier',
  LSTM_AE: 'LSTM-AE Anomaly Detector',
};

export function ModelObservatory() {
  const { data, isLoading, isError } = useModelPerformance();
  const { ref, inView } = useInView();
  const reduced = usePrefersReducedMotion();
  const queryClient = useQueryClient();
  const [retraining, setRetraining] = useState<ModelName | null>(null);
  const { data: retrainHistory, isLoading: isLoadingHistory } = useRetrainStatus();
  const [logJob, setLogJob] = useState<{ id: number, model: string } | null>(null);

  const modelConfidence = useMemo(() => {
    if (!data) return 0;
    const lgbm = data.lightgbm.pr_auc * 100;
    const tft = Math.max(0, (1 - data.tft.val_wrmsse) * 100);
    return (lgbm + tft) / 2;
  }, [data]);

  const handleRetrain = async (modelName: ModelName) => {
    setRetraining(modelName);
    try {
      const response = await apiClient.post('/models/retrain', { model_name: modelName });
      toast.success(`${MODEL_LABELS[modelName]} retrain started — ${response.data.message ?? 'Background job spawned.'}`);
      // Invalidate model performance cache so metrics refresh after retraining
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: queryKeys.modelPerformance });
      }, 3000);
    } catch (err: any) {
      const detail = err.response?.data?.detail ?? err.message ?? 'Retrain request failed';
      toast.error(`Retrain failed: ${detail}`);
    } finally {
      setRetraining(null);
    }
  };

  if (isLoading || !data) {
    return <ViewSkeleton />;
  }

  if (isError) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-risk-high text-sm">Failed to load model performance metrics.</p>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-5 lg:p-6">
      <Stagger className="max-w-content mx-auto space-y-5">
        <StaggerItem>
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-xl font-semibold text-ink">Model Observatory</h1>
              <p className="text-sm text-body mt-1">/models/performance</p>
            </div>
            {/* Retrain controls */}
            <div className="flex flex-col gap-2 items-end">
              <p className="text-[11px] text-muted uppercase tracking-wider">Retrain Model</p>
              <div className="flex flex-wrap gap-2 justify-end">
                {MODEL_NAMES.map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => handleRetrain(m)}
                    disabled={retraining !== null}
                    className="btn-secondary !h-8 !text-xs !px-3 flex items-center gap-1.5"
                    title={`Retrain ${MODEL_LABELS[m]}`}
                  >
                    {retraining === m ? (
                      <Loader2 size={12} className="animate-spin" />
                    ) : (
                      <RefreshCw size={12} />
                    )}
                    {m}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </StaggerItem>

        <StaggerItem>
          <div className="flex flex-col sm:flex-row items-center justify-around gap-8 glass-card">
            <RadialGauge value={modelConfidence} label="Avg confidence" accent="indigo" size={120} />
            <RadialGauge value={data.lightgbm.pr_auc * 100} label="LGBM PR-AUC" accent="emerald" size={120} />
            <RadialGauge value={Math.min(100, data.lstm_ae.current_threshold * 1000)} label="LSTM threshold×1000" accent="rose" size={120} />
          </div>
        </StaggerItem>

        <StaggerItem>
          <div ref={ref} className="grid lg:grid-cols-3 gap-4">
          <GlassCard accent="indigo">
            <div className="flex justify-between mb-3">
              <h2 className="text-sm font-semibold flex items-center gap-2"><TrendingUp size={14} /> TFT</h2>
              <span className="font-mono tabular-nums text-ink">{data.tft.val_wrmsse.toFixed(4)}</span>
            </div>
            <p className="text-[10px] text-muted mb-2">WRMSSE (lower = better)</p>
            {inView && (
              <div className="h-[200px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={data.tft.history}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.12)" />
                    <XAxis dataKey="date" tick={{ fontSize: 9, fill: '#94a3b8' }} />
                    <YAxis tick={{ fontSize: 9, fill: '#94a3b8' }} domain={['dataMin', 'dataMax']} />
                    <Tooltip contentStyle={{ background: '#0f172a', borderRadius: 12 }} />
                    <Line type="monotone" dataKey="wrmsse" stroke="#06b6d4" strokeWidth={2} dot={{ r: 3 }} isAnimationActive={!reduced} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </GlassCard>

          <GlassCard accent="emerald">
            <div className="flex justify-between mb-3">
              <h2 className="text-sm font-semibold flex items-center gap-2"><ShieldCheck size={14} /> LightGBM</h2>
              <span className="font-mono tabular-nums text-ink">{data.lightgbm.pr_auc.toFixed(3)}</span>
            </div>
            <p className="text-[10px] text-muted mb-2">PR-AUC (calibration curve)</p>
            {inView && (
              <div className="h-[200px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={data.lightgbm.calibration_curve}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.12)" />
                    <XAxis dataKey="predicted" type="number" domain={[0, 1]} tick={{ fontSize: 9, fill: '#94a3b8' }} />
                    <YAxis type="number" domain={[0, 1]} tick={{ fontSize: 9, fill: '#94a3b8' }} />
                    <Tooltip contentStyle={{ background: '#0f172a', borderRadius: 12 }} />
                    <Line type="linear" dataKey="predicted" stroke="#475569" strokeDasharray="3 3" dot={false} />
                    <Line type="monotone" dataKey="actual" stroke="#10b981" strokeWidth={2} dot={{ r: 3 }} isAnimationActive={!reduced} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </GlassCard>

          <GlassCard accent="rose">
            <div className="flex justify-between mb-3">
              <h2 className="text-sm font-semibold flex items-center gap-2"><AlertTriangle size={14} /> LSTM-AE</h2>
              <span className="font-mono tabular-nums text-ink">{data.lstm_ae.current_threshold.toFixed(3)}</span>
            </div>
            <p className="text-[10px] text-muted mb-2">Reconstruction error threshold</p>
            {inView && (
              <div className="h-[200px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data.lstm_ae.recent_errors}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.12)" vertical={false} />
                    <XAxis dataKey="supplier_id" tick={{ fontSize: 8, fill: '#94a3b8' }} angle={-30} textAnchor="end" height={48} />
                    <YAxis tick={{ fontSize: 9, fill: '#94a3b8' }} />
                    <ReferenceLine y={data.lstm_ae.current_threshold} stroke="#f43f5e" strokeDasharray="4 4" />
                    <Bar dataKey="error" radius={[4, 4, 0, 0]} isAnimationActive={!reduced}>
                      {data.lstm_ae.recent_errors.map((e: { supplier_id: string; error: number }, i: number) => (
                        <Cell key={i} fill={e.error > data.lstm_ae.current_threshold ? '#f43f5e' : '#64748b'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </GlassCard>
          </div>
        </StaggerItem>

        <StaggerItem>
          <div className="mt-6">
            <h2 className="text-sm font-semibold text-ink uppercase tracking-wider mb-4 flex items-center gap-2">
              <RefreshCw size={16} className="text-muted" /> Retraining History
            </h2>
            <GlassCard className="!p-0 overflow-hidden max-h-[300px] overflow-y-auto">
              {isLoadingHistory ? (
                <div className="p-8 text-center text-xs text-muted flex items-center justify-center gap-2">
                  <Loader2 size={14} className="animate-spin" /> Loading history...
                </div>
              ) : retrainHistory?.jobs && retrainHistory.jobs.length > 0 ? (
                <table className="w-full text-xs text-left">
                  <thead>
                    <tr className="border-b border-hairline text-muted bg-slate-900/50 sticky top-0 backdrop-blur-md">
                      <th className="px-5 py-3 font-semibold">Job ID</th>
                      <th className="px-4 py-3 font-semibold">Model</th>
                      <th className="px-4 py-3 font-semibold">Status</th>
                      <th className="px-4 py-3 font-semibold">Started</th>
                      <th className="px-4 py-3 font-semibold">Completed</th>
                      <th className="px-5 py-3 font-semibold text-right">Logs</th>
                    </tr>
                  </thead>
                  <tbody>
                    {retrainHistory.jobs.map((job: any) => (
                      <tr key={job.job_id} className="border-b border-hairline hover:bg-slate-800/20">
                        <td className="px-5 py-3 font-mono text-muted">#{job.job_id}</td>
                        <td className="px-4 py-3 font-medium text-ink">{job.model_name}</td>
                        <td className="px-4 py-3">
                          <span className={clsx(
                            'font-medium uppercase text-[9px] px-2 py-0.5 rounded-full border',
                            job.status === 'completed' ? 'text-risk-low bg-emerald-900/20 border-emerald-700/30' :
                            job.status === 'failed' ? 'text-risk-high bg-rose-900/20 border-rose-700/30' : 
                            'text-risk-medium bg-amber-900/20 border-amber-700/30 animate-pulse'
                          )}>{job.status}</span>
                        </td>
                        <td className="px-4 py-3 text-muted">
                          {job.created_at ? new Date(job.created_at).toLocaleString() : '—'}
                        </td>
                        <td className="px-4 py-3 text-muted">
                          {job.completed_at ? new Date(job.completed_at).toLocaleString() : '—'}
                        </td>
                        <td className="px-5 py-3 text-right">
                          <button 
                            onClick={() => setLogJob({ id: job.job_id, model: job.model_name })}
                            disabled={!job.log_file}
                            className="btn-secondary !h-7 !text-[10px] !px-2.5 disabled:opacity-30 disabled:cursor-not-allowed"
                          >
                            View Logs
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="p-8 text-center text-xs text-muted italic">
                  No retraining history found.
                </div>
              )}
            </GlassCard>
          </div>
        </StaggerItem>
      </Stagger>

      <RetrainLogsModal 
        jobId={logJob?.id ?? null} 
        modelName={logJob?.model ?? ''} 
        onClose={() => setLogJob(null)} 
      />
    </div>
  );
}

export default ModelObservatory;
