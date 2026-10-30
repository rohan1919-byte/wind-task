export default function Kpi({ label, value, unit, hint, tone }) {
  return (
    <div className={`kpi ${tone || ""}`}>
      <div className="label">{label}</div>
      <div className="value">
        {value}
        {unit && <small>{unit}</small>}
      </div>
      {hint && <div className="hint">{hint}</div>}
    </div>
  );
}
