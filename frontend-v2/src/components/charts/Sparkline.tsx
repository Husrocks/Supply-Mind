import { memo } from 'react';
import { LineChart, Line, ResponsiveContainer } from 'recharts';
import { usePrefersReducedMotion } from '../../hooks/usePrefersReducedMotion';

interface SparklineProps {
  data: number[];
  color?: string;
  width?: number;
  height?: number;
}

export const Sparkline = memo(function Sparkline({
  data,
  color = '#6366f1',
  width = 72,
  height = 24,
}: SparklineProps) {
  const reduced = usePrefersReducedMotion();

  if (data.length < 2) {
    return <span className="text-muted text-xs">—</span>;
  }

  const chartData = data.map((v, i) => ({ i, v }));

  return (
    <div style={{ width, height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <Line
            type="monotone"
            dataKey="v"
            stroke={color}
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={!reduced}
            animationDuration={400}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
});
