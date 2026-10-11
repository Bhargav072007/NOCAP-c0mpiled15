# FS1-A — Full-stack foundation

User scope expansion: persistent dashboard/workbench and device-to-cloud integration base.
Read all eight pages of the AWS guide and rendered page 3. Guide facts are historical
source claims: RDS PostgreSQL in us-east-2 is documented as available; EC2/S3,
networking, credentials and deployed schema remain unverified. No cloud writes made.
Inspected authorized MeghyanAI demo Overview/Studio/Runs/Reports/Admin without
mutating remote data. Screenshots and observed CSS are in reports/reference-dashboard.
No reference credentials or session cookies were saved in project files.

Implemented cloud/config.py, db.py, schemas.py, storage.py, api.py, bootstrap.py,
server.py, explicit frozen Alembic migration, device/upload.py, requirements-cloud.txt,
and local process launcher. Organization-scoped bearer authentication, role checks,
optimistic review versions, assignments/comments, immutable capture IDs, per-device
chain-head compare-and-swap, upload digest checks, bounded request bodies, storage
compensation, private S3 adapter and PostgreSQL TLS guard. Missing signing/verifier
integrations fail closed in live mode; local unsigned ingestion is UNSUPPORTED.
Synchronous ledger has an explicit 10,000-record bound, not a high-scale guarantee.

Checks: compileall passed; local bootstrap succeeded with synthetic rows and random
server-only token in ignored .runtime/local.env mode 0600. Ten new FastAPI integration
and storage/config tests passed. Initial sandboxed TestClient stalled; stopped it
and reran with authorized local event-loop access: 10 passed in 0.68s. One upstream
Starlette/httpx deprecation warning. No live AWS/RDS/S3/hardware, real signature or
AI verification evidence. Next: complete dashboard visual/functional validation,
security regression and integration documentation. No deployment/push/merge.
