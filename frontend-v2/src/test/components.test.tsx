import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { GlassCard } from '../components/ui/GlassCard';
import { KpiCard } from '../components/ui/KpiCard';

describe('UI Components', () => {
  it('renders GlassCard correctly with children', () => {
    render(<GlassCard accent="indigo">Test Content</GlassCard>);
    expect(screen.getByText('Test Content')).toBeInTheDocument();
  });

  it('renders KpiCard with static details', () => {
    render(<KpiCard label="Overall Risk" value={75} accent="rose" />);
    expect(screen.getByText('Overall Risk')).toBeInTheDocument();
  });
});
