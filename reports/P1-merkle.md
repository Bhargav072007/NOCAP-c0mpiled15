# P1 — Merkle root

Status: complete. Scope: exact build-plan algorithm and minimal test setup.

Implemented `ledger/merkle.py` and compatible import; empty input returns None,
single leaf is decoded/normalized without rehashing, odd layers duplicate the
last leaf. Input ordering is preserved and the caller's list is not mutated.
Changed: `ledger/`, `tests/test_merkle.py`, `tests/__init__.py`, `pyproject.toml`,
`.gitignore`, `scripts/record_milestone.py`, this report and `context.md`.

Checks: `python3 -m unittest tests.test_merkle -v` — **7 tests passed**, including
fixed 2/3/5-leaf vectors, empty/single, changed inputs, invalid hex, and ordering.
Both source files have now been read in full; their saved contents resolve the
first attempt's blocker. No applicable AGENTS.md or application code existed.
Git is not initialized; no teammate code was changed. API import is covered by
tests; `cloud/api.py` does not exist. Live integration: none.

Decision: user authorization to run P1–P7 sequentially supersedes the prompt
pack's per-milestone stops. No verifier takeover is established. Streamlit is
selected per the user's empty-workspace instruction; no frontend is installed
yet, so no app launch command is currently available. P2 will add it.

Next: P2 audit/export and an explicit fixture/live adapter. Missing external
components: API/storage, signing, verifier, hardware, Sepolia wallet/RPC.
