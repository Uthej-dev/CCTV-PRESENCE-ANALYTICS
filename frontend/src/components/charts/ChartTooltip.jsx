/** Shared tooltip: title + one row per series (swatch beside text; text stays in text colors). */
export default function ChartTooltip({ active, payload, label, labelFormatter, valueFormatter = (v) => v }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tooltip">
      <div className="title">{labelFormatter ? labelFormatter(label, payload) : label}</div>
      {payload.map((p) => (
        <div className="line" key={p.dataKey}>
          <span>
            <span className="swatch" style={{ width: 8, height: 8, borderRadius: 2, background: p.color, display: "inline-block" }} />
            {p.name}
          </span>
          <strong>{valueFormatter(p.value, p.dataKey)}</strong>
        </div>
      ))}
    </div>
  );
}
