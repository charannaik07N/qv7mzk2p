# Validation evidence — 25 October 2026

## Local redesign and data-loading update

- Frontend Vite production build passed, with separate React/chart chunks.
- 8 frontend tests passed, including data-loading progress/failure states.
- 31 backend tests passed, including local refresh origin/loopback/content-type/cooldown checks.
- Launcher shell syntax, Python compilation and source scan passed.
- Official OpenAPI URL corrected to https://data.elexon.co.uk/swagger/v1/swagger.json and publication queries reviewed through the browser tool.
- Live observation acquisition still blocked by this session's DNS; no January data fabricated.
- The light UI has not been inspected in a live browser from this session.

## Earlier implementation checks (historical record)

| Check | Actual result |
|---|---|
| Backend tests | 28 passed in 0.78s; one upstream Starlette TestClient/HTTPX deprecation warning |
| API integration | Passed in-process via FastAPI TestClient, with unavailable state and isolated synthetic observations |
| Hand calculations | MAE 20; RMSE sqrt(1400/3); bias 0; WAPE 40%, verified in tests |
| DST | 48 January, 46 spring-forward, 50 fall-back settlement intervals verified |
| JSX compilation | esbuild syntax/bundling check with external dependencies; no runtime/build equivalence |
| Frontend tests | Written; not run because dependencies unavailable |
| Frontend production build | Attempted, failed: `vite: command not found` after npm DNS failure |
| npm install | Failed `ENOTFOUND registry.npmjs.org`; offline cache lacks frontend libraries |
| Frontend lockfile | Not generated; must be generated after successful installation |
| Docker Compose config | `docker compose config --quiet` passed |
| Docker service start/build | Not run successfully; Docker socket permission denied |
| Uvicorn | Application startup complete; bind to 127.0.0.1:8000 denied by sandbox |
| Elexon API | Acquisition attempted; DNS failure, schema gate correctly stopped refresh |
| January observations | None acquired; no coverage or measured accuracy claimed |
| Public deployment | Not deployed or verified |
| GitHub | Existing authentication invalid; no public repository |
| Workspace Git init | Denied by filesystem permissions on `.git` |
| Video | Scripts ready; no recording/upload |

All quantitative test fixtures are synthetic and are kept in tests. No test data is loaded into the application store. No source failure is converted to zero or demonstration observations.


## Requested pre-deployment check

- `cd backend && ../.venv/bin/python -m pytest -q`: **31 passed**, 0.95 seconds; one upstream Starlette TestClient/HTTPX deprecation warning.
- `cd frontend && npm run build`: **passed**, Vite production build completed in 2.24 seconds; all generated chunks below the default 500 kB warning threshold.
- `docker compose config --quiet`: **passed**.
- `docker compose up --build -d`: **blocked**, permission denied connecting to the Docker API socket. No container build/start/health success is claimed.

Deployment must wait for Docker runtime verification on a machine/session with daemon access. Run from repository root:

```sh
docker compose up --build -d --wait
docker compose ps
curl --fail http://localhost:8000/api/health
curl --fail --head http://localhost:8080/
```

If startup fails there, inspect `docker compose logs --tail=100` before deployment. The socket restriction cannot be repaired by changing application source. No deployment was attempted during this check.
