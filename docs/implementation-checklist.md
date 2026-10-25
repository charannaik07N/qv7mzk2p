# Implementation checklist
- [x] Inspect empty workspace, runtime and access constraints.
- [x] Consult official source documentation; dataset endpoints retain superseded publications.
- [ ] Verify precise schemas and representative January responses (blocked: API DNS inaccessible).
- [ ] Implement strict normalization, immutable snapshots, cutoff selection and tested analytics.
- [ ] Build validated API and React analytical workspace.
- [ ] Run tests, build and local HTTP checks.
- [ ] Prepare Docker, deployment instructions, anonymous Git repository and demo materials.

Environment: Node 24; managed Python 3.12 available; Docker installed but socket access denied; GitHub token invalid. No preexisting user files. No data substituted.

## Final implementation and verification
- [x] Strict dataset-specific normalization, publication selection, settlement alignment and metrics implemented.
- [x] Resilient source client, runtime schema gate and atomic CSV storage implemented.
- [x] Validated REST API, unavailable state and protected refresh implemented.
- [x] Five JSX dashboard screens, backend-derived KPIs, charts, ledger, history and scenarios implemented.
- [x] Backend suite executed: 28 tests passed.
- [x] Frontend JSX syntax checked with esbuild; production build remains blocked.
- [x] Compose configuration validated; container build/start remains blocked.
- [x] README, architecture, deployment steps and two-part ≤10-minute demo materials prepared.
- [x] Source secret/identifier pattern scan passed.
- [ ] Live January response/schema/coverage verification: blocked by external DNS access.
- [ ] Frontend dependency install/lockfile/tests/build/browser checks: blocked by registry access.
- [ ] Local HTTP and Docker runtime checks: blocked by sandbox socket permissions.
- [ ] GitHub public push: blocked by invalid account authentication.
- [ ] Public deployment and video: require authenticated accounts and the preceding runtime/data validation.
