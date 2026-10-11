# NoCap: sequential Codex prompts for Divyam

## How to use

Copy this file and the updated `context.md` to the root of the team's NoCap repository. Run prompts one at a time in order. Each block is independently pasteable and requires a report plus a context update. Run the next prompt after reviewing the previous report; fixture-only completion does not establish live integration. P7 is optional. The earlier `nocap-divyam-codex-prompt.md` is not the specification for this sequence: it contained additional suggestions beyond the PDF baseline.

First finish the Merkle-root function and its tests. This is Divyam's explicit primary responsibility and is consumed directly by the ledger API and dashboard. Next make the ledger/export work; build visual polish on that working path.

## Research and design decisions

| Finding | Application to NoCap | Source |
| --- | --- | --- |
| Layout changes can be animated in React | Smooth selection, panel transitions and updated record lists if the team uses React | [Motion](https://motion.dev/docs/react-layout-animations) |
| Motion can adapt to the device reduced-motion preference | Keep the full interface usable without moving panels or large transitions | [Reduced motion](https://motion.dev/docs/react-use-reduced-motion) |
| Streamlit fragments can rerun independently and periodically | Refresh captures/status without rerunning unrelated inputs where supported | [Streamlit](https://docs.streamlit.io/develop/api-reference/execution-flow/st.fragment) |
| Transform and opacity avoid many layout/paint costs | Favor short fades/translations; inspect dropped frames and expensive paints | [web.dev](https://web.dev/articles/animations-guide) |
| Milestones benefit from explicit deliverables and validation | Every prompt ends with checked evidence, a report and updated project memory | [OpenAI](https://developers.openai.com/blog/run-long-horizon-tasks-with-codex) |

The aesthetic and timings below are design recommendations for Divyam's new request, not findings claimed by these sources or requirements in the PDFs. Preserve a working frontend; no framework migration is required by this sequence.

## Prompt 1 — primary deliverable: Merkle root

```text
Read repository-root context.md first. Treat it as the project brain: preserve its PDF baseline, use Current implementation state and Change log to resume, and follow its reporting workflow. Inspect the actual repository, applicable AGENTS.md, working tree, dependencies and existing tests. Do not overwrite teammates' changes. Record any disagreement between documented status and actual code.

Complete P1 only: Divyam's ledger/merkle.py and tests. Match merkle_root(hashes: list[str]) -> str | None and the exact supplied algorithm in context.md. Keep the existing API import compatible. If already implemented, verify it and repair only necessary defects. Add the two required tests: repeated inputs produce the same root, and a changed input hash changes the root. Also check the documented empty, single-leaf and odd-layer behavior with fixed expected values, not expectations calculated by the function under test. Do not add an alternative hashing scheme, inclusion-proof system, blockchain work or frontend redesign.

Run the relevant tests. Check the import used by cloud/api.py if present. Record the existing frontend stack and exact available launch commands for later prompts; do not change it now. If the repository is empty, create only the minimal ledger module/test setup needed and record missing teammate components.

Before finishing: save reports/P1-merkle.md; update context.md Current implementation state and P1 status; check off only verified baseline items; append a timestamped P1 change-log entry with files, actual commands/results, decisions, blockers and next step. Report complete/partial/blocked honestly. End with the report link, test results, and whether P2 is ready. Do not implement P2 in this run.
```

## Prompt 2 — working audit ledger and export

```text
Read context.md as the project brain and the P1 report. Inspect the code and preserve teammate work. Complete P2 only, following the context.md reporting workflow.

Connect Divyam's ledger work to the existing dashboard's Audit ledger view. Use the active frontend stack. If no dashboard exists, start the supplied Streamlit dashboard approach with this ledger view; keep the four-view structure available for subsequent milestones. Consume Avishkar's GET /ledger response: records, merkle_root, anchor_tx, and where implemented chain_ok/chain_msg. Do not silently invent missing fields or claim chain integrity when the endpoint supplies no chain result.

Display record count, chain status/message, Merkle root, and any supplied Etherscan transaction link. Make the JSON download work as nocap_ledger.json. Use NOCAP_API configuration consistent with the existing project. Do not implement anchoring yet. Provide loading, empty, request-failed and malformed-response states without reporting success on errors.

If the live API is absent, use an explicit fixture adapter behind the same client interface, label fixture mode visibly, and document what live integration remains. Do not replace Avishkar's service or silently switch modes after a failure.

Verify a populated ledger, empty ledger, backend failure and exported JSON contents. Run live checks if available and distinguish them from fixtures. Save reports/P2-ledger.md; update context.md state, tracker and evidenced checkboxes; append the timestamped change log including commands/results, files, API coverage and next action. End with report and context links and P3 readiness. Stop after P2.
```

## Prompt 3 — polished visual foundation

```text
Read context.md as the project brain and prior reports. Complete P3 only. Preserve functional P2 behavior and Bhargav's dashboard ownership. Use the actual installed stack: keep Streamlit if that is the active app; keep React/Next.js if that is active. Do not migrate frameworks or change backend contracts.

Create a polished research-integrity workspace for the existing four views: Live captures, Verify a file, Citation check, Audit ledger. This is a functional application, not a marketing landing page. Reuse existing components and assets where possible. Preserve the PDF's dark-first identity, lime #C8F53B accent, red failure, amber review and monospace hashes.

Proposed visual specification for the new user request: charcoal canvas #0B0F12, raised panels #141A1F, borders #2A343D, primary text #F4F7F8, secondary text #A8B2BC. Use a clean sans font available locally, 16px body text, clear 28–32px page headings, consistent spacing and 12–16px panel radii. Lime buttons use dark readable labels. Check contrast in rendered states.

Build a compact NoCap / Proof, not vibes. header, four-view navigation with a clear selected state, explicit Live/Fixtures connection indicator, and a dominant content area. Captures pair thumbnails with metadata; verification pairs an upload area with a result panel; citations show readable rows and expandable reasons; the ledger highlights chain status, root and download. Avoid excessive tiny cards and raw-JSON-first presentation. Full hashes remain accessible via expansion/copy with working feedback. Do not create unsupported analytics or trust percentages.

Keep controls functional where data is available. Unavailable capabilities show a clear disabled explanation, not decorative working-looking buttons. Preserve input and selection across navigation/refresh. Adapt layout at 1440x900, 1280x720 and 390px width. Provide keyboard focus and readable status labels independent of color. Use only basic hover/focus transitions now; P5 adds choreography.

Run the app, inspect the rendered views if browser tools are available, and capture screenshots. If unavailable, mark visual inspection unverified. Save reports/P3-visual-foundation.md, update context.md current stack/design decisions and milestone status, and append the timestamped change log with files and checks. End with screenshots/report links and P4 readiness. Stop after P3.
```

## Prompt 4 — functional interactions and API states

```text
Read context.md as the project brain and previous reports. Complete P4 only, preserving the P3 appearance and the existing API contract. Inspect existing functionality first; fill gaps rather than duplicate it.

Wire Live captures to GET /captures and GET /captures/{id}/file; Verify a file to multipart POST /verify/file; Citation check to POST /reports; Audit ledger to its working P2 adapter. Use one consistent API client/configuration mechanism. Do not reimplement Sanjay's signing, Avishkar's storage or Pranav's verifier. Verifier takeover requires the documented condition to be established, not inferred from a missing endpoint.

Every operation needs clear idle/loading/success/empty/error states as applicable. Prevent duplicate submissions while requests run; keep typed input and selected files stable on unrelated refreshes. Bound request timeouts and surface actionable errors. Show backend verdicts and reasons without broadening them into unsupported claims. Fixture or cached results stay labeled; provider failure never becomes a fabricated successful response. Do not send a file or run a report simply because a page rerenders.

For live refresh, use the backend's existing event mechanism if present. Otherwise use supported partial refresh/polling with cleanup and no overlapping requests; label it accurately. Streamlit st.fragment may be used only if supported by the installed version. Preserve the manual Refresh action. Do not assume a WebSocket endpoint exists.

Verify file upload, citation submission, capture selection/refresh, ledger download, empty datasets, API disconnection and recovery. Test contracts with fixtures where needed; record live coverage separately. Save reports/P4-functionality.md, update context.md state/tracker and evidenced checkboxes, append the timestamped log, and report unresolved teammate dependencies. Stop after P4 and state P5 readiness.
```

## Prompt 5 — smooth, impressive motion

```text
Read context.md as the project brain and previous reports. Complete P5 only. The UI must remain functional while becoming smooth, fancy and polished. Preserve the working layout, data contracts and operation states. Use one coherent motion system; no framework migration.

If React is already in use, use the installed Motion-compatible approach and confirm version-compatible APIs. If Streamlit is active, use scoped CSS and supported components/fragments; do not inject fragile scripts to manipulate undocumented framework DOM. Record any motion limitation honestly instead of forcing a rewrite.

Implement this proposed choreography where the stack supports it:
- Navigation: selected indicator glides over about 180ms; content fades with a small 6–10px translation over 180–220ms, without delaying interaction.
- Capture selection: thumbnail/inspector transition over 200–250ms; keep stable item identities. A newly received capture gets a one-time subtle emphasis rather than replaying the entire list animation on every poll.
- Upload: immediate hover/drop feedback; show actual upload/verification state. Use indeterminate loading unless real progress exists.
- Result reveal: a brief 250–350ms transition into the backend's actual verdict, followed by its reason. No random counters, fake scanning stages or success before the response.
- Citation rows: at most a small 30ms stagger for the first few newly arriving rows; avoid long delays on large lists. Expand reasons smoothly where supported.
- Audit view: emphasize an actual updated root/status once. An optional simple record-to-root illustration must reflect the displayed records and be labeled an illustration; do not suggest new inclusion-proof functionality.
- Buttons and copy/download feedback: 120–160ms hover/press feedback; never report a completed download when only export preparation is known.

Prefer transform/opacity. Avoid page-wide animated blur, perpetual particles, scroll hijacking and repeated layout recalculation. Respect prefers-reduced-motion by replacing spatial motion with immediate state updates or short fades. Keep focus and keyboard behavior correct; status announcements should not repeat on every poll. Animations must not delay network requests or make results inaccessible.

Inspect rapid tab switching, repeated selections, long lists, request failure, reduced-motion mode and narrow layout. Profile representative transitions if tools allow, recording environment and measurements; do not claim 60fps without evidence. Fix visible flicker, replaying animations and state resets. Save screenshots and, if supported, a short recording. Save reports/P5-motion.md, update context.md with actual motion choices and limitations, append the timestamped log, and report P6 readiness. Stop after P5.
```

## Prompt 6 — demo validation and completion report

```text
Read context.md as the project brain and every milestone report. Complete P6: validate and repair the implemented scope, without adding features.

Run the relevant ledger tests and frontend checks. Launch the system with the documented commands. Exercise the four-view demo twice: captures appear with supplied status; an original/edited file comparison through Verify a file produces the backend's actual results; the prepared citation example shows returned statuses/reasons; Audit ledger shows its actual root/chain status and downloads valid JSON. Verify the exact downloaded file content. Use the team's existing demo assets; clearly identify fixtures/cached reports when live dependencies are unavailable.

Inspect at 1440x900, 1280x720 and 390px width; test keyboard navigation, reduced motion, slow responses, empty data and API failure/recovery. Check input preservation and no repeated submissions on rerender. Repair regressions within scope. If browser tools or live dependencies are unavailable, state which checks remain unverified and keep the corresponding milestone partial.

Provide exact setup/run commands and a concise demo script based only on working features. List remaining issues and whether the demo is ready for live integration or only a fixture rehearsal. Do not claim deployment, hardware integration or blockchain confirmation without evidence.

Save reports/P6-demo-validation.md. Update context.md current state, milestone tracker, confirmed completion checkboxes and remaining blockers. Append a timestamped log entry with files, checks and outcomes. End with the report link, verified demo path and remaining work. P7 is optional and should not run automatically.
```

## Prompt 7 — optional Sepolia stretch

```text
Read context.md as the project brain and the P6 report. Implement only the documented Sepolia stretch work, keeping the working local demo usable.

Inspect any existing ledger/anchor.py. Complete anchor_root(root_hex: str) -> str and integrate with the existing POST /ledger/anchor contract using the team's documented testnet approach. Use only server-side SEPOLIA_RPC and SEPOLIA_KEY configuration and a throwaway testnet wallet; never expose keys in the frontend, context, reports or logs. Check current network/library compatibility before calling external services. Missing credentials are a documented blocker, not grounds to fabricate a transaction.

Add the dashboard anchor action with disabled/in-flight/error handling to prevent accidental duplicate submissions. Display the real returned transaction hash/explorer URL. Distinguish submitted from confirmed; if confirmation is not checked, say submitted. Associate the displayed transaction with the root that was submitted. Use a real earlier transaction only for its matching snapshot. Do not create a mainnet transaction or use real funds.

Run mocked RPC success/failure checks first. A live transaction may run only when a configured throwaway testnet wallet and user authorization are established; otherwise finish the code and document the missing live step. Record whether the pre-demo anchor requirement has actually been met.

Save reports/P7-sepolia.md; update context.md tracker, current state and evidenced stretch checkboxes; append a timestamped log including test outcomes and live status without secrets. End with report link and remaining steps. Do not expand into verifier work.
```

## Required report/log shape

Each prompt should produce the following information in its report and a concise corresponding append-only entry in `context.md`:

```markdown
### Pn — YYYY-MM-DD HH:MM timezone
- Status: complete / partial / blocked
- Requested scope:
- Implemented changes and reasons:
- Files changed:
- Commands/checks actually executed and results:
- Evidence: screenshots, test output, export checks, etc.
- Data coverage: live / cached / fixtures / unverified
- Decisions and deviations from the plan:
- Remaining issues/dependencies:
- Next action:
- Report: reports/Pn-name.md
```

No implementation milestone was executed when this prompt pack was authored. Its initial status is intentionally “Not started” in context.md.
