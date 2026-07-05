import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useSupplierDetail } from '../hooks/useDashboardQueries';
import { apiClient } from '../api/client';
import { 
  ArrowLeft, Loader2, AlertCircle, CheckCircle2, PlayCircle, BarChart3, 
  MapPin, Landmark, TrendingUp, ShieldAlert 
} from 'lucide-react';
import { 
  ResponsiveContainer, BarChart, Bar, Cell, XAxis, YAxis, Tooltip as RechartsTooltip, 
  LineChart, Line, CartesianGrid 
} from 'recharts';
import toast from 'react-hot-toast';
import clsx from 'clsx';
import { GlassCard } from '../components/ui/GlassCard';
import { ViewSkeleton } from '../components/ui/ViewSkeleton';
import { Stagger, StaggerItem } from '../components/motion/Stagger';
import { riskScoreColor } from '../utils/risk';
import { usePrefersReducedMotion } from '../hooks/usePrefersReducedMotion';

export function SupplierDetail() {
  const { supplier_id } = useParams<{ supplier_id: string }>();
  const navigate = useNavigate();
  const reduced = usePrefersReducedMotion();
  const { data, isLoading, isError, refetch } = useSupplierDetail(supplier_id ?? '');
  const [triggering, setTriggering] = useState(false);

  if (isLoading) {
    return <ViewSkeleton />;
  }

  if (isError || !data) {
    return (
      <div className="p-8 flex flex-col items-center gap-4 glass-card max-w-lg mx-auto mt-12">
        <AlertCircle className="text-risk-high" size={32} />
        <p className="text-sm text-body text-center">Unable to load details for supplier "{supplier_id}". Ensure they exist in the current network.</p>
        <button onClick={() => navigate('/')} className="btn-secondary !h-9 text-xs flex items-center gap-1.5">
          <ArrowLeft size={12} /> Back to Command Center
        </button>
      </div>
    );
  }

  const handleTriggerAnalysis = async () => {
    setTriggering(true);
    try {
      const response = await apiClient.post('/agent/trigger', {
        primary_supplier_id: supplier_id,
        trigger_type: 'MANUAL',
        sku_id: 'FOODS_1_001_CA_1_evaluation'
      });
      toast.success(`Agent analysis triggered! Created ${response.data.actions_generated} actions.`);
      refetch();
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to trigger agent';
      toast.error(`Analysis error: ${errorMsg}`);
    } finally {
      setTriggering(false);
    }
  };

  // Process risk trend chart data
  const trendData = (data.risk_trend ?? []).map((score: number, idx: number) => ({
    cycle: `C-${idx + 1}`,
    score: score * 100
  }));

  // Process SHAP drivers chart data
  const shapData = (data.shap_drivers ?? []).map((d: any) => ({
    name: d.feature.replace(/_/g, ' '),
    impact: Math.abs(d.impact) * 100,
    direction: d.direction
  }));

  const otd = data.on_time_delivery_pct;
  const otdStr = otd !== null && otd !== undefined ? `${(otd * 100).toFixed(0)}%` : '—';
  
  const poAcc = data.po_acceptance_rate;
  const poStr = poAcc !== null && poAcc !== undefined ? `${(poAcc * 100).toFixed(0)}%` : '—';

  return (
    <div className="h-full overflow-y-auto p-5 lg:p-6">
      <Stagger className="max-w-[1400px] mx-auto space-y-6">
        
        {/* Header Block */}
        <StaggerItem className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-hairline">
          <div className="flex items-center gap-3">
            <button 
              onClick={() => navigate('/')} 
              className="p-2 hover:bg-slate-800/80 rounded-full text-muted hover:text-ink transition-colors focus:ring-1 focus:ring-accent-indigo focus:outline-none"
              title="Back"
            >
              <ArrowLeft size={18} />
            </button>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-semibold text-ink">{data.supplier_name}</h1>
                <span className="text-xs font-mono bg-slate-800/80 px-2 py-0.5 rounded border border-hairline text-muted">{data.supplier_id}</span>
              </div>
              <div className="flex items-center gap-3 mt-1.5 text-xs text-muted">
                {data.country_code && (
                  <span className="flex items-center gap-1">
                    <MapPin size={12} className="text-accent-cyan" /> {data.country_code} ({data.geographic_risk_region ?? 'Global'})
                  </span>
                )}
                <span className="flex items-center gap-1 capitalize">
                  <Landmark size={12} className="text-accent-indigo" /> Tier: {data.risk_tier}
                </span>
              </div>
            </div>
          </div>
          
          <button
            onClick={handleTriggerAnalysis}
            disabled={triggering}
            className="btn-primary !h-10 px-5 flex items-center gap-2"
          >
            {triggering ? <Loader2 size={14} className="animate-spin" /> : <PlayCircle size={14} />}
            Trigger Agent Analysis
          </button>
        </StaggerItem>

        {/* Risk Metrics Summary Grid */}
        <StaggerItem className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <GlassCard accent={data.risk_score >= 0.75 ? 'rose' : data.risk_score >= 0.4 ? 'amber' : 'emerald'} className="flex justify-between items-center py-5">
            <div>
              <p className="text-[10px] text-muted uppercase tracking-wider">Disruption Risk</p>
              <h3 className="text-3xl font-mono tabular-nums font-semibold mt-1" style={{ color: riskScoreColor(data.risk_score) }}>
                {(data.risk_score * 100).toFixed(1)}%
              </h3>
            </div>
            <span className={clsx(
              'text-xs font-semibold px-2.5 py-1 rounded-full border',
              data.risk_score >= 0.75 ? 'bg-rose-900/20 text-risk-high border-rose-700/30' :
              data.risk_score >= 0.4 ? 'bg-amber-900/20 text-risk-medium border-amber-700/30' :
              'bg-emerald-900/20 text-risk-low border-emerald-700/30'
            )}>{data.risk_tier.toUpperCase()}</span>
          </GlassCard>

          <GlassCard accent="cyan" className="py-5">
            <p className="text-[10px] text-muted uppercase tracking-wider">On-Time Delivery Rate</p>
            <h3 className="text-3xl font-mono tabular-nums font-semibold text-ink mt-1">{otdStr}</h3>
          </GlassCard>

          <GlassCard accent="indigo" className="py-5">
            <p className="text-[10px] text-muted uppercase tracking-wider">Avg Lead Time</p>
            <h3 className="text-3xl font-mono tabular-nums font-semibold text-ink mt-1">
              {data.avg_lead_time_days != null ? `${data.avg_lead_time_days} days` : '—'}
            </h3>
          </GlassCard>

          <GlassCard accent="rose" className="py-5">
            <p className="text-[10px] text-muted uppercase tracking-wider">PO Acceptance Rate</p>
            <h3 className="text-3xl font-mono tabular-nums font-semibold text-ink mt-1">{poStr}</h3>
          </GlassCard>
        </StaggerItem>

        {/* Charts: Risk Trend and SHAP Impact */}
        <StaggerItem className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <GlassCard accent="indigo">
            <h3 className="text-sm font-semibold text-ink uppercase tracking-wider mb-4 border-b border-hairline pb-2 flex items-center gap-2">
              <TrendingUp size={16} className="text-accent-indigo" /> Historic Risk Score Trend
            </h3>
            <div className="h-[260px]">
              {trendData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={trendData} margin={{ top: 10, right: 10, left: -20, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.12)" />
                    <XAxis dataKey="cycle" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                    <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} domain={[0, 100]} unit="%" />
                    <RechartsTooltip contentStyle={{ background: '#0f172a', border: '1px solid rgba(148,163,184,0.2)', borderRadius: 12 }} />
                    <Line type="monotone" dataKey="score" stroke="#06b6d4" strokeWidth={2.5} dot={{ r: 4 }} isAnimationActive={!reduced} />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex h-full items-center justify-center text-xs text-muted italic">
                  No historical trend logged.
                </div>
              )}
            </div>
          </GlassCard>

          <GlassCard accent="cyan">
            <h3 className="text-sm font-semibold text-ink uppercase tracking-wider mb-4 border-b border-hairline pb-2 flex items-center gap-2">
              <ShieldAlert size={16} className="text-accent-cyan" /> ML Feature Attribution (SHAP)
            </h3>
            <div className="h-[260px]">
              {shapData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={shapData} layout="vertical" margin={{ top: 10, right: 10, left: 20, bottom: 5 }}>
                    <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 9 }} unit="%" />
                    <YAxis dataKey="name" type="category" tick={{ fill: '#94a3b8', fontSize: 9 }} width={100} axisLine={false} tickLine={false} />
                    <RechartsTooltip contentStyle={{ background: '#0f172a', border: '1px solid rgba(148,163,184,0.2)', borderRadius: 12 }} />
                    <Bar dataKey="impact" radius={[0, 4, 4, 0]} barSize={10} isAnimationActive={!reduced}>
                      {shapData.map((entry: any, index: number) => (
                        <Cell 
                          key={`cell-${index}`} 
                          fill={entry.direction === 'increases_risk' ? '#f43f5e' : '#10b981'} 
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex h-full items-center justify-center text-xs text-muted italic">
                  No feature attribution data recorded.
                </div>
              )}
            </div>
          </GlassCard>
        </StaggerItem>

        {/* Action History and Probation Metrics */}
        <StaggerItem className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          
          {/* Action History Table/List */}
          <div className="lg:col-span-2 space-y-4">
            <GlassCard accent="indigo" className="!p-0 overflow-hidden">
              <div className="p-5 pb-3 border-b border-hairline">
                <h3 className="text-sm font-semibold text-ink uppercase tracking-wider">Mitigation Actions Audit</h3>
              </div>
              <div className="max-h-[360px] overflow-y-auto">
                {data.actions && data.actions.length > 0 ? (
                  <table className="w-full text-xs text-left">
                    <thead>
                      <tr className="border-b border-hairline text-muted">
                        <th className="px-5 py-3 font-semibold">Action</th>
                        <th className="px-4 py-3 font-semibold">Status</th>
                        <th className="px-4 py-3 font-semibold">Cost</th>
                        <th className="px-5 py-3 font-semibold">Reasoning</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.actions.map((a: any) => (
                        <tr key={a.action_id} className="border-b border-hairline hover:bg-slate-800/20">
                          <td className="px-5 py-3">
                            <div className="font-semibold text-ink">{a.action_type.replace(/_/g, ' ')}</div>
                            <div className="text-[10px] text-muted font-mono">{a.sku_id} · {new Date(a.created_at).toLocaleDateString()}</div>
                          </td>
                          <td className="px-4 py-3">
                            <span className={clsx(
                              'font-medium uppercase text-[10px]',
                              a.status === 'executed' || a.status === 'approved' ? 'text-risk-low' :
                              a.status === 'rejected' ? 'text-risk-high' : 'text-risk-medium'
                            )}>{a.status}</span>
                          </td>
                          <td className="px-4 py-3 font-mono tabular-nums">
                            {a.estimated_impact?.cost_delta ? `$${a.estimated_impact.cost_delta.toLocaleString()}` : '—'}
                          </td>
                          <td className="px-5 py-3 text-muted max-w-[200px] truncate" title={a.reasoning}>
                            {a.reasoning}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="p-8 text-center text-xs text-muted italic">
                    No actions logged for this supplier.
                  </div>
                )}
              </div>
            </GlassCard>
          </div>

          {/* Onboarding Probation Status */}
          <div className="space-y-4">
            <GlassCard accent="cyan" className="flex flex-col h-full">
              <h3 className="text-sm font-semibold text-ink uppercase tracking-wider mb-4 border-b border-hairline pb-2 flex items-center gap-2">
                <BarChart3 size={16} className="text-accent-cyan" /> Onboarding Probation
              </h3>
              
              {data.onboarding ? (
                <div className="space-y-4 flex-1">
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-muted">Probation Status</span>
                    <span className={clsx(
                      'text-xs font-semibold px-2 py-0.5 rounded border capitalize',
                      data.onboarding.status === 'APPROVED' && 'bg-emerald-900/20 text-risk-low border-emerald-700/30',
                      data.onboarding.status === 'REJECTED' && 'bg-rose-900/20 text-risk-high border-rose-700/30',
                      data.onboarding.status === 'IN_PROBATION' && 'bg-cyan-900/20 text-accent-cyan border-cyan-700/30',
                      data.onboarding.status === 'PENDING_REVIEW' && 'bg-amber-900/20 text-risk-medium border-amber-700/30'
                    )}>{data.onboarding.status.replace('_', ' ').toLowerCase()}</span>
                  </div>

                  <div className="space-y-1.5">
                    <div className="flex justify-between text-xs">
                      <span className="text-muted">On-Time Delivery Rate</span>
                      <span className="font-mono tabular-nums text-ink font-semibold">{(data.onboarding.probation_on_time_rate * 100).toFixed(1)}%</span>
                    </div>
                    <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
                      <div 
                        className={clsx('h-full', data.onboarding.probation_on_time_rate >= 0.85 ? 'bg-risk-low' : 'bg-risk-high')}
                        style={{ width: `${data.onboarding.probation_on_time_rate * 100}%` }}
                      />
                    </div>
                    <div className="text-[10px] text-muted">Auto-approve threshold: &gt;= 85%</div>
                  </div>

                  <div className="space-y-1.5">
                    <div className="flex justify-between text-xs">
                      <span className="text-muted">PO Rejection Rate</span>
                      <span className="font-mono tabular-nums text-ink font-semibold">{(data.onboarding.probation_rejection_rate * 100).toFixed(1)}%</span>
                    </div>
                    <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
                      <div 
                        className={clsx('h-full', data.onboarding.probation_rejection_rate < 0.03 ? 'bg-risk-low' : 'bg-risk-high')}
                        style={{ width: `${data.onboarding.probation_rejection_rate * 100}%` }}
                      />
                    </div>
                    <div className="text-[10px] text-muted">Auto-reject threshold: &gt; 8%</div>
                  </div>

                  <div className="grid grid-cols-2 gap-2 pt-2 border-t border-hairline text-xs text-muted">
                    <div>POs Recorded</div>
                    <div className="text-right text-ink font-medium">{data.onboarding.probation_po_count} POs</div>
                    <div>Days Left</div>
                    <div className="text-right text-ink font-medium">
                      {data.onboarding.days_remaining !== null ? `${data.onboarding.days_remaining} days` : '—'}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex-1 flex flex-col items-center justify-center p-6 text-center text-xs text-muted border border-dashed border-hairline rounded-xl">
                  <CheckCircle2 className="text-muted mb-2" size={24} />
                  <span>Onboarded supplier profile is mature and graduated. No probation constraints exist.</span>
                </div>
              )}
            </GlassCard>
          </div>

        </StaggerItem>
      </Stagger>
    </div>
  );
}

export default SupplierDetail;
