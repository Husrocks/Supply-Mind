import { memo } from 'react';
import { Bot, Clock, CalendarClock, Zap } from 'lucide-react';
import clsx from 'clsx';
import type { SchedulerHealth, AgentAction } from '../../types';
import { GlassCard } from '../ui/GlassCard';

interface AgentStatusWidgetProps {
  health: SchedulerHealth | undefined;
  isLoading: boolean;
  isError: boolean;
  lastAction?: AgentAction;
}

export const AgentStatusWidget = memo(function AgentStatusWidget({
  health,
  isLoading,
  isError,
  lastAction,
}: AgentStatusWidgetProps) {
  const running = health?.running ?? false;
  const schedulerUp = health?.scheduler_running ?? false;
  const lastTriggerType = health?.last_trigger_type ?? lastAction?.trigger_type ?? null;

  return (
    <GlassCard accent="cyan" className="!py-5">
      <div className="flex items-center gap-3 mb-4">
        <Bot size={18} className="text-accent-cyan" />
        <h3 className="text-sm font-semibold text-ink">Agent Status</h3>
        {!isLoading && !isError && health && (
          <span className="flex items-center gap-1.5 text-xs text-body ml-auto">
            <span className={clsx('w-2 h-2 rounded-full', running ? 'bg-accent-cyan pulse-live' : schedulerUp ? 'bg-risk-low' : 'bg-slate-600')} />
            {running ? 'Running' : schedulerUp ? 'Idle' : 'Stopped'}
          </span>
        )}
      </div>

      {isLoading ? (
        <p className="text-xs text-muted">Loading scheduler status…</p>
      ) : isError || !health ? (
        <p className="text-xs text-amber-400">Status unavailable — /scheduler/status unreachable</p>
      ) : (
        <dl className="grid grid-cols-2 gap-3 text-xs">
          <div>
            <dt className="text-muted flex items-center gap-1"><Clock size={12} /> Scheduler</dt>
            <dd className="text-ink font-medium mt-0.5">{schedulerUp ? 'Active' : 'Stopped'}</dd>
          </div>
          <div>
            <dt className="text-muted flex items-center gap-1"><CalendarClock size={12} /> Next run</dt>
            <dd className="text-ink font-mono tabular-nums mt-0.5 text-[11px]">
              {health.next_run_at ? new Date(health.next_run_at).toLocaleString() : '—'}
            </dd>
          </div>
          <div>
            <dt className="text-muted flex items-center gap-1"><Clock size={12} /> Last run</dt>
            <dd className="text-ink font-mono tabular-nums mt-0.5 text-[11px]">
              {health.last_run_at ? new Date(health.last_run_at).toLocaleString() : '—'}
            </dd>
          </div>
          <div>
            <dt className="text-muted flex items-center gap-1"><Zap size={12} /> Last trigger</dt>
            <dd className="text-ink mt-0.5 font-medium">{lastTriggerType ?? '—'}</dd>
          </div>
        </dl>
      )}
    </GlassCard>
  );
});
