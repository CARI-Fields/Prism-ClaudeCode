# CC Orchestration Report — frontend (SPA)

Vite + React + TypeScript SPA that reproduces the layout of `reports/report.html`,
fetching raw rows from the backend API (`serve/`). Plan 2a = shell; charts in 2b/2c.

## Develop against a local backend

```bash
make serve            # repo root: uvicorn :8799 (run `make analyze` first)
cd web
echo 'VITE_API_BASE=http://localhost:8799' > .env.local   # not committed
npm install && npm run dev                                 # http://localhost:5173
```
First load prompts for the access token (the backend's `API_TOKEN`; leave it unset for open local dev). Stored in `localStorage` (`cc_report_token`).

## Build / deploy (Vercel)

- `npm run build` → `web/dist/`.
- Vercel: set **Root Directory = `web`** and env **`VITE_API_BASE`** = the HF Space URL; add the Vercel origins to the backend's `ALLOWED_ORIGINS`.

The stylesheet (`src/styles.css`) is ported verbatim from `reports/report.html`; components mirror its class names so the SPA matches the report's layout.

## Test

`npm test` (Vitest): pure logic unit-tested; components via React Testing Library.
