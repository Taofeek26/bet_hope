interface MetricRow {
  metric: string;
  value: string;
  remark: string;
}

interface MetricPlateProps {
  title: string;
  rows: MetricRow[];
}

/**
 * Numbered metric table (01, 02, ...) used for summary stat panels across
 * the dashboard, leagues, and analytics pages instead of a plain stat-card
 * grid — the blueprint corner-bracket "plate" look.
 */
export function MetricPlate({ title, rows }: MetricPlateProps) {
  return (
    <div className="blueprint plate mb-6">
      <i className="corner tl" /><i className="corner tr" /><i className="corner bl" /><i className="corner br" />
      <div className="metric-plate-header">
        <span>{title}</span>
      </div>
      {/* Phones: one stacked row per metric. A 4-column table left the remark
          about 60px wide, one word per line. */}
      <ul className="sm:hidden divide-y divide-border-dim">
        {rows.map((row, i) => (
          <li key={row.metric} className="px-4 py-3">
            <div className="flex items-baseline justify-between gap-3">
              <span className="text-sm text-text-sec">
                <span className="metric-row-num mr-2">{String(i + 1).padStart(2, '0')}</span>
                {row.metric}
              </span>
              <span className="metric-row-value text-right">{row.value}</span>
            </div>
            <div className="metric-row-remark text-xs mt-1">{row.remark}</div>
          </li>
        ))}
      </ul>
      <table className="w-full hidden sm:table">
        <thead>
          <tr className="border-b border-border text-left text-xs text-text-muted">
            <th className="px-5 py-2 font-normal">No.</th>
            <th className="px-5 py-2 font-normal">Metric</th>
            <th className="px-5 py-2 font-normal">Value</th>
            <th className="px-5 py-2 font-normal">Remark</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={row.metric} className="border-b border-border-dim last:border-b-0">
              <td className="px-5 py-3 metric-row-num">{String(i + 1).padStart(2, '0')}</td>
              <td className="px-5 py-3">{row.metric}</td>
              <td className="px-5 py-3 metric-row-value">{row.value}</td>
              <td className="px-5 py-3 metric-row-remark">{row.remark}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
