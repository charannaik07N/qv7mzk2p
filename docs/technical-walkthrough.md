# Technical walkthrough

1. Start with `docs/architecture.mmd` and the README status. Distinguish implementation from live-source, runtime and deployment validation.
2. Open `backend/app/source.py`. The official OpenAPI schema must confirm publication query names before acquisition. Stream array shape is validated separately. Two bounded requests run at once, each spanning one publication day. Transient failures retry; non-transient HTTP failures stop. No alternate data source is used.
3. Open `normalization.py`. Actuals filter WIND, forecasts preserve publishTime. Offset-aware timestamps normalize to UTC. Negative/non-finite generation and malformed intervals are excluded. Identical rows collapse; conflicting keys are removed with counters.
4. Open `storage.py`. Read the immutable version directory and atomic pointer. Explain failed-refresh preservation and in-memory reload. Production needs durable `/data` and a single refresh writer. Raw source data is not committed.
5. Open `analytics.py`. Start from a complete UK settlement grid, select latest eligible publication, join on UTC start. Keep audit columns. Use matched-pair metrics and explicit denominators; nulls remain null. Show retrospective mode and why it is a separate evaluation.
6. Open the tests. Explain the hand-computed sample (errors +20, +10, −30), zero actual, exact-cutoff eligibility and DST days. Fixtures never enter runtime storage.
7. Open `main.py` and `/docs`. Show January enforcement, timezone validation, mode separation, pagination and the demand-scenario route. Refresh is disabled without a token, 403 with a wrong token, and preserves cache on upstream failure.
8. Open `frontend/src/api.js`, `components.jsx` and `main.jsx`. Explain data-hook cancellation, reusable states, no hardcoded generation KPIs, working filters/export, and scenario demand provenance. The UI exposes source limitations rather than hiding them.
9. Show Docker Compose and deployment guide. Local Nginx proxies same-origin `/api`; Vercel needs an explicit HTTPS backend base. CORS is exact-origin. Render uses a persistent disk; ephemeral filesystem is unsuitable for durable snapshots.
10. Report validation precisely: backend tests actually run; frontend/browser/container/public checks pending unless subsequently completed. Show the remaining steps and recording checklist.

## Reviewer questions

- **Could a future forecast leak into day-ahead evaluation?** Decision mode filters `publishTime <= decisionTime` before grouping; tested at equality and just after cutoff.
- **Does the snapshot prove complete history?** No. Multiple vintages are counted, but completeness stays false. Query windows and source limitations remain visible.
- **Why not use the latest wind endpoint?** It is a derived latest view; raw dataset publication queries are intended to retain superseded records according to Elexon’s developer portal.
- **Why no data bundled?** API access was blocked, and synthetic fixtures must never masquerade as observations. The unavailable state is intentional.
- **Why no MAPE?** Actual wind can be zero or small. Per-interval percentage errors exclude zero actual, and WAPE has an explicit summed-actual denominator.
- **Is demand observed?** No, both estimated and optional actual demand are user scenario inputs.
