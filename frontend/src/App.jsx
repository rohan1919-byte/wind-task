import { useEffect, useState } from "react";
import { api } from "./api.js";
import DecisionView from "./components/DecisionView.jsx";
import AccuracyView from "./components/AccuracyView.jsx";

export default function App() {
  const [tab, setTab] = useState("decision");
  const [meta, setMeta] = useState(null);
  const [date, setDate] = useState(null);
  const [day, setDay] = useState(null);
  const [acc, setAcc] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.meta()
      .then((m) => {
        setMeta(m);
        setDate(m.delivery_days[14]); // open mid-month so the first view has data on both sides
      })
      .catch((e) => setError(e.message));
    api.accuracy().then(setAcc).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!date) return;
    setDay(null);
    api.day(date).then(setDay).catch((e) => setError(e.message));
  }, [date]);

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <div className="logo">
            <svg width="22" height="22" viewBox="0 0 32 32" fill="none" stroke="#fff" strokeWidth="2.4" strokeLinecap="round">
              <path d="M7 12h13a3 3 0 1 0-3-3M7 17h17a3 3 0 1 1-3 3M7 22h9" />
            </svg>
          </div>
          <div>
            <h1>WindDesk</h1>
            <p>Day-ahead wind forecast &amp; accuracy · Great Britain</p>
          </div>
        </div>
        <nav className="tabs" role="tablist">
          <button role="tab" className={`tab ${tab === "decision" ? "active" : ""}`} onClick={() => setTab("decision")}>
            Decision view
          </button>
          <button role="tab" className={`tab ${tab === "accuracy" ? "active" : ""}`} onClick={() => setTab("accuracy")}>
            Forecast accuracy
          </button>
        </nav>
      </header>

      {meta?.source === "demo" && (
        <div className="banner">
          <strong>Demo data.</strong> The live Elexon feed could not be reached, so these numbers are generated for illustration only. {meta.note}
        </div>
      )}
      {error && <div className="error" style={{ marginBottom: 16 }}>Something went wrong: {error}</div>}

      {!meta && !error && <div className="state">Loading…</div>}

      {meta && tab === "decision" && <DecisionView meta={meta} date={date} setDate={setDate} day={day} />}
      {meta && tab === "accuracy" && (
        <AccuracyView
          acc={acc}
          onPickDay={(d) => {
            setDate(d);
            setTab("decision");
          }}
        />
      )}

      <footer>
        Source: Elexon BMRS (FUELHH actuals, WINDFOR forecasts), national wind only. All times London. Day-ahead cutoff {meta?.cutoff ?? "09:00"} the day before delivery.
      </footer>
    </div>
  );
}
