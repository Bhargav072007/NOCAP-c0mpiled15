# P6 — Demo validation and handoff

Status: **partial overall; fixture demo fully rehearsed twice**. Live integration
cannot be established without teammate services/hardware. All independently
available local checks below passed.

Changed: `scripts/inspect_ui.py`, `README.md`, `requirements-lock.txt`, browser
check JSON, downloaded ledger evidence, screenshots, report/context.

Commands/checks actually run:
- `.venv/bin/python -m pytest -q`: **26 passed, 7 subtests passed**.
- Local Streamlit launched on 127.0.0.1:8501; clean restart validated new imports.
- `.venv/bin/python scripts/inspect_ui.py`: **two full browser rehearsals passed**.
  Original media download matches exact asset bytes; photo/audio selection works;
  original upload returns DEMO VERIFIED, edited upload returns DEMO CAP; upload
  remains after capture refresh; mixed citation report returns all four statuses,
  planted fake report returns three NOT_FOUND outcomes; reasons expand correctly.
- Downloaded `nocap_ledger.json` twice through Chrome. Both files parse and
  deep-equal the fixture adapter response, with SHA-256
  `dc2dd6bb34278e27dff422e7024cc2a732363db4540b66c3a3947c80421489a8`.
- Empty, disconnected, malformed, recovery, 1.5-second fixture delay/spinner,
  60-record list, manual reduced transparency, and system reduced motion pass.
- Four views at 1440x900, 1280x720, 390x844 have no document horizontal overflow.
  Native tabs support arrow-key focus and Space activation; focus outline is
  solid and Tab continues into controls. Screenshots visually inspected.
- Primary solid-token contrast: dark/lime 14.53:1; text/panel 16.29:1;
  secondary/panel 8.15:1; failure/panel 8.34:1; amber/panel 10.60:1.
  These are token calculations, not a claim of complete accessibility auditing.

Evidence: `reports/P6-browser-checks.json`, `reports/P6-downloaded-ledger-1.json`,
`reports/P6-downloaded-ledger-2.json`, and `reports/screenshots/P6-*.png`.
Screenshots with accessibility settings enabled intentionally show opaque panels.
A sidebar locator initially failed in the browser test; updated it to the
actual native control and reran the full workflow successfully.

Setup/run/live commands: `README.md`. Rehearsal: `demo/README.md`. No provider
lookups, signatures, hardware, deployment or blockchain confirmation occurred.
No live credentials were needed for the local checks. Screen-reader behavior,
all browsers and full transition profiling were not audited; no video recorded.

Next: user-authorized P7 server-side Sepolia anchoring and mocked RPC checks.
Live API/hardware demo, signed chain verification, actual citation lookup and
pre-demo confirmed anchor remain open external dependencies.
