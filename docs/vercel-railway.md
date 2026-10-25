# Vercel frontend + Railway backend

No public deployment is claimed. `YOUR-BACKEND` and `YOUR-FRONTEND` below are placeholders, not verified URLs.

## Folder structure

```text
repository/
├── frontend/                    ← Vercel Root Directory
│   ├── src/
│   │   ├── main.jsx
│   │   ├── components.jsx
│   │   ├── api.js               ← VITE_API_BASE_URL + /api/…
│   │   └── style.css
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.js
│   ├── vercel.json              ← npm ci, npm run build, dist
│   ├── .env.example
│   └── index.html
├── backend/                     ← Railway Root Directory: /backend
│   ├── app/
│   │   ├── main.py              ← app.main:app, /api/health, /docs
│   │   ├── source.py
│   │   ├── normalization.py
│   │   ├── storage.py
│   │   ├── analytics.py
│   │   └── config.py
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── start.sh                 ← 0.0.0.0:${PORT:-8000}
│   ├── railway.json
│   ├── .dockerignore
│   └── .env.example
├── data/                        ← ignored local snapshots
├── docs/
│   └── vercel-railway.md
├── scripts/
├── compose.yaml                 ← local development only
├── .gitignore
└── README.md
```

The Railway volume mounts at `/data` inside the running container. It is not the repository `data/` folder. Do not upload data into Vercel or depend on Railway's ephemeral container disk for durable snapshots.

## 1. Railway backend

1. Create a Railway project and deploy the GitHub repository as one service.
2. Set **Root Directory** to `/backend`.
3. Set the **Railway Config File** to `/backend/railway.json` if it is not automatically detected. The config-file path is relative to the repository root, independently of the service root.
4. Use the supplied Dockerfile. Leave custom build/start commands blank: the Dockerfile invokes `sh /service/start.sh`. The script uses Railway's injected `PORT`.
5. Attach a persistent volume mounted at `/data`. Use one replica; snapshot refresh coordination is process-local.
6. Set service variables:

| Variable | Value |
|---|---|
| `DATA_DIR` | `/data` |
| `CORS_ORIGINS` | `https://YOUR-FRONTEND.vercel.app` (replace with exact origin, no trailing slash) |
| `AUTO_REFRESH_ON_STARTUP` | `1` |
| `ENABLE_LOCAL_REFRESH` | `0` |
| `DEFAULT_CUTOFF` | `09:20` |
| `RAILWAY_RUN_UID` | `0` for write access to the root-owned mounted volume |
| `ADMIN_TOKEN` | Optional generated secret; never put this in Vercel/browser variables |

Railway documents `RAILWAY_RUN_UID=0` for images using non-root users with its mounted volumes. This overrides the Dockerfile's default non-root user for that service. If your deployment policy requires non-root execution, provision compatible volume ownership instead; do not enable startup acquisition against an unwritable directory.

7. Deploy, then use **Networking → Generate Domain**. Record the actual public HTTPS origin.
8. Open `<RAILWAY_ORIGIN>/api/health` and `<RAILWAY_ORIGIN>/docs`.

The server starts independently of acquisition. A successful health check means the API is running, not that January data has finished loading. `AUTO_REFRESH_ON_STARTUP=1` initiates acquisition only when no valid snapshot exists. A failure remains visible in `/api/metadata` under `refresh`; it does not crash the service or fabricate observations. Subsequent redeployments reuse the mounted snapshot.

For a controlled retry, use the Railway service shell to run `python -m app.storage`, or configure `ADMIN_TOKEN` and call `POST /api/admin/refresh` from a secure client with `X-Admin-Token`. Run acquisition at runtime, not as a pre-deploy command: the volume is not mounted during pre-deploy.

## 2. Vercel frontend

Import the same GitHub repository:

| Setting | Value |
|---|---|
| Root Directory | `frontend` |
| Framework | Vite |
| Install Command | `npm ci` |
| Build Command | `npm run build` |
| Output Directory | `dist` |
| Environment variable | `VITE_API_BASE_URL=https://YOUR-BACKEND.up.railway.app` |

