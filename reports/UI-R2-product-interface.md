# UI-R2 — NoCap public entry and workspace refinement

Status: implemented and locally validated. Timestamp: 2026-10-11T20:56:02+00:00.

## Latest user decision

The user requested the full MeghyanAI-style product: a main landing page, working
access and a clean dashboard. One NoCap device integrates with the cloud; no Devices
tab. This supersedes FS1's dashboard-only/five-section UI decision. Original PDF
requirements, earlier reports, source contracts and historical data remain intact.

## Reference inspection and design

Opened https://meghyanai.com/login in the in-app browser. A first tab showed Render's
wakeup interstitial; following Sign In from the live landing page loaded the real
login. Inspected its public demo account, Overview and Studio read-only. No remote
jobs, reports, settings, uploads, membership changes or messages were submitted.
The public demo credentials were not saved in the repository.

Matched the observed black canvas, system typography, large lightweight headings,
split-screen login, narrow persistent sidebar, white pill buttons, thin borders and
rounded panels. Adapted the product content to NoCap; no copied risk scores, pricing,
commercial claims or fabricated live results. No mandala, bulbs, ornamental dots or
floating gradient artwork. This is a Streamlit adaptation, not a pixel-identical
copy of the reference framework.

## Delivered

- Public landing with product navigation, a typographic hero, clearly labelled
  evidence-workflow illustration, a three-step workflow and working workspace links.
- Split login with real personal-token validation against `/me`, empty/invalid token
  feedback, explicit local-demo entry, protected workspace entry and session sign-out.
  No reference-site password is represented as a NoCap credential. Email/password,
  SSO, invitations and account recovery are not invented.
- Four dashboard sections: Overview, Evidence studio, Team workbench, Settings.
  No Devices tab, device enrollment dialog, fleet registry or fleet metric.
- Overview shows real API totals, latest three reviews, recent activity and human
  review progress. Single-source status is secondary in Settings. Ambiguous physical
  sources require an explicit `NOCAP_DEVICE_ID`; no silent device guessing.
- All existing capture previews, byte comparison, citation results, team assignments,
  comments, permissions and ledger export remain connected to the existing API.
- Authentication failure now blocks all workspace routes. The older Evidence studio
  fall-through after failed `/me` was removed. Production never uses the demo token.
- Mobile landing/login/workspace layouts, a two-column mobile metric grid, visible
  focus, reduced-motion CSS and persistent display/refresh preferences.

## Validation actually performed

- `.venv/bin/python -m pytest -q`: **66 passed, 7 subtests passed**. Two upstream
  deprecation warnings (websockets legacy and Starlette/httpx).
- `.venv/bin/python -m pip check`: no broken requirements.
- `.venv/bin/python -m compileall -q dashboard tests`: passed.
- New access regressions: unauthenticated direct-workspace redirect, invalid token,
  successful personal-token entry, later token rejection, sign-out clearing, explicit
  demo entry, no Devices navigation, unambiguous source selection, and preferences
  surviving navigation. Auth UI tests use a mocked HTTP adapter; backend token,
  role, expiration and tenant-isolation tests remain in the full suite.
- Live **local** browser: landing → sign-in → local demo; empty input rejected;
  actual invalid token returns 401; sign out returns to login. Landing workflow
  anchor scrolls to its section. Desktop button text was checked as rgb(17,17,17).
- Browser upload: synthetic original returned DEMO VERIFIED; edited bytes returned
  DEMO CAP. These are prepared demo verdicts, not genuine signature verification.
- Browser citation run: prepared mixed demo returned VERIFIED, MISMATCH, UNSUPPORTED
  and NOT_FOUND, all labelled DEMO.
- Browser ledger: seven records, zero supplied signatures, chain status Not checked,
  disabled fixture anchor; clicking Download ledger JSON emitted a download event.
  Separately, the exact export serializer output was compared with the local API
  and saved in `UI-R2-api-ledger.json`. No claim of re-reading browser-download bytes
  is made in this iteration; FS1's historical exact browser-download checks remain.
- Browser review: created `UI-R2 · workspace acceptance`, set In progress, saved a
  clearly synthetic discussion entry. A separate authenticated API read confirmed
  status and comment persistence. Existing rows were not deleted or rewritten.
- Visually inspected landing, login, overview, evidence studio and team layouts in
  the in-app Chromium browser. Desktop checks used the default 1280×720 and a
  1440×900 override; mobile checks used 390×844. Mobile Overview, Team workbench,
  Settings, Audit ledger and landing had no document horizontal overflow. Data
  tables retain their own internal horizontal scrolling.
- Reduced motion preference produced computed animation-name `none`. Automated
  test verifies preferences survive leaving Settings. CSS also respects the system
  media query; full screen-reader/cross-browser auditing was not performed.
- Both local health endpoints passed. API checks: `UI-R2-api-checks.json`.

Browser screenshots were captured and visually reviewed in the task conversation;
this iteration did not write new screenshot PNGs to the repository. Existing FS1
reference and product screenshots are preserved and are not labelled as UI-R2.

Initial new-test failures were test-harness assumptions about query parameter shape,
form batching and AppTest state access; fixed before the final 66-test pass. Browser
review found a white primary-form label, fixed by styling primary form buttons too.
A file chooser attempt against the hidden input timed out; the visible Upload control
worked. Reduced-motion switch interaction worked through the visible toggle after
locator clicks did not change its value. An initial API evidence script attempted a
text write for byte output; corrected to write_bytes and rerun successfully.

## Files and run

Changed: `dashboard/app.py`, `shell.py`, `workbench.py`, `ui.py`, `style.css`,
`tests/test_interactions.py`, `tests/test_anchor.py`, `README.md`, `docs/FULLSTACK.md`,
`.env.example`, `context.md`, reports index. New: `tests/test_entry.py`,
`tests/ui_helpers.py`, this report and UI-R2 API evidence. Backups/scratch under work/.
No repository `.git` exists; no commit, push, merge or public deployment occurred.

Run `.venv/bin/python scripts/run_local.py` from /home/divyamarorakkr/Compiled.
The running product is http://localhost:8501; choose Sign in → Open local demo.
The API is http://localhost:8000/docs. Existing SQLite and file data were retained.
Old FS1 browser scripts remain historical and target the retired five-section UI;
use the pytest suite and this browser checklist for current acceptance.

## Remaining external work

Actual AWS/RDS/S3 acceptance, physical device/signing integration, citation provider,
whole-chain verification, durable Sepolia orchestration and production identity work
remain as documented in FULLSTACK.md. No cloud infrastructure or shared migration
was applied. No live production-readiness or cryptographic success is claimed.
Next: user reviews the running interface; the operator configures the one real source
and existing backend integrations when available.
