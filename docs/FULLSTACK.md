# NoCap full-stack integration base

Current entry point: public landing page → sign-in → workspace. UI-R2 follows the
inspected MeghyanAI landing, login and dashboard with NoCap content, a quiet sidebar,
white pill actions, dark panels, and restrained lime accents. Streamlit remains the
frontend. The previous dashboard-only decision is historical and superseded by the
latest request for a landing page plus dashboard. No decorative dots, bulbs or mandala.

There is no Devices tab or enrolled-device metric. Settings reads one configured
source. Set `NOCAP_DEVICE_ID` on the dashboard server to select the actual enrolled
source. Without it, exactly one enabled non-fixture source is selected; ambiguous
physical sources are not guessed. The existing synthetic-generator can illustrate
local settings. Historical enrollments and evidence are preserved; the API's legacy
device registry and token/revocation contracts are unchanged. Device administration
is an operator/API concern rather than a fleet-management screen.

## Run the complete local product

```bash
cd /home/divyamarorakkr/Compiled
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt -r requirements-cloud.txt
.venv/bin/python scripts/run_local.py
```

Product: http://localhost:8501 → Sign in → Open local demo. OpenAPI: http://localhost:8000/docs.
The launcher binds the dashboard to 0.0.0.0:8501 for IDE forwarding and the API to
127.0.0.1:8000. It creates synthetic demo rows only once and persists subsequent
changes under `.runtime/`. Ctrl+C stops both processes. For strictly loopback UI:

```bash
NOCAP_UI_ADDRESS=127.0.0.1 .venv/bin/python scripts/run_local.py
```

Local mode uses a random administrator token in `.runtime/local.env`, mode 0600.
It is read only by the server processes, not placed in source/URLs. It deliberately
opens a shared demo administrator session for local testing. Do not publish this
demo server. Other sessions see persisted changes after refresh/navigation.
Member cards use project-team first names and synthetic example.test addresses;
these are seeded demo memberships, not evidence that those people signed in.

## What to test

1. Overview: actual counts, review queue and persistent activity from the API.
2. Team workbench: create a review, assign an owner, change status, comment;
   People & collaborators lists workspace memberships. Admin can add membership
   records. No email is sent; adding a member does not issue a login credential.
3. Settings: inspect the single configured source, its last contact and signing-key
   configuration. Heartbeat receipt is not hardware authentication. No enrollment
   tokens or fleet controls appear in the product UI.
4. Evidence studio: original/edited file comparison, prepared fictional citation
   examples, media previews and exact ledger JSON export. Capture pages use stable
   ingestion sequence cursors, 100 records per page.
5. Settings: see active adapters, database query result, and missing
   signing/verifier integrations. Configuration does not imply successful AWS use.

To exercise the direct-device transport locally:

```bash
.venv/bin/python scripts/simulate_device.py
```

This creates a **synthetic, unsigned** source, POSTs a heartbeat and an original
file with its record, persists it, and reports UNSUPPORTED. Refresh Evidence studio. Source details live under Settings. The simulator is loopback-only and does not build the hardware
or invent Sanjay's signing canonicalization.

## Service boundaries and storage

Device -> authenticated HTTPS FastAPI -> private original storage + metadata DB.
Dashboard -> authenticated FastAPI only. Dashboard/device never connect to RDS or
receive S3 credentials. Boto3 uses the standard workload credential provider chain;
use an EC2 instance role, not long-lived keys in application configuration.

`cloud/db.py` contains organization-scoped tables: organizations, members,
access_tokens (SHA-256 token digests only), devices, captures, reports, work_items,
comments, audit_events. Capture payload is immutable; filenames never form the
object key. Local files use exclusive writes; S3 uses random opaque org-prefixed
keys with AES256 server-side encryption. API download authenticates organization
access and rechecks SHA-256 before returning bytes. No public ACL or presigned
URL is issued by this implementation. S3 Block Public Access, IAM policy,
versioning, backups and lifecycle remain infrastructure-owner configuration.

Authentication takes a bearer token; tenant identity comes from its DB row, never
from user-supplied organization headers. Members are admin/reviewer/collaborator.
Only admin manages members/devices. Reviewers/admin approve; collaborators update
only their own assignments. Work updates require the current version and fail
409 on a concurrent edit. All reads/mutations are scoped to the principal's org.
The base supports expiring per-member tokens and a production-mode sign-in screen;
SSO/OIDC, invitation emails, recovery/MFA and an external identity-provider lifecycle
are integration work, not implemented claims. Device tokens are revocable and
must be rotated by the hardware operator (register a replacement, revoke old).

