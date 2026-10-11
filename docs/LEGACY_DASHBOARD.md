# Historical dashboard handoff (superseded by ../README.md and FULLSTACK.md)

# NoCap — Proof, not vibes.

Divyam's SHA-256 Merkle module and Streamlit evidence workspace. This repository
contains the ledger, dashboard, adapters, deterministic demo assets and tests.
It does not implement the team's API/database, signing system, hardware or AI
verifier. **Default data is synthetic; no live verification is implied.**

## Setup and run

Python 3.11+ (validated here with Python 3.14.4 on Linux). From this folder:

```bash
cd /home/divyamarorakkr/Compiled
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
NOCAP_MODE=fixture .venv/bin/streamlit run dashboard/app.py --server.address 127.0.0.1
```

Open http://127.0.0.1:8501. For the exact validated dependency versions, install
`requirements-lock.txt` instead. Runtime-only dependencies are in
`requirements.txt`. Settings are behind the sidebar toggle at the upper left.
Stop with Ctrl+C. Restart the server after adding/changing imported modules if
the development watcher retains stale imports.

## Live API configuration

```bash
NOCAP_MODE=live NOCAP_API=http://localhost:8000 .venv/bin/streamlit run dashboard/app.py --server.address 127.0.0.1
```

Replace localhost with Avishkar's reachable API address. Alternatively copy
`.env.example` to `.env` and edit it; environment variables take precedence.
Never commit `.env` or Streamlit secrets. Fixture/live mode is explicit; a
failed live request produces an error, never fixture results.

The client consumes `GET /captures` as a list with the documented capture fields
and a `status`, `GET /captures/{id}/file`, multipart `POST /verify/file`, JSON
`POST /reports` (`text`, `capture_ids`), and `GET /ledger`. It validates returned
shapes. Ledger records must be a list, `merkle_root` a SHA-256 hex or null,
`anchor_tx` a transaction hash or null; missing chain results remain unknown.
IDs in media paths are escaped. Connect/read timeouts: 3.05/20 seconds. Uploads
and downloaded previews are bounded to 25 MiB. Authentication was not specified
in the team contract; authenticated deployments require an agreed adapter
extension. No private service credentials are exposed in UI error messages.

## What works locally

- Four native tabs: capture/media inspection, explicit file verification,
  citation submission and reasons, audit ledger and exact JSON export.
- Synthetic original/edited comparison and prepared fictional citation reports.
  Fixture mode rejects arbitrary citation text. Every simulated verdict is labeled.
- Manual refresh and optional 10-second capture fragment polling; no assumed
  WebSocket endpoint. Inputs persist while tabs and capture refresh are used.
- Empty, disconnected, malformed, slow, recovery and 60-record fixture scenarios.
- Export is `nocap_ledger.json` and preserves all received fields. The displayed
  Merkle root is not proof that signatures or chain integrity were verified.
- Repeated successful file/text submissions reuse their response for identical
  inputs in the session. Browser reload starts a fresh check. Failures can be
  explicitly retried. Changing scenario invalidates response caches.

Use [demo/README.md](../demo/README.md) for the exact rehearsal. Both filenames
`paper_real.txt` and `photo_ai_edited.jpg` follow the original plan; the files
are fictional text and a deterministic graphic edit, not real scholarly data
or an AI-edited photograph. `signature` fields are empty, not fabricated keys.

## Validation

```bash
.venv/bin/python -m pytest -q
# With the app running, and Chrome installed:
CHROME_BIN=/usr/bin/google-chrome .venv/bin/python scripts/inspect_ui.py
```

The browser check exercises the full demo twice, compares downloaded JSON with
the adapter, and saves evidence under `reports/`. It uses only localhost.
`CHROME_BIN` can point at another installed Chromium-compatible binary.

## Visual and accessibility decisions

The current UI follows the user-selected [MeghyanAI reference](https://meghyanai.com/):
near-black canvas, large system typography, white pill buttons, fine-bordered
cards, segmented navigation and an adapted decorative radial SVG. NoCap lime
marks status and focus. The reference's commercial claims and metrics are not
used. The latest user direction supersedes the earlier Liquid Glass visual
foundation; its original research and screenshots remain in historical reports.

Supported Streamlit theme options and keyed containers scope CSS. Native widgets
preserve keyboard semantics; no app scripts manipulate framework DOM. Short
opacity/movement reveals reflect actual responses. System reduced-motion/contrast
settings and explicit motion/transparency toggles are supported. Evidence stays
opaque. This adapts the reference components to Streamlit's native forms and tabs;
it is not a pixel-identical implementation of the reference site's framework.
See [UI-R1 report](../reports/UI-R1-reference-redesign.md) for current screenshots.

## Ownership and status

See [context.md](../context.md) for the preserved PDF baseline, subsequent user
requirements, current milestone tracker and full append-only history. Reports
are in [reports/](../reports/). Hardware capture, signing, live API/verifier results
and a real Sepolia anchor remain external integration work unless a report
explicitly records live evidence. Nothing has been deployed, pushed or merged.

## Optional Sepolia anchor (P7)

Install only on the server that will sign (development tests already include it):

```bash
.venv/bin/python -m pip install -r requirements-anchor.txt
```

On **Avishkar's API host**, put `SEPOLIA_RPC`, `SEPOLIA_KEY` and
`SEPOLIA_THROWAWAY=1` in its private `.env`. Use a disposable wallet funded only
with free Sepolia test ETH. Values are intentionally absent from this repo.
`ledger.anchor.anchor_root(root_hex)` returns the submitted transaction hash for
`POST /ledger/anchor`; it checks RPC chain ID **11155111**, signs a zero-value
self-transfer with the root in data, uses pending nonce and a padded gas estimate,
and caps gas price at 50 gwei. HTTP provider retries are disabled. No contract
or mainnet transaction is created. Missing configuration fails before broadcast.

For a configured throwaway wallet, the standalone server-side entry point is:

```bash
# Paste the real 64-character root from the intended snapshot:
read -r ROOT_HEX
.venv/bin/python -m ledger.anchor "$ROOT_HEX"
```

Enable the dashboard action only when the teammate's Sepolia endpoint is ready:

```bash
NOCAP_MODE=live NOCAP_API=http://localhost:8000 NOCAP_ENABLE_ANCHOR=1 \
  .venv/bin/streamlit run dashboard/app.py --server.address 127.0.0.1
```

The dashboard sends the documented bodyless POST; it never receives a wallet
key. The action is disabled in fixtures, for empty/already-anchored snapshots,
and after an attempt in the session. Submitted and confirmed are distinct.
The baseline API response does not echo the anchored root, so the UI records
the requested snapshot but explicitly marks association unverified. An optional
`merkle_root` response field can identify the root the API actually submitted;
this is an adapter extension, not a silently changed baseline contract.

API-owner handoff: compute and freeze a ledger snapshot, call `anchor_root`,
persist its `(root, tx_hash)` atomically, and make the endpoint idempotent across
workers/restarts. The module's duplicate protection is process-local only.
After an ambiguous broadcast error, reconcile the locally derived transaction
hash on Sepolia before retrying; the module and UI do not automatically retry.
Before a live demo, check receipt success and transaction input/root and save
the matching snapshot. **No live anchor or confirmation was performed here.**
