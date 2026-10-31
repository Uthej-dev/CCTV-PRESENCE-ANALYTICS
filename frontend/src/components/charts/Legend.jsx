/** HTML legend shown above multi-series charts (identity never relies on color alone). */
export default function Legend({ series }) {
  if (series.length < 2) return null;
  return (
    <div className="legend" style={{ marginBottom: 8 }}>
      {series.map((s) => (
        <span className="tag" key={s.key}>
          <span className="swatch" style={{ background: s.color }} />
          {s.label}
        </span>
      ))}
    </div>
  );
}
