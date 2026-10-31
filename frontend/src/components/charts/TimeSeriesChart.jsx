import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import ChartTooltip from "./ChartTooltip";

/** Single-series area chart over time (2px line + 10% wash). x values are epoch millis. */
export default function TimeSeriesChart({
  data,
  xKey = "t",
  yKey,
  label,
  color = "var(--series-1)",
  xFormatter,
  tooltipLabel,
  valueFormatter,
  height = 260,
  domain,
  step = false,
}) {
  return (
    <div className="chart" style={{ height }}>
      <ResponsiveContainer>
        <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
          <CartesianGrid vertical={false} stroke="var(--grid)" />
          <XAxis
            dataKey={xKey}
            type="number"
            scale="time"
            domain={domain || ["dataMin", "dataMax"]}
            tickFormatter={xFormatter}
            tickLine={false}
            axisLine={{ stroke: "var(--border)" }}
            minTickGap={40}
          />
          <YAxis allowDecimals={false} tickLine={false} axisLine={false} width={48} />
          <Tooltip
            cursor={{ stroke: "var(--text-3)", strokeWidth: 1 }}
            content={<ChartTooltip labelFormatter={tooltipLabel || xFormatter} valueFormatter={valueFormatter} />}
          />
          <Area
            type={step ? "stepAfter" : "monotone"}
            dataKey={yKey}
            name={label}
            stroke={color}
            strokeWidth={2}
            fill={color}
            fillOpacity={0.1}
            activeDot={{ r: 4, stroke: "var(--surface)", strokeWidth: 2 }}
            dot={false}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
