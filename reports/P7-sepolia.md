# P7 — Optional Sepolia anchoring

Status: **partial — code and mocked RPC checks complete; live anchor blocked by
absent configured throwaway wallet/RPC**. No transaction was broadcast.

Implemented `ledger/anchor.py:anchor_root(root_hex)` with Web3 7.16.0. It validates
32-byte root hex, requires API-host SEPOLIA_RPC/SEPOLIA_KEY/SEPOLIA_THROWAWAY=1,
checks actual chain ID 11155111, signs a zero-value self-transfer, puts the root
in transaction data, uses pending nonce, estimates gas with a margin, and applies
balance/fee guards. Provider retries are disabled. Submitted hashes return only
after RPC acknowledgement. Errors are sanitized. Ambiguous broadcasts retain
the locally derived transaction hash and block process-local retries. Persistent
idempotency across API workers remains Avishkar's responsibility.

Dashboard POST /ledger/anchor preserves the bodyless baseline contract; keys
are never supplied to browser controls. Fixture/cached/empty snapshots and
unconfigured actions are disabled. Attempt state prevents repeat submission in
the session. Success says submitted, not confirmed. The baseline API does not
return the anchored root; UI explicitly labels snapshot association unverified.
Optional returned `merkle_root` is checked against the requested snapshot and
mismatches are exposed. This optional field is a separately documented extension,
not a rewrite of the source contract.

Files: `ledger/anchor.py`, `tests/test_anchor.py`, `dashboard/client.py`,
`dashboard/ui.py`, `dashboard/app.py`, requirements-anchor/dev/lock,
`.env.example`, `README.md`, browser evidence/script, report/context.

Research before implementation: official [Web3 transaction docs](https://web3py.readthedocs.io/en/v7.7.0/transactions.html)
confirm local signing and `signed.raw_transaction`; [Sepolia network repository](https://github.com/eth-clients/sepolia/blob/main/README.md)
confirms chain ID. Installed v7 code was exercised through mocked JSON-RPC with
real ephemeral local signing; no test private key was stored or logged.

Checks and outcomes:
- `.venv/bin/python -m pytest -q`: **46 passed, 7 subtests passed**.
  Tests include decoded signed transaction data/value/destination/chain/nonce,
  mainnet and other-network rejection before signing, credentials/root/funding/
  fee errors, RPC preparation failure, ambiguous broadcast and duplicate block,
  safe explorer URL validation, UI submitted/error/dedup and fixture disabling.
- `.venv/bin/python -m pip check`: no broken requirements.
- `.venv/bin/python -m compileall -q ledger dashboard scripts tests`: passed.
- Final browser regression: two rehearsals passed again after the changes;
  exact downloaded JSON, error/recovery, three viewport sizes, keyboard focus,
  motion/transparency fallbacks, disabled fixture anchor and a timed 10-second
  polling cycle passed. `reports/P6-browser-checks.json` contains final evidence.
- Inspected final result screenshots. Default glass and disabled-anchor captures
  are `reports/screenshots/final-default-captures.png` and `final-ledger.png`.
- Configuration availability check printed booleans only: RPC false, key false,
  throwaway declaration false. No wallet creation/funding, live RPC, real
  transaction, receipt or confirmation was attempted.

Repairs during final validation: full-scope rerun replaces an invalid
fragment-only rerun in the anchor AppTest path. A rapid replacement/upload
interaction exposed a submit race; native Streamlit form now batches the file
and click, and responses identify the last submitted filename/hash. Final
browser rehearsals confirm original→edited→original comparisons. Fixture or
cached flags from a live API retain provenance labeling and disable anchoring.
Fixture-only scenario controls are disabled in live mode.

One upstream Web3/websockets legacy deprecation warning remains; tests pass.
Native Liquid Glass optics, cross-browser/screen-reader audit and a backup demo
video remain outside the verified evidence. No public deployment/push/merge.

Next external action: API owner connects `anchor_root`, persists root/hash
snapshots idempotently, configures a disposable Sepolia wallet funded with free
test ETH, submits once, and checks receipt/input against the intended root.
Exact setup, live-API and optional-anchor commands are in `README.md`.

## Final handoff audit

Final handoff audit: visually inspected the settled default glass workspace and
ledger screenshot, reread current state/tracker and the P7 entry, and confirmed
that live capture/wallet/confirmed-anchor checkboxes remain open. Updated the
Streamlit lower bound to 1.65 to match the supported form/key APIs tested here.
Added reports/README.md as the evidence index. No application behavior changed
in this audit; no additional test run was needed after this dependency metadata
and documentation-only edit. Last functional result: 46 tests and 7 subtests,
plus both final browser rehearsals, passed. Remaining action: teammate live
integration and throwaway-wallet configuration, as documented in README.md.
