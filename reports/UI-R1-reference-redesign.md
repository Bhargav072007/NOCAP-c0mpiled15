# UI-R1 — MeghyanAI reference redesign

Latest user direction: use the components and visual treatment from
https://meghyanai.com/ for this NoCap project, change the UI and run it again.
This supersedes the earlier Liquid Glass direction for the current visual
implementation; the PDF-derived requirements and historical reports remain intact.

## Implemented

- Inspected the public reference in Chrome, including hero, feature, demo and
  workflow sections. Read-only inspection; no external forms were submitted.
- Adapted its black canvas (#0a0a0a), large system typography, white pill primary
  actions, outlined secondary actions, fine-bordered cards, segmented controls,
  navigation, three-step guide and decorative radial SVG to NoCap.
- Preserved NoCap's lime status/focus accent and all four functional native views.
  Reference commercial claims, metrics, logos and pricing are not displayed.
- Header and hero links scroll to the workspace and guide. Every fixture verdict
  stays labeled. Native forms, previews, API adapter and exact ledger export remain.
- Scoped CSS and supported Streamlit themes/widgets; no application JavaScript
  manipulates framework DOM. Reduced motion/transparency, keyboard focus and mobile
  layouts remain. Native framework controls are styled adaptations, not a claim
  of pixel-identical rendering of the reference site's frontend.
- Decorative SVG is an adapted reference component, not an evidence visualization.
  Inline SVG was removed by Streamlit sanitization; a local SVG image encoded in
  an HTML image now renders correctly. Server restart loads the new imported shell.

## Files

`dashboard/shell.py`, `dashboard/assets/mandala.svg`, `dashboard/app.py`,
`dashboard/ui.py`, `dashboard/style.css`, `.streamlit/config.toml`,
`scripts/reference_ui.py`, `scripts/inspect_ui.py`, `README.md`, reports and context.

## Evidence and checks

Reference captures and computed styles: `reports/reference/`. Main reference:
[hero](reference/meghyan-hero.png), [feature card](reference/meghyan-section-0.png),
[demo component](reference/meghyan-section-2.png).

`.venv/bin/python -m pytest -q`: 46 passed, 7 subtests passed. One existing upstream
websockets deprecation warning. No new live-integration coverage is implied.

`.venv/bin/python scripts/inspect_ui.py`: passed. Two complete rehearsals;
original/edited uploads, media download exact bytes, mixed/fake citations and
reasons, retained inputs, JSON downloads deep-equal to the adapter, disabled
fixture anchor, empty/disconnected/malformed/slow/60-record/recovery states,
10-second polling, reduced transparency, reduced motion and keyboard focus.
All four views checked at 1440×900, 1280×720 and 390×844 with no document
horizontal overflow. New hero links and decorative image loading also passed.

Initial checks exposed a sanitized SVG and stale imported shell, fixed with the
image component and server restart. A rapid second-rehearsal mouse selection
missed the opening dropdown; the browser test now uses the native keyboard
combobox interaction. Final complete run passed. Historical debugging screenshot
is retained as `browser-failure.png`; it is not a delivery screenshot.

Visually inspected the settled desktop hero, desktop capture view and mobile
ledger. Chrome is the verified browser; full screen-reader/cross-browser audits
remain unperformed. Actual downloaded snapshots are
[run 1](UI-R1-downloaded-ledger-1.json) and [run 2](UI-R1-downloaded-ledger-2.json).
Machine-readable results: [browser checks](UI-R1-browser-checks.json).

Screenshots: [desktop hero](screenshots/UI-R1/final-default-captures.png),
[captures](screenshots/UI-R1/UI-R1-captures-1440.png),
[citations](screenshots/UI-R1/UI-R1-citations-results.png),
[mobile ledger](screenshots/UI-R1/UI-R1-ledger-390.png).
Original P1–P7 reports/screenshots were preserved.

## Run and external dependencies

Server restarted with:

```bash
NOCAP_MODE=fixture .venv/bin/streamlit run dashboard/app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true --browser.gatherUsageStats false
```

Kept running on port 8501 for the user. Open http://localhost:8501 (or the IDE's
forwarded port). No public deployment, push or merge. Live API, hardware, signing,
citation verification, RPC/wallet credentials and real Sepolia confirmation remain
external dependencies. P6/P7 live requirements remain open. Next: user review of
the running redesign, then teammate-owned live integration when available.


Final visual check also covered the 390px mobile hero; corrected whitespace at the responsive line break. Targeted Chrome check passed with no horizontal document overflow; updated mobile screenshot saved. Final server restart returned health: ok on port 8501. No functional code changed after the full regression.
