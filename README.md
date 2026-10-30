# WindDesk

Day-ahead wind forecast and accuracy portal for a UK power buying desk (national wind, Elexon BMRS only, January 2026).


## How it works
- Delivery day D is bought on D-1 at a cutoff (default 09:00 London, `DECISION_CUTOFF_HOUR` / `DECISION_CUTOFF_MINUTE`).
- Forecast used = latest WINDFOR row with `publishTime` ≤ cutoff. Later forecasts are never used.
- Actuals = FUELHH, `fuelType = WIND`. Joined on `startTime`. Sign: `error = forecast − actual`.
- Metrics: MAE, RMSE, bias, wMAPE, P90/P95 error, by day / hour / forecast age. Planning range = P10–P90 of January errors (in-sample, pilot only).

## Run
**Docker:** `docker compose up --build` → http://localhost:8000

**Local:**
```bash
cd backend && python -m venv .venv && .venv\Scripts\activate   
pip install -r requirements.txt && uvicorn app.main:app --port 8000

cd frontend && npm install && npm run dev                      
```
First start downloads data from Elexon into `backend/data/`. If Elexon is unreachable, labelled demo data is shown.
Tests: `cd backend && pytest`

## Files
```
backend/app/       config, elexon (API client), analysis (metrics), store, demo, main (FastAPI)
backend/scripts/   fetch_data.py (one-off download)
backend/tests/     unit tests
frontend/src/      React app (Decision view, Accuracy view)
Dockerfile, docker-compose.yml, vercel.json, api/index.py
```

## Limitations
No demand data (out of scope); wind only, national level.