## API and migration contracts

Existing capture/report/ledger shapes remain usable. Additions:

| Endpoint | Behavior |
|---|---|
| GET /me, /summary, /integration | Principal, SQL-derived counts, adapter readiness |
| GET/POST /members | Org roster / admin creates a membership record |
| GET/POST /work-items | Paginated reviews / create assignment |
| PATCH /work-items/{id} | Versioned status/owner update |
| GET/POST /work-items/{id}/comments | Persistent discussion |
| GET /activity | Latest org events; after sequence and limit |
| GET/POST /devices | Registry / token returned once at enrollment |
| POST /devices/{id}/heartbeat | Matching device token only |
| POST /devices/{id}/revoke | Admin disables device and its tokens |
| POST /captures | Matching device token, multipart file + JSON record string |
| GET /captures | List, default 100, max 500, `after` sequence cursor |
| GET /captures/{id}/file | Original bytes, authenticated and digest checked |
| POST /verify/file | Registry byte comparison; UNSUPPORTED for unverified matches |
| POST /reports, GET /reports/{id} | Stored citation reports via plugin or explicit fixtures |
| GET /ledger | Stable ordered snapshot and real SHA-256 Merkle computation |
| POST /ledger/anchor | Explicit 503 until durable API orchestration is integrated |
| GET /pubkey?device_id=... | That org device's enrolled public key; 404 if absent |

`UNSUPPORTED` is an explicit proposed extension of the file/capture verdict
contract. It avoids calling an unsigned accepted upload VERIFIED. `/pubkey` now
requires a device ID because there can be multiple enrolled keys. Both changes
are documented for owner review; they are not attributed to the baseline PDF.

Capture validation: strict IDs/hashes, UTC timestamp, supported record type,
exact original-file digest, max 25 MiB, 64 KiB multipart overhead, and device
binding. Signed field strings are preserved. A signing adapter must verify the
canonical record hash AND signature. Per-device head updates use compare-and-swap
in the DB transaction. Same ID + exact payload retries return the existing result;
changed ID payloads or chain heads return 409. Client retries only temporary
failures and preserves the original ID/bytes. A concurrent same-ID race may return
409; retrying that same immutable request after reconciliation is safe.

S3 and SQL cannot commit atomically. If a definite DB failure occurs, cleanup is
attempted. If commit acknowledgement is lost, a separate query checks whether the
row committed; if the DB is unreachable, original bytes are retained and the API
returns 503 with unknown outcome. Audit logs contain IDs, not credentials/content.
A scheduled orphan reconciliation/retention worker is still required in production.

Migrations are explicit, never performed on server import/startup. `0001` freezes
the current initial schema. Local demo bootstrap creates only local SQLite tables;
it is blocked for PostgreSQL. Back up, review the migration and obtain the team's
approved target before applying it to shared RDS. Nothing here has modified RDS.

## AWS configuration and handoff

The supplied AWS guide records RDS PostgreSQL 18.3 `nocap-db`, us-east-2, single AZ,
db.t4g.micro/1 GiB as available in its source screenshots. Those are document facts,
not a fresh AWS inspection. The hostname and credentials are not supplied. EC2,
private S3, IAM roles, database principal/schema, TLS ingress and network paths
remain unverified. No infrastructure was provisioned, and no AWS charge was incurred
by this work.

On the API host, inject these through your approved secret/runtime mechanism:

```bash
export NOCAP_BACKEND_MODE=live
export DATABASE_URL='postgresql+psycopg://<app-user>:<url-encoded-password>@<rds-endpoint>:5432/<approved-db>?sslmode=verify-full&sslrootcert=/run/certs/global-bundle.pem'
export NOCAP_STORAGE=s3
export S3_BUCKET='<private-bucket>'
export AWS_REGION=us-east-2
export NOCAP_SIGNING_PLUGIN='team_signing_adapter:verify_record'
export NOCAP_VERIFIER_PLUGIN='verifier:verify'
```

After the owner approves the migration target:

