import { useState } from 'react';
import { Play, Loader2, GitBranch } from 'lucide-react';
import { useSkuRiskContextMutation } from '../../hooks/useDashboardQueries';
import { GlassCard } from '../ui/GlassCard';
import clsx from 'clsx';
import { riskScoreColor } from '../../utils/risk';

interface RiskContextSimulatorProps {
  skuId: string;
  defaultSupplierId?: string;
  defaultInventory?: number;
  availableSuppliers: { supplier_id: string; supplier_name: string }[];
}

export function RiskContextSimulator({ 
  skuId, 
  defaultSupplierId = '', 
  defaultInventory = 5000,
  availableSuppliers
}: RiskContextSimulatorProps) {
  const [supplierId, setSupplierId] = useState(defaultSupplierId);
  const [inventory, setInventory] = useState(defaultInventory.toString());
  const [altSuppliers, setAltSuppliers] = useState<string[]>([]);
  const [result, setResult] = useState<any>(null);

  const mutation = useSkuRiskContextMutation();

  const handleSimulate = async () => {
    if (!supplierId) return;
    try {
      const data = await mutation.mutateAsync({
        skuId,
        supplierId,
        currentInventory: parseInt(inventory, 10) || 0,
        alternativeSuppliers: altSuppliers
      });
      setResult(data);
    } catch (err) {
      console.error(err);
    }
  };

  const toggleAltSupplier = (id: string) => {
    setAltSuppliers(prev => 
      prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id]
    );
  };

  return (
    <GlassCard accent="indigo" className="!p-0 overflow-hidden">
      <div className="p-5 pb-4 border-b border-hairline flex items-center justify-between">
        <h3 className="text-sm font-semibold text-ink uppercase tracking-wider flex items-center gap-2">
          <GitBranch size={16} className="text-accent-indigo" /> Simulate Risk Context
        </h3>
        <button 
          onClick={handleSimulate}
          disabled={mutation.isPending || !supplierId}
          className="btn-primary !h-8 !text-xs !px-4 flex items-center gap-1.5"
        >
          {mutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
          Run Simulation
        </button>
      </div>
      
      <div className="p-5 grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">Primary Supplier</label>
            <select 
              value={supplierId}
              onChange={(e) => setSupplierId(e.target.value)}
              className="w-full bg-slate-900/50 border border-slate-700/50 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500/50"
            >
              <option value="" disabled>Select primary supplier</option>
              {availableSuppliers.map(s => (
                <option key={s.supplier_id} value={s.supplier_id}>{s.supplier_name} ({s.supplier_id})</option>
              ))}
            </select>
          </div>
          
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">Current Inventory Level</label>
            <input 
              type="number"
              value={inventory}
              onChange={(e) => setInventory(e.target.value)}
              className="w-full bg-slate-900/50 border border-slate-700/50 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500/50"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">Alternative Suppliers</label>
            <div className="flex flex-wrap gap-2">
              {availableSuppliers.filter(s => s.supplier_id !== supplierId).map(s => {
                const isSelected = altSuppliers.includes(s.supplier_id);
                return (
                  <button
                    key={s.supplier_id}
                    onClick={() => toggleAltSupplier(s.supplier_id)}
                    className={clsx(
                      "px-3 py-1.5 rounded-lg text-xs font-medium transition-colors border",
                      isSelected 
                        ? "bg-indigo-500/20 text-indigo-300 border-indigo-500/30" 
                        : "bg-slate-800/50 text-slate-400 border-slate-700/50 hover:bg-slate-700/50"
                    )}
                  >
                    {s.supplier_name}
                  </button>
                );
              })}
              {availableSuppliers.filter(s => s.supplier_id !== supplierId).length === 0 && (
                <span className="text-xs text-slate-500 italic">No alternatives available</span>
              )}
            </div>
          </div>
        </div>

        <div className="bg-slate-900/40 rounded-xl border border-slate-800/50 p-4 flex flex-col">
          <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Simulation Results</h4>
          
          {mutation.isError ? (
            <div className="text-rose-400 text-sm p-4 bg-rose-500/10 rounded-lg border border-rose-500/20">
              Failed to run simulation. Check console for details.
            </div>
          ) : result ? (
            <div className="space-y-4">
              <div className="flex items-end gap-3">
                <div className="flex-1">
                  <p className="text-[10px] text-slate-500 uppercase">Primary Risk Score</p>
                  <p className="text-3xl font-mono font-semibold" style={{ color: riskScoreColor(result.risk_score) }}>
                    {(result.risk_score * 100).toFixed(1)}%
                  </p>
                </div>
                <div className="flex-1">
                  <p className="text-[10px] text-slate-500 uppercase">Status</p>
                  <p className="text-lg font-semibold text-slate-200">
                    {result.context_frame?.primary_supplier?.risk_level || 'UNKNOWN'}
                  </p>
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-3 mt-4">
                <div className="bg-slate-950/50 p-3 rounded-lg border border-slate-800/50">
                  <p className="text-[10px] text-slate-500 uppercase mb-1">Stockout ETA</p>
                  <p className="font-mono text-sm text-slate-300">{result.context_frame?.demand_forecast?.days_to_stockout} days</p>
                </div>
                <div className="bg-slate-950/50 p-3 rounded-lg border border-slate-800/50">
                  <p className="text-[10px] text-slate-500 uppercase mb-1">Alt Routes Found</p>
                  <p className="font-mono text-sm text-slate-300">{result.context_frame?.alternative_routes?.length || 0}</p>
                </div>
              </div>
              
              {result.context_frame?.alternative_routes?.length > 0 && (
                <div className="mt-3">
                  <p className="text-[10px] text-slate-500 uppercase mb-2">Alternative Capacities</p>
                  <div className="space-y-2">
                    {result.context_frame.alternative_routes.map((route: any, i: number) => (
                      <div key={i} className="flex justify-between items-center text-xs bg-slate-950/50 p-2 rounded border border-slate-800/50">
                        <span className="text-slate-300">{route.supplier_id}</span>
                        <span className="font-mono text-emerald-400">+{route.available_capacity} units</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center text-slate-500 text-sm italic">
              Run a simulation to see predicted ML context frame.
            </div>
          )}
        </div>
      </div>
    </GlassCard>
  );
}
