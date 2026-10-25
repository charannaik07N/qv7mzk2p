# WindMarket Intelligence — recording script

Target duration: **9 minutes 30 seconds**, hard stop before 10 minutes. One unlisted YouTube video with two parts. Rehearse with a timer; remove pauses rather than accelerate explanations. This is a script, not evidence a recording exists.

## Part 1 — client presentation (0:00–4:45)

**0:00–0:30 — Problem.** “A utility plans purchases before it knows actual wind output. We need to evaluate the forecast available at the purchase decision, rather than a more accurate forecast published later.” Explain national wind-only scope and January 2026.

**0:30–1:25 — Overview.** Select a verified covered January date. Show D−1 cutoff and latest publication no later than the decision. Point to snapshot freshness and matched sample. State the 09:20 cutoff is a modelling assumption, not a desk instruction. If data remains unavailable, explain this and do not show invented values.

**1:25–2:20 — Comparison and audit.** Show actual and selected forecast profiles. Inspect one settlement period, publication timestamp, forecast age and error. Change decision time to demonstrate eligibility only if retained vintages support the example. Show ineligible later publications in the ledger.

**2:20–3:20 — Accuracy.** Explain MAE as typical absolute MW error, RMSE as more sensitive to large errors, and positive bias as overestimated wind. Read actual backend values and sample sizes only. Switch briefly to retrospective latest and explain the difference, then return to decision-time mode. Discuss coverage and zero-actual percentage exclusions.

**3:20–4:15 — Scenario.** Enter a clearly labelled user demand assumption. Show max(0, demand − forecast wind), then the actual-wind comparison under the same demand assumption. Explain how overestimated wind can leave a greater residual requirement. Do not call this a complete trading recommendation.

**4:15–4:45 — Limitations and next steps.** Summarize auditability, incomplete-vintage risk and missing data. No prices, weather, measured savings or claimed operational improvements. Next steps are verified source coverage, trading-desk cutoff confirmation and broader operational integration.

## Part 2 — technical review (4:45–9:30)

**4:45–5:25 — Architecture.** Show the Mermaid diagram: React, FastAPI, vectorized analytics, immutable CSV snapshot, HTTPX ingestion. Explain durable local volume / separate production backend.

**5:25–6:10 — Acquisition.** Show source client, schema gate, publication-time chunks, concurrency two, timeout/retry handling, WIND filtering and source-specific parsers. State which source semantics were actually verified after network access is restored. If not verified, explicitly retain that limitation.

**6:10–7:05 — Temporal selection.** Show `analytics.evaluate`: publication ≤ cutoff, latest per target, full settlement grid, left join actuals. Explain Europe/London day boundaries, 46/50 DST tests and separate retrospective mode. Show one cutoff test and metric example.

**7:05–7:45 — API and UI.** Show `/docs`, validated inputs, protected refresh, data hook cancellation, loading/error/unavailable states and ledger audit. Point to modular files without reading every function.

**7:45–8:30 — Tests and quality.** Run the backend tests and, after dependencies are installed, frontend tests/build. Report only actual results. Explain conflicts, missing actuals, WAPE denominator and no synthetic fallback.

**8:30–9:30 — Operations and handover.** Show Compose configuration and successful local startup if verified. Show public URLs only after verifying them. Explain exact CORS, public API base, persistent snapshots and secret handling. End with current limitations and outstanding actions. Stop recording by 9:30.
