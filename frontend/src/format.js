const TZ = "Europe/London";

export const mw = (v) => (v == null ? "–" : `${Math.round(v).toLocaleString("en-GB")} MW`);
export const num = (v) => (v == null ? "–" : Math.round(v).toLocaleString("en-GB"));
export const gwh = (v) => (v == null ? "–" : `${v.toFixed(0)} GWh`);
export const pct = (v) => (v == null ? "–" : `${v.toFixed(1)}%`);
export const signed = (v) => (v == null ? "–" : `${v > 0 ? "+" : ""}${Math.round(v).toLocaleString("en-GB")} MW`);

export const timeLabel = (iso) =>
  new Date(iso).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: TZ });

export const dateTimeLabel = (iso) =>
  new Date(iso).toLocaleString("en-GB", {
    weekday: "short", day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", timeZone: TZ,
  });

export const longDate = (isoDate) =>
  new Date(`${isoDate}T12:00:00Z`).toLocaleDateString("en-GB", {
    weekday: "long", day: "numeric", month: "long", year: "numeric", timeZone: "UTC",
  });

export const shortDate = (isoDate) =>
  new Date(`${isoDate}T12:00:00Z`).toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "UTC" });

export function toCsv(points) {
  const head = "time_london,forecast_mw,planning_low_mw,planning_high_mw,actual_mw";
  const rows = points
    .filter((p) => p.forecast != null)
    .map((p) => [dateTimeLabel(p.t), p.forecast, p.lo, p.hi, p.actual ?? ""].join(","));
  return [head, ...rows].join("\n");
}

export function download(name, text) {
  const url = URL.createObjectURL(new Blob([text], { type: "text/csv" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}