```bash
.venv/bin/alembic upgrade head
.venv/bin/python -m cloud.manage create-org --name 'Your organization' --admin-name 'Administrator' --admin-email 'admin@example.org' --output /secure/admin-token.txt
.venv/bin/uvicorn cloud.server:app --host 127.0.0.1 --port 8000 --workers 2
```

Run behind approved HTTPS ingress. RDS must have a secure VPC route and port5432
restricted to the app security group. `verify-full` and `sslrootcert` are enforced;
do not disable TLS verification to work around a connection failure.
`Dockerfile.api` is an optional API image specification, not a tested/deployed image.
Workers each use a bounded 5+5 PostgreSQL pool; tune combined connections to RDS
capacity. Current micro/single-AZ evidence is not a high-availability architecture.

Signing plugin signature:

```python
def verify_record(record: dict, public_key_pem: str) -> bool:
    # Owner-supplied implementation must check exact canonical record hash,
    # device signature, key format and trust enrollment. Only True accepts.
    ...
```

The application imports that trusted server-configured function. No plugin path
comes from a request. Exceptions yield 503; False yields 422. Missing signing
fails closed in live mode. Citation plugin `verify(text)` returns the shared list
of findings and is schema-validated. No AI backend is fabricated. Whole-chain
verification and durable Sepolia orchestration are still owner integrations;
ledger always reports chain_ok=null until a real audit is connected.

On the dashboard host (no DB/S3 credentials):

```bash
NOCAP_MODE=live NOCAP_SERVICE_DEMO=0 NOCAP_API=https://<approved-api-host> .venv/bin/streamlit run dashboard/app.py --server.address 127.0.0.1 --server.port 8501
```

Each browser session signs in with its own workspace token. The local demo token
is not used in this mode. For a newly created member, the operator can issue or
revoke tokens on the API host:

```bash
.venv/bin/python -m cloud.manage issue-token --org <org-id> --member <member-id> --hours 24 --output /secure/member-token.txt
.venv/bin/python -m cloud.manage revoke-tokens --org <org-id> --member <member-id>
```

No emails are sent. Deliver credentials through your existing approved secure
channel. Token files are created exclusively with mode0600, never printed.

On an actual device, use its enrolled token and the record produced by the team's
capture/signing module:

```bash
export NOCAP_API=https://<approved-api-host>
read -rsp 'Device token: ' NOCAP_DEVICE_TOKEN
export NOCAP_DEVICE_TOKEN
python -m device.upload --record signed-record.json --file original.jpg
```

## Scale boundaries and outstanding production work

Implemented: stateless authenticated API handlers, DB-backed identity/permissions,
indexed tenant/digest/sequence lookups, bounded pages and body sizes, bounded DB
pool, optimistic review locking, atomic device head comparison, immutable uploads,
private object adapter, explicit migrations and no automatic fixture fallback.

Not claimed: load-tested throughput, autoscaling, HA database, zero-loss queue,
background AI jobs, distributed rate limiting, WebSocket fanout, fine-grained
paper/project ACLs within one organization, SSO or security certification.
Ledger snapshot/export is synchronous and capped at 10,000 records; move larger
exports to an immutable background snapshot job. Reports currently run synchronously;
slow verifiers need a job queue and status endpoint. Member/device lists cap at500,
comments at500, work pages at100; expand their pagination for larger organizations.
Streamlit uses per-session server state; multiple UI replicas need appropriate
session routing. Refresh-based collaboration has no presence/cursor synchronization.
Operator bootstrap uses a shared DB transaction but token-file delivery is a
separate side effect; reconcile unused files on a failed transaction.

## Validation

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pip check
```

Current UI-R2 browser checks mutate **only the local demo**, adding a labelled
acceptance review/comment and a prepared fixture report. See reports/UI-R2*. The
older scripts/inspect_fullstack.py and snapshot_dashboard.py document FS1 and still
expect its retired five-section UI; do not use them as current acceptance commands.
Mock S3 tests establish adapter call behavior only; real RDS/S3/network/device
acceptance and a production load/security review remain outstanding.

Official references consulted: [FastAPI SQL databases](https://fastapi.tiangolo.com/tutorial/sql-databases/),
[RDS PostgreSQL TLS](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/PostgreSQL.Concepts.General.SSL.html),
[Boto3 credentials](https://docs.aws.amazon.com/boto3/latest/guide/credentials.html).
