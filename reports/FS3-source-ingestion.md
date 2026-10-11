# FS3 — Source capture / signing / AWS integration

Date: 2026-10-11. Based on main f3f1cb4, including Sanjay's signing module.

Implemented:

- Default ingestion verification now calls `signing.adapter:verify_record`.
- The API image includes signing source; CI runs its three independent suites.
- JPEG/PNG and MP4 receive basic media inspection, 50 MiB capture limits, hashes,
  private storage and workspace preview support. Manuscript limit remains 25 MiB.
- Lab label, experiment, sample and notes are validated, persisted, displayed and
  available for report evidence linking; annotations are explicitly unsigned.
- Signed uploads retain immutable IDs and retries. File-only gateway uploads are
  hashed receipts with UNSUPPORTED provenance, never fabricated signatures.
- Device transport no longer depends on an unavailable gateway heartbeat route;
  it supports private token files and checks returned file hashes when supplied.
- S3 bucket configuration supports S3_BUCKET and the deployment's legacy
  S3_BUCKET_NAME spelling. Existing encrypted private-object transport is retained.

Validation:

- Main suite: 175 passed, 7 subtests; existing upstream deprecation warnings only.
- Signing suites: 82 checks across signing, synthetic and integration scripts.
- Local tests cover exact 50 MiB acceptance / one-byte-over rejection, actual
  generated MP4 decode, image labels and original download, access isolation,
  Sanjay-produced signature → API → private S3 SDK substitute → verifier,
  signed retry immutability and deployed-style file-only transport.
- Live HTTPS /health: 200. Missing-token multipart PNG: 401.
- Live device-token uploads: PNG, JPEG and MP4 each returned 200, a capture ID and
  an S3 key. All returned SHA-256 hashes matched the submitted bytes.
- Live /me, /integration, /docs and /openapi.json: 404. GET /captures: 405.
  Capture detail/original routes: 404. This gateway is not yet the workspace API.
- Live S3 read-back, lab annotation persistence and dashboard synchronization are
  not established by those upload acknowledgments. EC2 deployment access is still
  required to update the running service. No production configuration was changed.

Only three small, explicitly synthetic test files were sent to the remote gateway.
The supplied device credential is kept in ignored owner-only runtime storage and
is absent from source, reports, commit content and visible test output.
