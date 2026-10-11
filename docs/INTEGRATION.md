# Frontend and backend integration

The Streamlit workspace calls the authenticated FastAPI service. The service now
runs the bundled `verifier` package directly, using workspace-owned files and
enrolled public keys, and saves the complete result in the existing `reports`
table. No additional database migration is required.

## Run from GitHub

Follow the repository README local launcher instructions. Open the workspace,
then **Research papers** (also available under Evidence studio → Citation check). The default **Offline evidence checks**
option accepts arbitrary pasted text or PDF/DOCX/TXT/Markdown/TeX manuscripts.
An uploaded file takes precedence over pasted text. Limits: 25 MiB manuscript upload, 50 MiB source capture upload,
200,000 extracted characters, 100 selected captures, 500 chain records, and
100 MiB total evidence bytes per review. Scanned PDFs need OCR text first.

Select workspace captures to include their provenance and available CSV/JSON
readings or photo assets. The backend obtains organization scope, originals,
public keys and chain heads from its own authenticated database/storage. All
records for each selected source are checked in order, including predecessors.
There is one source shown in Settings and no Devices tab.

Each response includes simplified UI rows **and** the original verifier audit.
Precise verdicts such as SCIENTIFIC_CONCERN, RETRACTED and NEEDS_REVIEW remain
visible and preserved in JSON. Offline mode performs no provider calls: source
lookup and scientific assessment are not claimed. Coverage gaps remain visible.
Synthetic examples require an explicit demo selection and are disabled on live
backends. A real offline result is not labelled synthetic merely because it runs
in a local workspace; reports identify any synthetic evidence they contain.

Completed reports are stored by organization. Use **Saved research reports** to
reopen one after navigation or restart, and download its full JSON audit.
Manuscript text and audit evidence are sensitive workspace data; exports inherit
that sensitivity. No manuscript or credential is written into Git.

## Enable full research analysis

On the API host, configure private environment variables or an ignored `.env`:

```dotenv
NOCAP_VERIFIER_MODE=hybrid
NOCAP_PROVIDER=luminal
LUMINAL_API_KEY=your-private-key
```

Alternatively select `NOCAP_PROVIDER=openai` and configure `OPENAI_API_KEY` and
`NOCAP_MODEL`. Keep credentials on the server. The local launcher reads `.env`,
then environment overrides, then its private local access configuration. Restart
it after changing provider settings. Deployment processes must inject the same
variables into the API process. Details: [VERIFIER.md](VERIFIER.md).

Full research analysis then appears in the frontend. Choosing it sends the
manuscript/relevant evidence to the configured provider and publication services.
Provider failures produce review-required findings rather than a fabricated pass.
No automatic provider switch occurs. `NOCAP_VERIFIER_QUANTUM=1` optionally enables
the verifier's local Qiskit prioritization simulation; its probabilities are not
scientific confidence scores.

Reports run synchronously; the client allows up to 600 seconds for a report
response. Configure deployed proxy timeouts accordingly. If a request times out,
check saved reports before resubmitting. A durable background job queue and
high-volume scheduling remain future work. Workbench edits and reports use
persisted storage; a long verifier call does not hold an open DB read transaction.

## Endpoint contract

| Method | Endpoint | Body / result |
| --- | --- | --- |
| POST | `/reports` | `{text, capture_ids, mode}` → saved report with results and full analysis |
| POST | `/reports/file` | Multipart file, JSON-string capture_ids, mode → same report shape |
| GET | `/reports?limit=20` | Most recent organization-scoped report summaries |
| GET | `/reports/{id}` | Complete saved report, including text and audit |
| GET | `/integration` | Configured verifier mode and hybrid availability |
| POST | `/captures` | Device-token upload; built-in canonical hash and Ed25519 check for enrolled keys |
| POST | `/verify/file` | Compare uploaded bytes with authenticated stored captures |

Modes are `configured` (server default), `offline`, `references` (up to 12 DOI publication lookups), `hybrid` (server must enable),
and `demo` (local prepared fixtures only). Legacy `NOCAP_VERIFIER_PLUGIN` remains
supported for `configured` requests; explicit offline/hybrid uses the built-in
engine. The legacy adapter cannot claim assessment of linked captures.

`origin/avishkar-backend` at f4952be contains an earlier independent schema and
unimplemented S3 methods. The integration uses the runnable, authenticated
`cloud` service on main and its implemented local/S3 adapters. It does not overlay
that service with the older scaffold or alter the contributor's branch.

## Validation boundary

`tests/test_workspace_verifier.py` runs the real dashboard client against FastAPI
and Segment 3, checks uploads, complete signed chains, saved-report reopening,
tenant/device-token isolation and Streamlit submission/rendering. Hybrid tests
replace external service boundaries with doubles. No fresh paid provider request,
AWS deployment, physical device upload or Sepolia transaction was performed.
