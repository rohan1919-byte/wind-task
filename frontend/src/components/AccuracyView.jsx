import { Bar, BarChart, CartesianGrid, Cell, ComposedChart, Line, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import Kpi from "./Kpi.jsx";
import { C, axis, tooltipStyle } from "../theme.js";
import { num, pct, shortDate } from "../format.js";

function Card({ title, sub, children }) {
  return (
    <div className="card">
      <h3>{title}</h3>
      <p className="sub">{sub}</p>
      {children}
    </div>
  );
}

export default function AccuracyView({ acc, onPickDay }) {
  if (!acc) return <div className="state">Crunching January…</div>;
  const o = acc.overall;
  const buffer = o.q10_actual_minus_forecast != null ? Math.abs(o.q10_actual_minus_forecast) : null;
  const horizon = acc.horizon.buckets.map((b) => ({ ...b, label: `${b.from}–${b.to}h` }));
  const win = acc.horizon.decision_window;
  const hist = acc.histogram.map((h) => ({ ...h, label: `${h.start}`, mid: (h.start + h.end) / 2 }));

  return (
    <>
      <div className="hero">
        <div>
          <h2>How good are the forecasts?</h2>
          <p>
            Every half-hour of January 2026, using only what was published before each day-ahead cutoff ({o.n?.toLocaleString("en-GB")} points compared).
          </p>
        </div>
      </div>

      <div className="kpis">
        <Kpi label="Mean absolute error" value={num(o.mae)} unit="MW" hint="Typical miss, either direction" />
        <Kpi label="RMSE" value={num(o.rmse)} unit="MW" hint="Punishes the big misses" />
        <Kpi label="wMAPE" value={pct(o.wmape)} hint="Error as % of generation" />
        <Kpi
          label="Bias"
          value={`${o.bias > 0 ? "+" : ""}${num(o.bias)}`}
          unit="MW"
          hint={o.bias > 0 ? "Forecasts ran high on average" : "Forecasts ran low on average"}
          tone={Math.abs(o.bias) > o.mae * 0.25 ? "risk" : ""}
        />
        <Kpi label="90% of misses under" value={num(o.p90_abs)} unit="MW" hint={`95% under ${num(o.p95_abs)} MW`} />
        <Kpi label="Suggested wind haircut" value={num(buffer)} unit="MW" hint="Subtract from forecast to cover 90% of days" tone="risk" />
      </div>

      <div className="callout" style={{ marginTop: 0, marginBottom: 18 }}>
        <h3>What this means for buying</h3>
        <p>
          If you plan on the raw forecast, wind landed more than {num(buffer)} MW below it about 1 half-hour in 10. Holding roughly that
          much extra thermal or firm cover (or a cheaper hedge) closes most of that gap. The worst single half-hour was{" "}
          {num(o.max_overforecast)} MW below forecast.
        </p>
      </div>

      <div className="grid-2">
        <Card title="Error by delivery day" sub="Mean absolute error each day. Click a bar to open that day.">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={acc.daily} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid stroke={C.line} vertical={false} />
              <XAxis dataKey="date" tickFormatter={(d) => d.slice(8)} {...axis} />
              <YAxis tickFormatter={(v) => `${(v / 1000).toFixed(1)}k`} width={44} {...axis} />
              <Tooltip {...tooltipStyle} labelFormatter={shortDate} formatter={(v) => [`${num(v)} MW`, "MAE"]} />
              <Bar dataKey="mae" radius={[4, 4, 0, 0]} onClick={(d) => onPickDay(d.date)} cursor="pointer">
                {acc.daily.map((d) => (
                  <Cell key={d.date} fill={d.mae > o.mae * 1.4 ? C.risk : C.teal} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <p className="sub" style={{ margin: "8px 0 0" }}>Terracotta bars are days with 40%+ more error than the month's average.</p>
        </Card>

        <Card title="Over- or under-forecast each day" sub="Average of forecast minus actual. Above zero = less wind than promised.">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={acc.daily} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid stroke={C.line} vertical={false} />
              <XAxis dataKey="date" tickFormatter={(d) => d.slice(8)} {...axis} />
              <YAxis tickFormatter={(v) => `${(v / 1000).toFixed(1)}k`} width={44} {...axis} />
              <ReferenceLine y={0} stroke={C.ink} />
              <Tooltip {...tooltipStyle} labelFormatter={shortDate} formatter={(v) => [`${v > 0 ? "+" : ""}${num(v)} MW`, "Bias"]} />
              <Bar dataKey="bias" radius={[3, 3, 3, 3]}>
                {acc.daily.map((d) => (
                  <Cell key={d.date} fill={d.bias > 0 ? C.risk : C.teal} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Error vs. forecast age" sub="Forecasts get worse the further ahead they were made. The band is what a 9:00 day-ahead decision actually sees.">
          <ResponsiveContainer width="100%" height={280}>
            <ComposedChart data={horizon} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid stroke={C.line} vertical={false} />
              <XAxis dataKey="label" {...axis} />
              <YAxis tickFormatter={(v) => `${(v / 1000).toFixed(1)}k`} width={44} {...axis} />
              <Tooltip {...tooltipStyle} formatter={(v, n) => [`${num(v)} MW`, n]} />
              {horizon.length > 0 && (
                <ReferenceArea
                  x1={horizon.find((h) => win.from < h.to)?.label}
                  x2={[...horizon].reverse().find((h) => win.to > h.from)?.label}
                  fill={C.sand}
                  fillOpacity={0.55}
                  stroke="none"
                />
              )}
              <Bar dataKey="mae" name="MAE" fill={C.teal} radius={[4, 4, 0, 0]} />
            </ComposedChart>
          </ResponsiveContainer>
          <p className="sub" style={{ margin: "8px 0 0" }}>
            Day-ahead decisions use forecasts {win.from.toFixed(0)}–{win.to.toFixed(0)} hours old (sand area).
          </p>
        </Card>

        <Card title="Error by time of day" sub="Which half of the day is harder to call? Lines show MAE (teal) and bias (terracotta).">
          <ResponsiveContainer width="100%" height={280}>
            <ComposedChart data={acc.by_hour} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid stroke={C.line} vertical={false} />
              <XAxis dataKey="hour" tickFormatter={(h) => `${String(h).padStart(2, "0")}:00`} interval={3} {...axis} />
              <YAxis tickFormatter={(v) => `${(v / 1000).toFixed(1)}k`} width={44} {...axis} />
              <ReferenceLine y={0} stroke={C.line} />
              <Tooltip {...tooltipStyle} labelFormatter={(h) => `${String(h).padStart(2, "0")}:00`} formatter={(v, n) => [`${num(v)} MW`, n]} />
              <Line type="monotone" dataKey="mae" name="MAE" stroke={C.teal} strokeWidth={2.5} dot={false} />
              <Line type="monotone" dataKey="bias" name="Bias" stroke={C.risk} strokeWidth={2} dot={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </Card>
      </div>

      <div className="card" style={{ marginTop: 18 }}>
        <h3>Distribution of forecast errors</h3>
        <p className="sub">Each bar counts half-hours by how far forecast was from actual (500 MW bins). Right of zero = forecast too high.</p>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={hist} margin={{ top: 4, right: 8, left: 0, bottom: 0 }} barCategoryGap={1}>
            <CartesianGrid stroke={C.line} vertical={false} />
            <XAxis dataKey="label" interval={Math.ceil(hist.length / 12)} tickFormatter={(v) => `${(v / 1000).toFixed(1)}k`} {...axis} />
            <YAxis width={36} {...axis} />
            <Tooltip {...tooltipStyle} labelFormatter={(l, p) => (p?.[0] ? `${num(p[0].payload.start)} to ${num(p[0].payload.end)} MW` : l)} formatter={(v) => [v, "Half-hours"]} />
            <Bar dataKey="count">
              {hist.map((h) => (
                <Cell key={h.start} fill={h.mid > 0 ? C.risk : C.teal} fillOpacity={0.85} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </>
  );
}
