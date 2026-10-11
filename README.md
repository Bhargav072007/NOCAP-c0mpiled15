# NoCap — Proof, not vibes.

A full-stack workspace with a public landing page and sign-in for evidence review, team collaboration and
NoCap device ingestion. Streamlit frontend, authenticated FastAPI, SQLAlchemy
persistence, local files/SQLite for demo, and PostgreSQL/private-S3 adapters for
the team's AWS integration. Dark reference-dashboard layout with restrained
transitions, clear status labels and reduced-motion support.

## Start the complete local demo

```bash
git clone https://github.com/Bhargav072007/NOCAP-c0mpiled15.git
cd NOCAP-c0mpiled15
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt -r requirements-cloud.txt
.venv/bin/python scripts/run_local.py
```

Open **http://localhost:8501** → **Sign in** → **Open local demo**. API documentation: http://localhost:8000/docs.
The dashboard stays on port8501 for IDE forwarding; API stays on loopback8000.
Ctrl+C stops both. Data persists in ignored `.runtime/`; the local demo uses a
random server-side admin token and clearly labeled synthetic evidence.

The four workspace sections are Overview, Evidence studio, Team workbench, and
Settings. There is no Devices tab or fleet counter. Settings shows one configured
NoCap source; set `NOCAP_DEVICE_ID` on the dashboard server when necessary. Reviews support assignment, statuses, approval permissions,
comments and conflict detection. Member additions create records, not emails.
Devices get scoped, revocable upload credentials; never a database password.

Test direct device-to-API transport with an explicitly unsigned local simulator:

```bash
.venv/bin/python scripts/simulate_device.py
```

Refresh Evidence studio. Source connection details are under Settings. The new capture is **DEMO · UNSUPPORTED**,
not falsely reported as cryptographically verified.

## Connect your real API

```bash
NOCAP_MODE=live NOCAP_SERVICE_DEMO=0 NOCAP_API=https://<approved-api-host> .venv/bin/streamlit run dashboard/app.py --server.address 127.0.0.1 --server.port 8501
```

Users sign in with their own expiring workspace tokens. Backend provisioning,
PostgreSQL TLS, S3 role configuration, migrations, signing/verifier plugin
contracts, device upload commands and scale limits are in
[docs/FULLSTACK.md](docs/FULLSTACK.md). No AWS resources or shared DB migrations
were applied. The API now uses the bundled Segment 3 verifier and Ed25519 signature checks.
Physical hardware, AWS acceptance and confirmed Sepolia anchoring remain untested.
See [the frontend/backend integration guide](docs/INTEGRATION.md) for manuscript review and provider setup.

For the original standalone fixtures without an API:

```bash
NOCAP_MODE=fixture .venv/bin/streamlit run dashboard/app.py --server.port 8501
```

Open Evidence studio. Team/device persistence requires the full-stack launcher.
The original ledger/anchor implementation and tests remain intact;
[legacy setup and P7 notes](docs/LEGACY_DASHBOARD.md) record the earlier handoff.
The new backend's anchor endpoint deliberately returns503 until the API owner
connects durable snapshot/transaction orchestration; it never invents a transaction.

## Validation and evidence

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pip check
```

The UI-R2 browser review exercised landing/login, mobile navigation, file comparison,
citation results, review persistence, and a ledger download. Local synthetic data only.
The older FS1 browser scripts retain their historical five-section expectations;
they are not the current acceptance command.
Current evidence: [UI-R2 report](reports/UI-R2-product-interface.md),
[reports index](reports/README.md), and [context.md](context.md), which preserves
source requirements, new user decisions, milestone status and the change log.
This is a tested integration base, not a claim of measured high-scale production
readiness. No public deployment is claimed; source updates are published to this repository.

Public routes use Streamlit query parameters: `?page=home`, `?page=login`, and
`?page=workspace`. A direct workspace URL requires an authenticated session or an
explicit local-demo entry. Sign out clears session state. Production entry validates
a personal token against `/me`; this is not an email/password or SSO implementation.

### Motion update

The interface now includes ten component animations and one continuous colour ribbon.
Use its pause control, or Settings → Display & refresh preferences → Reduce motion.
System reduced-motion preferences are also respected. [Motion report](reports/UI-M1-motion.md).

### Interactive workflow preview

The landing page now has a 3D capture → review → export tour. Select a step, use
arrow keys, or pause the full scene. The preview uses clearly labelled sample data;
**Try the workspace** opens the existing access flow. [UI-M2 report](reports/UI-M2-dynamic-demo.md).

## Segment 3 verifier

The repository also includes the hybrid verifier. See [verifier setup and usage](docs/VERIFIER.md) and [its validation report](VALIDATION.md). Its existing source, tests, fixtures, and dependency lock are preserved. The dashboard now calls the authenticated API for text/document review, linked capture checks and saved full reports. Local client/API/verifier integration is tested; external model calls are separately configured. `requirements.txt` includes both components; the existing lockfiles record their separate validation environments.

Luminal Flash has been reworked and live-tested for the Segment 3 verifier. It defaults to final-answer JSON mode with local schema/evidence validation. See [verifier setup](docs/VERIFIER.md#luminal-provider--reworked-and-live-tested) and [validation](VALIDATION.md). The tested scientific fixture completes; the current dashboard integration has local and mocked-provider coverage, not a new live-provider accuracy evaluation.

## Source images, videos and lab labels

See [device ingestion and AWS handoff](docs/DEVICE_INGESTION.md) for signed uploads,
file-only gateway compatibility, 50 MiB limits, image/video processing and the
current deployed-endpoint verification boundary.
