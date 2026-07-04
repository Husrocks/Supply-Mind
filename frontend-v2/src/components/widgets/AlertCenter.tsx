import { memo } from 'react';
import { AlertTriangle, Info, ShieldAlert } from 'lucide-react';
import clsx from 'clsx';
import type { AlertItem } from '../../types';
import { GlassCard } from '../ui/GlassCard';

const ICONS = {
  critical: ShieldAlert,
  elevated: AlertTriangle,
  info: Info,
};

interface AlertCenterProps {
  alerts: AlertItem[];
  onAlertClick?: (alert: AlertItem) => void;
}

export const AlertCenter = memo(function AlertCenter({ alerts, onAlertClick }: AlertCenterProps) {
  return (
    <GlassCard accent="rose">
      <h3 className="text-base font-semibold text-ink mb-3">Alert Center</h3>
      {alerts.length === 0 ? (
        <p className="text-xs text-muted">No active alerts</p>
      ) : (
        <ul className="space-y-2 max-h-48 overflow-y-auto">
          {alerts.map((a) => {
            const Icon = ICONS[a.severity];
            const isClickable = Boolean(onAlertClick && (a.supplierId || a.skuId));
            return (
              <li 
                key={a.id} 
                onClick={() => onAlertClick?.(a)}
                className={clsx(
                  "flex gap-2 p-2 rounded-xl bg-slate-800/40 border border-hairline text-xs",
                  isClickable && "cursor-pointer hover:bg-slate-800/60 transition-colors"
                )}
              >
                <Icon size={14} className={clsx(
                  a.severity === 'critical' ? 'text-risk-high' :
                  a.severity === 'elevated' ? 'text-risk-medium' : 'text-accent-cyan'
                )} />
                <div>
                  <p className="font-medium text-ink">{a.title}</p>
                  <p className="text-body mt-0.5">{a.message}</p>
                  <time className="text-muted text-[10px]">{new Date(a.timestamp).toLocaleString()}</time>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </GlassCard>
  );
});
