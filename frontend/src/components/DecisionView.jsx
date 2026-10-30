import { useMemo } from "react";
import { Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import Kpi from "./Kpi.jsx";
import { C, axis, tooltipStyle } from "../theme.js";
import { dateTimeLabel, download, longDate, num, timeLabel, toCsv } from "../format.js";

export default function DecisionView({ meta, date, setDate, day }) {
  const days = meta.delivery_days;
  const idx = days.indexOf(date);

  const chartData = useMemo(
    () => (day ? day.points.map((p) => ({ ...p, band: p.lo != null ? [p.lo, p.hi] : null })) : []),
    [day]
  );
  const rows = useMemo(() => (day ? day.points.filter((p) => p.forecast != null && p.t.slice(14, 16) === "00") : []), [day]);
  const s = day?.summary;

  return (
    <>
      <div className="hero">
        <div>
          <h2>{longDate(date)}</h2>
          <p>
            {day
              ? `Decision cutoff ${day.decision_cutoff_local} (London). Showing the latest forecast published before it.`
              : "Loading…"}
          </p>
        </div>
        <div className="picker">
          <button disabled={idx <= 0} onClick={() => setDate(days[idx - 1])} aria-label="Previous day">←</button>
          <select value={date} onChange={(e) => setDate(e.target.value)} aria-label="Delivery day">
            {days.map((d) => (
              <option key={d} value={d}>{longDate(d)}</option>
            ))}
          </select>
          <button disabled={idx >= days.length - 1} onClick={() => setDate(days[idx + 1])} aria-label="Next day">→</button>
        </div>
      </div>

      {!day && <div className="state">Loading forecast…</div>}

      {s && !s.has_forecast && (
        <div className="error">No forecast was published before the cutoff for this delivery day.</div>
      )}

      {s?.has_forecast && (
        <>
          <div className="kpis">
            <Kpi label="Average wind forecast" value={num(s.mean_forecast)} unit="MW" hint={`${s.forecast_gwh?.toFixed(0)} GWh over the day`} />
            <Kpi label="Peak" value={num(s.peak_forecast)} unit="MW" hint={`at ${timeLabel(s.peak_time)}`} tone="good" />
            <Kpi label="Lowest" value={num(s.min_forecast)} unit="MW" hint={`at ${timeLabel(s.min_time)} – likely top-up window`} />
            <Kpi
              label="Cautious average (P10)"
              value={num(s.conservative_mean)}
              unit="MW"
              hint="Wind you can lean on 9 days in 10"
              tone="risk"
            />
            <Kpi label="Forecast published" value={timeLabel(s.latest_publish)} hint={dateTimeLabel(s.latest_publish)} />
          </div>

          <div className="card">
            <h3>Wind generation: forecast at decision time vs. what actually happened</h3>
            <p className="sub">
              The shaded band is the range actual wind has landed in 80% of the time relative to this forecast, based on January's errors.
            </p>
            <div className="legend">
              <span><i className="swatch" style={{ background: C.teal }} /> Forecast (as seen on the day before)</span>
              <span><i className="swatch box" style={{ background: C.tealSoft }} /> Planning range (P10–P90)</span>
              <span><i className="swatch" style={{ background: C.ink }} /> Actual outturn</span>
            </div>
            <ResponsiveContainer width="100%" height={340}>
              <ComposedChart data={chartData} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                <CartesianGrid stroke={C.line} vertical={false} />
                <XAxis dataKey="t" tickFormatter={timeLabel} interval={5} {...axis} />
                <YAxis tickFormatter={(v) => `${(v / 1000).toFixed(0)} GW`} width={56} {...axis} />
                <Tooltip
                  {...tooltipStyle}
                  labelFormatter={(l) => `${timeLabel(l)} London`}
                  formatter={(v, n) => (Array.isArray(v) ? [`${num(v[0])} – ${num(v[1])} MW`, n] : [`${num(v)} MW`, n])}
                />
                <Area type="monotone" dataKey="band" name="Planning range" stroke="none" fill={C.tealSoft} fillOpacity={0.9} connectNulls />
                <Line type="monotone" dataKey="forecast" name="Forecast" stroke={C.teal} strokeWidth={2.5} dot={false} connectNulls />
                <Line type="monotone" dataKey="actual" name="Actual" stroke={C.ink} strokeWidth={2} dot={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          {s.day_mae != null && (
            <div className="callout">
              <h3>How did this day turn out?</h3>
              <p>
                Average miss was <strong>{num(s.day_mae)} MW</strong>; the forecast ran{" "}
                <strong>{Math.abs(Math.round(s.day_bias)).toLocaleString("en-GB")} MW {s.day_bias > 0 ? "high" : "low"}</strong> on average
                ({s.forecast_gwh?.toFixed(0)} GWh forecast vs {s.actual_gwh?.toFixed(0)} GWh actual).
                {s.day_bias > 0 ? " A high forecast means less wind than expected, so more top-up power would have been needed." : " A low forecast means more wind than expected, so the desk may have over-bought."}
              </p>
            </div>
          )}

          <div className="card" style={{ marginTop: 18 }}>
            <div className="row">
              <div>
                <h3 style={{ margin: 0 }}>Hourly numbers</h3>
                <p className="sub" style={{ margin: 0 }}>What the desk would have had in front of them.</p>
              </div>
              <button className="btn" onClick={() => download(`wind-forecast-${date}.csv`, toCsv(day.points))}>
                Download CSV
              </button>
            </div>
            <div className="tablewrap">
              <table>
                <thead>
                  <tr><th>Time</th><th>Forecast MW</th><th>Low (P10)</th><th>High (P90)</th><th>Actual MW</th></tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <tr key={r.t}>
                      <td>{timeLabel(r.t)}</td>
                      <td>{num(r.forecast)}</td>
                      <td>{num(r.lo)}</td>
                      <td>{num(r.hi)}</td>
                      <td>{num(r.actual)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </>
  );
}
