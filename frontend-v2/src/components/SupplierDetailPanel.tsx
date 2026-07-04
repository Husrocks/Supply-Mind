import { useState } from 'react';
import type { SupplierContext } from '../types';
import { apiClient } from '../api/client';
import { Loader2, AlertCircle, X } from 'lucide-react';
import toast from 'react-hot-toast';

interface SupplierDetailPanelProps {
  supplier: SupplierContext | null;
  onClose: () => void;
}

export function SupplierDetailPanel({ supplier, onClose }: SupplierDetailPanelProps) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  if (!supplier) return null;

  const triggerAgent = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await apiClient.post('/agent/trigger', {
        primary_supplier_id: supplier.supplier_id,
        trigger_type: "MANUAL",
        sku_id: "FOODS_1_001_CA_1_evaluation"
      });
      setResult(response.data);
      toast.success(`Agent triggered successfully for ${supplier.supplier_id}`);
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to trigger agent';
      setError(errorMsg);
      toast.error(`Escalation Failed: ${errorMsg}`);
    } finally {
      setLoading(false);
    }
  };

  const getRiskColor = (score: number) => {
    if (score < 0.4) return 'text-semantic-up';
    if (score <= 0.7) return 'text-accent-yellow';
    return 'text-semantic-down';
  };

  return (
    <div className="absolute right-0 top-0 h-full w-96 bg-canvas border-l border-hairline p-8 flex flex-col overflow-y-auto shadow-card z-10">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-lg font-semibold text-ink">
          {supplier.supplier_id}
        </h2>
        <button onClick={onClose} className="p-2 hover:bg-surface-strong rounded-full text-muted transition-colors">
          <X size={18} />
        </button>
      </div>

      <div className="mb-8 p-5 bg-surface-soft rounded-xl border border-hairline">
        <div className="text-sm text-muted mb-1">Risk Score</div>
        <div className={`font-mono text-3xl ${getRiskColor(supplier.risk_score)} flex items-baseline gap-2`}>
          {(supplier.risk_score * 100).toFixed(1)}%
          <span className="text-sm font-sans font-medium text-muted uppercase">{supplier.risk_level}</span>
        </div>
      </div>

      <div className="mb-8">
        <h3 className="text-xs font-semibold text-muted uppercase tracking-wider mb-4 border-b border-hairline pb-2">
          Top Risk Drivers (SHAP)
        </h3>
        {supplier.shap_drivers && supplier.shap_drivers.length > 0 ? (
          <ul className="space-y-3">
            {supplier.shap_drivers.slice(0, 3).map((driver, idx) => (
              <li key={idx} className="p-3 rounded-xl border border-hairline">
                <div className="flex justify-between items-center mb-1">
                  <span className="font-medium text-ink capitalize text-sm">
                    {driver.feature.replace(/_/g, ' ')}
                  </span>
                  <span className={`text-xs font-medium ${driver.direction === 'increases_risk' ? 'text-semantic-down' : 'text-semantic-up'}`}>
                    {driver.direction === 'increases_risk' ? '↑ Risk' : '↓ Risk'}
                  </span>
                </div>
                <div className="text-sm font-mono text-muted">
                  {(driver.impact * 100).toFixed(1)}%
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <div className="text-sm text-muted italic p-4 text-center bg-surface-soft rounded-xl">
            No driver data available
          </div>
        )}
      </div>

      <div className="mt-auto pt-6">
        <button
          onClick={triggerAgent}
          disabled={loading}
          className="btn-primary w-full"
        >
          {loading ? (
            <>
              <Loader2 className="animate-spin" size={18} />
              Running Analysis...
            </>
          ) : (
            'Trigger Agent Analysis'
          )}
        </button>

        {error && (
          <div className="mt-4 p-3 border border-hairline rounded-xl text-semantic-down text-sm flex items-start gap-2 bg-surface-soft">
            <AlertCircle size={16} className="mt-0.5 shrink-0" />
            <p>{error}</p>
          </div>
        )}

        {result && (
          <div className="mt-4 p-4 border border-hairline rounded-xl bg-surface-soft">
            <h4 className="text-semantic-up font-semibold text-sm mb-2">Analysis complete</h4>
            <div className="text-sm text-body">
              Generated {result.actions_generated} actions.
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
