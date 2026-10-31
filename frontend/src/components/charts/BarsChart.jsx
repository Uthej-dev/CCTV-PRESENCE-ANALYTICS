import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import ChartTooltip from "./ChartTooltip";
import Legend from "./Legend";

/**
 * Column chart for one or more series sharing ONE y-axis.
 * series: [{ key, label, color }]
 */
export default function BarsChart({
  data,
  xKey,
  series,
  xFormatter = (v) => v,
  tooltipLabel,
  valueFormatter,
  height = 260,
  xInterval = "preserveStartEnd",
}) {
  return (
    <div>
      <Legend series={series} />
      <div className="chart" style={{ height }}>
        <ResponsiveContainer>
          <BarChart data={data} margin={{ top: 8, right: 4, bottom: 0, left: -18 }} barGap={2} barCategoryGap="20%">
            <CartesianGrid vertical={false} stroke="var(--grid)" />
            <XAxis dataKey={xKey} tickFormatter={xFormatter} tickLine={false} axisLine={{ stroke: "var(--border)" }} interval={xInterval} minTickGap={8} />
            <YAxis allowDecimals={false} tickLine={false} axisLine={false} width={48} />
            <Tooltip
              cursor={{ fill: "var(--surface-2)" }}
              content={<ChartTooltip labelFormatter={tooltipLabel || xFormatter} valueFormatter={valueFormatter} />}
            />
            {series.map((s) => (
              <Bar key={s.key} dataKey={s.key} name={s.label} fill={s.color} maxBarSize={24} radius={[4, 4, 0, 0]} isAnimationActive={false} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