Use the actual Railway origin, without trailing `/api`. The frontend appends `/api` itself. The Nginx Docker proxy is only for local Compose; Vercel serves the built static files and calls Railway directly.

Deploy. Copy the resulting Vercel production origin into Railway `CORS_ORIGINS`, then redeploy/restart Railway. Explicitly list any additional custom/preview origins you intend to support, comma-separated. Do not use `*` for production.

Changing `VITE_API_BASE_URL` requires a new Vercel deployment because Vite embeds it during the build. VITE-prefixed values are public; the API origin belongs there, credentials do not.

## Logs to check

These are **illustrative patterns**, not logs from an actual Railway/Vercel deployment. Port, duration, process IDs and counts vary.

Railway **Build Logs** should show Dockerfile detection, Python requirements installation and successful image creation. Railway **Deploy Logs** should include patterns such as:

```text
Using detected Dockerfile!
INFO:     Started server process [...]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:<Railway PORT>
INFO:app.storage:Elexon refresh started: January 2026 FUELHH and WINDFOR
INFO:     ... "GET /api/health HTTP/1.1" 200 OK
```

After successful real acquisition, storage logs report actual counts:

```text
INFO:app.storage:Elexon refresh completed: actual_intervals=<count> forecast_intervals=<count> snapshot=<id>
```

Do not interpret that line alone as complete vintage history. Inspect coverage and exclusions in `/api/metadata` and the dashboard.

Vercel **Deployment → Build Logs** should show:

```text
npm ci
npm run build
vite ... building for production...
... modules transformed
... dist/assets/...
... built in ...
```

The static frontend has no FastAPI runtime logs in Vercel. Inspect browser Developer Tools → Network/Console for frontend requests, and Railway HTTP/application logs for backend errors. Never paste secrets or real admin headers into logs or screenshots.

| Symptom | What to check |
|---|---|
| `No module named app` | Railway root `/backend`; use supplied Docker start command |
| Health check timeout / 502 | Uvicorn must bind `0.0.0.0` and Railway's `PORT`; check deploy logs |
| `PermissionError` under `/data` | Volume attachment and `RAILWAY_RUN_UID=0`, or provisioned directory ownership |
| `vite: command not found` | Vercel root `frontend`; `npm ci` must install dev/build dependencies |
| Browser CORS rejection | Exact deployed Vercel origin in Railway `CORS_ORIGINS`; restart backend |
| HTML returned instead of API JSON | `VITE_API_BASE_URL` missing/wrong; use Railway origin, rebuild Vercel |
| `/api/api/...` returns 404 | Remove `/api` suffix from `VITE_API_BASE_URL` |
| Dashboard says no snapshot | Inspect `/api/metadata` refresh state and Railway acquisition logs |
| Local-loading action unavailable | Expected in production; use startup acquisition or authenticated admin refresh |
| Data disappears on redeploy | Verify mounted persistent `/data` volume and `DATA_DIR` |

## Verify after deployment

Replace placeholders with your actual domains:

```sh
curl --fail https://YOUR-BACKEND.up.railway.app/api/health
curl --fail https://YOUR-BACKEND.up.railway.app/api/metadata
curl -i -H 'Origin: https://YOUR-FRONTEND.vercel.app' \
  'https://YOUR-BACKEND.up.railway.app/api/overview?delivery_date=2026-01-15'
curl --fail --head https://YOUR-FRONTEND.vercel.app/
```

Confirm the overview response contains the matching `Access-Control-Allow-Origin` header. Open the frontend and exercise its filters, history, accuracy and scenario views. Verify that restart preserves the snapshot and source timestamps. Do not mark deployment complete until these checks pass.

## Official references

- [Railway monorepo roots and config paths](https://docs.railway.com/deployments/monorepo)
- [Railway Dockerfile builds](https://docs.railway.com/builds/dockerfiles)
- [Railway PORT and health checks](https://docs.railway.com/deployments/healthchecks)
- [Railway persistent volumes and permissions](https://docs.railway.com/volumes)
- [Vercel Vite deployment](https://vercel.com/docs/frameworks/frontend/vite)
- [Vercel environment variable deployment behavior](https://vercel.com/docs/environment-variables)
