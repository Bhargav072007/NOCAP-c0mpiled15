# P2 — Audit ledger and export

Status: complete for fixtures and mocked transport; live integration outstanding.
Implemented Streamlit Audit ledger, count/chain message/root, safe Sepolia link,
JSON download, loading/empty/error/malformed states. Missing chain status is
explicitly unknown. Fixture records are unsigned; no signature or chain check
is invented. Live mode uses bounded HTTP timeouts and never falls back.

Changed: `dashboard/app.py`, `dashboard/client.py`, `dashboard/__init__.py`,
`tests/test_client.py`, requirements files, `.env.example`, `README.md`, report
and context. Dependencies installed after sandbox DNS failure required approved
network access. Python 3.14.4, Streamlit 1.65.0.

Checks: `.venv/bin/python -m pytest -q` — 15 passed, 7 subtests passed.
Streamlit AppTest: populated count=3, empty count=0, disconnection displayed;
no runtime exceptions. Unit test verifies exported JSON equals source object
exactly. HTTP success/error/timeout/non-JSON paths tested with mocked transport.
Browser download will be exercised in P6. No Avishkar API is configured.

Run: `NOCAP_MODE=fixture .venv/bin/streamlit run dashboard/app.py --server.address 127.0.0.1`.
Live: `NOCAP_MODE=live NOCAP_API=http://localhost:8000 .venv/bin/streamlit run dashboard/app.py --server.address 127.0.0.1`.
Other views visibly identify pending implementation. Next: P3 visual foundation.
