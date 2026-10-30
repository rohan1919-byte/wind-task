// Chart colours mirror the CSS variables in styles.css.
export const C = {
  ink: "#11283B",
  teal: "#0E8388",
  tealSoft: "#CFE8E8",
  risk: "#C8553D",
  muted: "#5B6B7A",
  line: "#DDE3E0",
  sand: "#F1E2BD",
};

export const axis = { stroke: C.muted, fontSize: 12, tickLine: false };
export const tooltipStyle = {
  contentStyle: { borderRadius: 10, border: `1px solid ${C.line}`, boxShadow: "0 6px 20px rgba(17,40,59,.12)", fontSize: 13 },
  labelStyle: { color: C.ink, fontWeight: 600 },
};
