import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import ChartTooltip from "./ChartTooltip";

/** Single-series line over categories (e.g. days). */
export default function TrendLineChart({ data, xKey, yKey, label, color = "var(--series-1)", xFormatter, yFormatter, valueFormatter, height = 220 }) {
  return (
    <div className="chart" style={{ height }}>
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -6 }}>
          <CartesianGrid vertical={false} stroke="var(--grid)" />
          <XAxis dataKey={xKey} tickFormatter={xFormatter} tickLine={false} axisLine={{ stroke: "var(--border)" }} minTickGap={8} />
          <YAxis tickFormatter={yFormatter} tickLine={false} axisLine={false} width={56} />
          <Tooltip cursor={{ stroke: "var(--text-3)", strokeWidth: 1 }} content={<ChartTooltip labelFormatter={xFormatter} valueFormatter={valueFormatter} />} />
          <Line
            type="monotone"
            dataKey={yKey}
            name={label}
            stroke={color}
            strokeWidth={2}
            dot={{ r: 4, fill: color, stroke: "var(--surface)", strokeWidth: 2 }}
            activeDot={{ r: 5, stroke: "var(--surface)", strokeWidth: 2 }}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
