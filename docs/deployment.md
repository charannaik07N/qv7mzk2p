# Deployment and publication — remaining actions

No public URLs are currently verified. The steps below require a network-enabled machine with Docker access and the intended hosting/GitHub accounts. They do not require writing application code manually.

## 1. Finish local verification

From the project root:

```sh
cp .env.example .env
cd frontend
npm install
npm test
npm run build
cd ..
python3 scripts/secret_scan.py
docker compose config --quiet
docker compose up --build
```

`npm install` must generate a real `frontend/package-lock.json`; retain it; the frontend Dockerfile automatically uses `npm ci` when this file exists. A lockfile was not fabricated in the restricted build environment. Confirm all peer/dependency installation issues are fixed before proceeding.

Open http://localhost:8080 and http://localhost:8000/docs. Check unavailable, loading and error states, then acquisition:

```sh
docker compose exec backend python -m app.storage
curl --fail http://localhost:8000/api/health
curl --fail http://localhost:8000/api/metadata
curl --fail 'http://localhost:8000/api/overview?delivery_date=2026-01-15'
```

If the schema gate fails, review the official endpoint documentation/OpenAPI location before changing the client. Confirm the publication query window, top-level response array, fields, MW units, explicit timestamp offsets, superseded vintages and lack of stream pagination. Inspect representative real FUELHH/WIND and WINDFOR records. Reconcile actual target counts with 1,488 expected January half-hours, and explain missing coverage and any revision/vintage limitations. Multiple vintages do not prove complete history.

Compare one eligible publication to the cutoff manually and hand-calculate the signed/absolute error. Check the explorer, all accuracy breakdowns, CSV export, missing-data indicators and user-demand scenario. Do not record observed metrics until data provenance is verified.

## 2. Anonymous public GitHub repository

The random repository name is in `repository-name.txt`. The source bundle, if provided in the root handover, can be cloned without changing the original workspace:

```sh
repo_name=$(cat docs/repository-name.txt)
git clone windmarket-submission.bundle "$repo_name"
cd "$repo_name"
gh auth login --hostname github.com
python3 scripts/secret_scan.py
git status --short
gh repo create "$repo_name" --public --source=. --remote=origin --push
gh repo view --json url,visibility
```

Verify `visibility` is `PUBLIC`, open the returned URL signed out, and record it in the README. Avoid displaying authenticated account menus in the video. No GitHub account name is embedded in the prepared repository branding. If working directly in a copied source folder without the bundle:

```sh
git init -b main
git config user.name 'WindMarket Engineering'
git config user.email 'engineering@example.invalid'
git add .
git diff --cached --check
git commit -m 'Build auditable wind forecast evaluation workspace'
```

Then run the same `gh repo create` command. Review all staged files and history before publishing; do not commit data snapshots, `.env`, credentials, dependency caches or local runtime files. Generate and commit the frontend lockfile and update test results after the successful installation/build.

## 3. Separate Docker backend

Use Render's Blueprint import for `render.yaml` from the public repository, or a compatible Docker host with a persistent disk mounted at `/data`. A persistent disk may require a paid plan; provision it in the intended account. This is an account action, not a service already created.

- Set `CORS_ORIGINS` to the exact final Vercel HTTPS origin (update after frontend creation).
- Leave `ADMIN_TOKEN` empty to disable remote refresh, or create a long random secret only in the host secret store. Do not send it to the frontend.
- Use one service instance/worker; cross-process refresh locking is not implemented.
- Container port is 8000 and health check is `/api/health`.
- In the host shell, run `python -m app.storage` to load durable January CSV snapshots. If host shell is unavailable, use the token-protected API from a secure local client; do not place a real secret in documentation or browser code.
- Verify `/api/health`, `/api/metadata`, `/docs`, and a covered overview interval over public HTTPS. Confirm a restart preserves `lastSuccessfulRefresh` and data counts.

The supplied blueprint requests a persistent disk; using an ephemeral/free service without a different durable snapshot loading strategy does not meet persistence requirements. No database or external data bucket is silently provisioned.

## 4. Vercel frontend

Import the GitHub repository in Vercel:

- Root directory: `frontend`.
- Framework: Vite.
- Install: `npm ci` after the lockfile is committed.
- Build: `npm run build`.
- Output: `dist`.
- Environment: `VITE_API_BASE_URL` = verified HTTPS backend origin, without `/api` suffix.

Deploy, record the actual HTTPS frontend origin, set that exact origin in backend `CORS_ORIGINS`, then redeploy/restart the backend. If the backend URL changes, rebuild the frontend; Vite environment variables are embedded at build time. There is no localhost dependency in production.

Alternative CLI from `frontend` after authenticating the Vercel account:

```sh
npx vercel login
npx vercel
npx vercel env add VITE_API_BASE_URL production
npx vercel --prod
```

Enter the verified backend origin when prompted. Review the generated project linkage before publishing.

## 5. Public acceptance checks

- Open frontend signed out; all five routes/tabs render on desktop and tablet.
- Check public backend health and metadata and verify CORS from the deployed frontend.
- Change January delivery date and cutoff; ensure KPI/chart responses update and sample counts agree.
- Check an interval with multiple vintages if available; post-cutoff records must not be selected.
- Compare decision mode with separately labelled retrospective latest.
- Run user-demand scenario and verify residual arithmetic, missing-forecast rejection and limitations.
- Reload after restarting the backend and confirm durable cache provenance.
- Confirm an unauthenticated refresh is denied and errors expose no secrets.
- Replace “none verified” URL fields in README only after checks pass.
- Run secret scan and `git diff --check`; review Git history and public visibility.

## 6. Video

Follow `recording-checklist.md`. Record one ≤10-minute video, upload as **Unlisted**, and verify playback signed out. No recording or YouTube upload has been performed in this delivery.
