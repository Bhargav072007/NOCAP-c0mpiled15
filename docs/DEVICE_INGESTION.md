# Source → hashing/signing → API → private S3 → workspace

## Deployed endpoint check (2026-10-11)

`https://nocap.18-119-159-67.sslip.io/health` returns HTTP 200.
An unauthenticated multipart PNG POST to `/captures` returns HTTP 401, as expected.
`/me`, `/integration`, `/docs` and `/openapi.json` return 404; GET `/captures`
returns 405. This is currently a file-ingestion gateway, **not the full workspace
API from main**. Do not point dashboard sign-in at this host until the workspace
routes are deployed. Authenticated PNG (2,333 bytes), JPEG (3,047 bytes) and MP4 (2,625 bytes)
test uploads returned HTTP 200, capture IDs and S3 object keys. All three returned
SHA-256 values matched locally computed hashes. Capture detail/file routes return
404, so S3 read-back, saved labels and dashboard visibility remain unverified.
Only explicitly synthetic test media was sent; no research specimen was uploaded.

## Supported paths in this repository

1. **Signed source (recommended for provenance):** use Sanjay's `signing.record`
   to create a record, upload `file` plus `record`, and optionally `metadata`.
   The API recomputes the file SHA-256 and calls `signing.adapter:verify_record`
   against the enrolled Ed25519 public key. Chain heads update atomically.
   No server private signing key is needed. The signing adapter is now the default.
2. **File-only gateway compatibility:** upload JPEG/PNG/MP4 as `file` with the
   source bearer token. The API generates a receipt/hash with an empty signature
   and UNSUPPORTED provenance status. Its timestamp is receipt time, not proven
   capture time. This is accepted only for sources without an enrolled signing key;
   a signed source must include a signed record. Do not mix unsigned receipts into
   an established signed chain. File-only uploads are not automatically retried
   because the external gateway does not document an idempotency contract.

Source uploads and original previews support 50 MiB. Manuscript uploads remain
25 MiB. JPEG/PNG structure and dimensions are inspected (40 megapixel cap). MP4
container and first-frame decoding are checked. Media metadata reports precisely
what was inspected; no OCR, object classification or scientific video assessment
is claimed. The verifier can compare linked photos and check video provenance;
video-content review remains a human task.

Optional multipart `metadata` is a JSON string with `label`, `experiment_id`,
`sample_id` and `notes`. Fields have size limits and unknown fields are rejected.
These lab annotations are persisted with the capture and displayed in Evidence
studio. They are explicitly **not covered by the device signature**. Labels can
help the manuscript verifier link a figure or dataset. Signed record IDs and
annotations are immutable: retrying a signed ID with changed metadata is rejected.
CSV/JSON lab readings retain the signed-record ingestion path.

## Device setup and transport

Keep these values in a private environment or an ignored `.env`; never in Git:

```dotenv
NOCAP_API=https://nocap.18-119-159-67.sslip.io
NOCAP_DEVICE_TOKEN_FILE=/secure/nocap-device-token.txt
NOCAP_KEY_FILE=/secure/device-key.pem
NOCAP_KEY_PASSPHRASE=your-private-passphrase
NOCAP_DEVICE_ID=the-enrolled-source-id
NOCAP_DATA_DIR=/secure/nocap-chain
```

Use `python -m signing.record` once on the device to initialize its encrypted key
and export the public key for enrollment. **Keep the existing key/chain on a source
that already signs captures.** The public key and device ID must match enrollment.
`signing.record.make_record(path, 'photo')` or `make_record(path, 'video')` produces
the JSON record; save that exact record and retain it for retries.

```sh
# Signed transport to the full workspace backend:
python -m device.upload --file lab.png --record record.json --metadata lab.json

# File-only transport to the deployed gateway (no heartbeat dependency):
python -m device.upload --file lab.png

# Explicit one-file smoke test; reports only status and safe receipt fields:
python scripts/check_upload.py --url https://nocap.18-119-159-67.sslip.io --file lab.png
```

`lab.json` example:

```json
{"label":"Figure 1 control","experiment_id":"EXP-01","sample_id":"A","notes":"Control specimen"}
```

The external gateway may not yet support records/annotations. A 201 alone does
not prove it persisted them. Confirm returned hashes and authenticated workspace
read-back after deploying this implementation.

## AWS receiving and processing

Deploy the updated API image, which includes both `signing/` and `verifier/`.
Set `NOCAP_STORAGE=s3`, `S3_BUCKET` (or legacy `S3_BUCKET_NAME`) and `AWS_REGION`.
Use the instance/task IAM role for `s3:PutObject`, `s3:GetObject`, and
`s3:DeleteObject` restricted to the configured private bucket prefix. Objects use
opaque organization-scoped keys, AES256 server-side encryption and no public ACL.
The backend DB stores labels, media inspection, file/record hashes, signatures,
source ID and object key. Downloads recheck stored SHA-256 before returning bytes.
All signing/media validation happens before S3 writes; failed persistence is
reconciled using the existing ingestion transaction logic.

The reverse proxy must allow slightly more than 50 MiB for multipart overhead
(e.g. a 52 MiB body limit) and route the complete workspace API. Repository code
still enforces the actual 50 MiB file limit. Database identity/storage schema must
match `cloud/db.py`; inspect the existing gateway deployment before migrating or
replacing it. No AWS infrastructure or production schema was changed by this work.

Acceptance after deployment: signed JPEG/PNG/MP4 upload → response hash → original
read-back → matching SHA-256 → persisted label/media metadata → Evidence studio
preview → saved provenance report. Reject missing/invalid tokens, changed bytes,
invalid signatures, malformed media and files above the limit. Unit/integration
tests cover this locally; S3 uses a controlled SDK substitute in those tests.
