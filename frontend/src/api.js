const BASE = import.meta.env.VITE_API_BASE || "";

async function get(path) {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} for ${path}`);
  return res.json();
}

export const api = {
  meta: () => get("/api/meta"),
  day: (d) => get(`/api/day/${d}`),
  accuracy: () => get("/api/accuracy"),
};
