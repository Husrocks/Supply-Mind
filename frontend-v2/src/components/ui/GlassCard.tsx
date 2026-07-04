import { memo, type ReactNode } from 'react';
import clsx from 'clsx';
import type { RiskAccent } from '../../types';

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  accent?: RiskAccent;
}

export const GlassCard = memo(function GlassCard({ children, className, accent = 'indigo' }: GlassCardProps) {
  return (
    <div className={clsx('glass-card', `glass-card--${accent}`, className)}>
      {children}
    </div>
  );
});
