# P4 — Functional interactions

Status: complete for fixture and mocked API coverage; teammate live integration
remains outstanding. No signing, hardware or AI verifier has been implemented.

Changed: `dashboard/client.py`, `dashboard/ui.py`, `dashboard/app.py`,
`demo/*`, `scripts/make_demo_assets.py`, `tests/test_interactions.py`, report/context.
All four views now work: captures/media and full metadata; explicit multipart
file checks; text report submissions and expandable findings; ledger/export.
Added strict result validation, bounded file/HTTP sizes/timeouts, streamed media,
manual refresh and optional supported 10-second fragment polling. Source IDs,
uploads and text persist across unrelated refreshes. Successful duplicate POSTs
are avoided by per-session input fingerprints. No POST runs on ordinary rerender.

Demo assets are generated calibration graphics, a tone and a reading. Signatures
are empty. File verdicts are explicitly synthetic registry hash matches; citation
results are scripted for prepared fictional texts only. Unknown text fails with
an actionable explanation rather than an invented lookup. No fabricated DOI or
transaction. Fixture scenario controls cover empty, slow, malformed, disconnected,
recovery and a 60-record list. Sidebar defaults collapsed for mobile access.

Checks: `.venv/bin/python -m pytest -q` — 26 passed, 7 subtests passed.
Tests cover original/edited file bytes and verdicts, citation examples, live
multipart/body contracts, media path escaping, invalid result shapes, app input
preservation, POST deduplication, empty/disconnected/recovery states. Initial
AppTest failures were test-locator mistakes (relative file resolution and
selectbox ordering); repaired to use an absolute app path and stable key.
Browser upload/download checks follow in P6. No real API was available.

Next: P5 motion applied to actual response changes without replay on polling.
