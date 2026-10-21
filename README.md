# Domain Watchdog

Checks four domains every 5 s, stores results in PostgreSQL, shows them on a React dashboard.

## Backend
```bash
cd server
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env     # set the postgres password for your container
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Frontend
```bash
cd frontend && npm install && npm run dev   # http://localhost:5173
```

## Charts
The dashboard shows a response-time line chart per domain (hatched bands mark downtime). Range: last hour / 24 hours / 7 days, served by `GET /api/domains/{hostname}/chart?range=1h|24h|7d`.

## Tests
```bash
cd server && pytest      # integration/contract tests need the local Postgres
cd frontend && npm test
```
