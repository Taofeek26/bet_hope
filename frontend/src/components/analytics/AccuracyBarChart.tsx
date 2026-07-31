'use client';

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';

export interface AccuracyBarDatum {
  label: string;
  accuracy: number; // 0-1
  total: number;
  correct: number;
}

function ChartTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const d: AccuracyBarDatum = payload[0].payload;
  if (d.total === 0) {
    return (
      <div className="rounded-lg border border-border bg-card px-3 py-2 text-xs shadow-lg">
        <div className="font-medium text-text">{d.label}</div>
        <div className="text-text-muted">No data yet</div>
      </div>
    );
  }
  return (
    <div className="rounded-lg border border-border bg-card px-3 py-2 text-xs shadow-lg">
      <div className="font-medium text-text">{d.label}</div>
      <div className="text-text-secondary">
        {(d.accuracy * 100).toFixed(1)}% accurate &middot; {d.correct}/{d.total} correct
      </div>
    </div>
  );
}

/**
 * Horizontal bar chart for accuracy-by-category breakdowns (outcome,
 * confidence tier, etc). Single hue since it's one measure (accuracy)
 * across a small fixed set of categories, not multiple series needing
 * identity color — per the dataviz guidance, magnitude gets one hue,
 * not a rainbow per bar.
 */
export function AccuracyBarChart({ data }: { data: AccuracyBarDatum[] }) {
  const chartData = data.map((d) => ({ ...d, accuracyPct: Math.round(d.accuracy * 1000) / 10 }));

  return (
    <div className="h-48 sm:h-56 w-full" role="img" aria-label="Accuracy by category bar chart">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ top: 4, right: 16, bottom: 4, left: 4 }}
          barCategoryGap={12}
        >
          <CartesianGrid horizontal={false} stroke="#222222" strokeDasharray="3 3" />
          <XAxis
            type="number"
            domain={[0, 100]}
            tickFormatter={(v) => `${v}%`}
            stroke="#666666"
            tick={{ fill: '#A3A3A3', fontSize: 12 }}
            axisLine={{ stroke: '#222222' }}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="label"
            width={110}
            stroke="#666666"
            tick={{ fill: '#A3A3A3', fontSize: 12 }}
            axisLine={{ stroke: '#222222' }}
            tickLine={false}
          />
          <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(56, 189, 248, 0.06)' }} />
          <Bar dataKey="accuracyPct" radius={[0, 4, 4, 0]} maxBarSize={22}>
            {chartData.map((entry, index) => (
              <Cell key={index} fill={entry.total === 0 ? '#333333' : '#38BDF8'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
