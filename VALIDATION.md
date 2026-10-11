# Hybrid verifier validation

Tested October 11, 2026 with Python 3.12, OpenAI SDK 2.54.0, Qiskit 2.5.2 and live `gpt-4.1-mini-2025-04-14`. The SDK requests strict Responses JSON schemas with `store=False`. These are implementation tests and small real-case checks, not a validated general detector.

## Automated checks

80 tests passed; dependency consistency passed. Tests cover signatures/keys/tampering/anchored chains and tenant scope, statistics and missing pairs, image changes/crops/reuse, parser formats, citation metadata and caching, provider failures and unrelated NGO search hits, retraction notices, OpenAI strict output/storage/error redaction, scientific evidence/source/claim identity, whitespace-only original-span recovery, model-label inconsistencies, bounded repair/abstention, every-column diagnostics, offline network isolation and Grover/batching/index conventions.

## Current live reference checks

| Case | Category | Result |
|---|---|---|
| puppet-1 | academic-fake | NOT_FOUND |
| puppet-2 | academic-fake | NOT_FOUND |
| puppet-3 | academic-fake | NOT_FOUND |
| mata-varghese | legal-fake | NEEDS_REVIEW |
| mata-shaboon | legal-fake | NEEDS_REVIEW |
| mata-peterson | legal-fake | NEEDS_REVIEW |
| mata-martinez | legal-fake | NEEDS_REVIEW |
| mata-durden | legal-fake | NEEDS_REVIEW |
| mata-miller | legal-fake | NEEDS_REVIEW |
| valid-oxfam | ngo-valid | VERIFIED |
| valid-amnesty | ngo-valid | NEEDS_REVIEW |
| valid-rr | academic-valid | VERIFIED |
| retracted-lancet | retracted | RETRACTED |

All three DOI failures are from the exact original-v1 Puppeteers bibliography. The separate live OpenAI bibliography extraction test also returned NOT_FOUND for all three. DOI nonresolution demonstrates an identifier problem, not that the whole work is fabricated or that its authors committed fraud. Cases/source locators and original-version links are in demo/reference_cases.jsonl.

The Oxfam and Reinhart–Rogoff references resolved; the retracted Lancet/Surgisphere paper was marked RETRACTED. Amnesty stayed NEEDS_REVIEW because scholarly indexes did not provide a sufficiently identified match. No hard false flag was emitted for these three valid controls. The six fake Mata case references stayed NEEDS_REVIEW online because CourtListener credentials are absent. This is an unresolved live capability, not six successful fake-case detections. The reviewed local catalog can corroborate those supplied case labels; that is not independent discovery. US parsing/resolution/opinion behavior is separately tested with fixtures. Current good-law status and non-US law were not evaluated.

The resolver benchmark uses independently prepared title/author/year metadata. Only the three original-v1 entries were separately exercised through automatic OpenAI extraction. There is no full-manuscript academic/NGO/legal end-to-end accuracy estimate from this small sample.

## Complete real scientific workflow

The complete default hybrid CLI ran citation extraction and live lookup, source-support judgment, automatic data extraction, local numerical/provenance checks, scientific review and Qiskit together using demo/hybrid_paper.txt and demo/hybrid_context.json.

- OpenAI and the publication lookup verified the NBER reference identity and textual support for the cited abstract sentence. This establishes what the source reports; it does not establish underlying correctness.
- The linked public replication observations recomputed an unweighted mean of **2.167971692398155%**, compared with the original **-0.1%** table value. The numerical discrepancy was flagged DATA_MISMATCH. The rounded replication **2.2%** was numerically consistent but remained reviewable because the data are unsigned.
- The scientific reviewer produced grounded methodology, statistics, reproducibility and limitations concerns; other categories remained evidence-limited. Its judgments always require human review. The final isolated scientific run completed without evidence-validation failures, as did scientific review in the complete workflow.
- Automatic data linking attempted a dataset assignment without an explicit ID/label anchor. The verifier rejected it and used the separately prepared manual links for the actual numerical checks. Automatic linkage is not demonstrated reliable for ambiguous manuscript tables.
- Unassessed columns, incomplete claim coverage, missing signatures and unresolved evidence remain in the report. No paper approval or universal scientific accuracy is claimed.

The difference involves sample/weighting choices and an acknowledged spreadsheet coding error; this program does not isolate/discover the original Excel formula bug or prove causality/fraud. The input combines exact original phrases with an explicitly normalized table transcription; it is a prepared regression case, not blind discovery from the entire original PDF. Published PDF version hashes, source URLs and cached-spreadsheet transformation details are in demo/source_fixture_manifest.json and demo/rr_data_provenance.json.

Early scientific attempts exposed rewritten/inexact quotes and claim formatting. The final scientific schema selects known sentence/passage IDs and the server copies exact original text. Invalid IDs, invalid direct quotations and conflicting positive labels still abstain; one repair is permitted. Failed experiments are not counted as successful accuracy tests.

## Offline and quantum checks

The offline demo keeps 36 references, with 35 explicitly reviewed catalog entries and wb-12 excluded as disputed. It retains all dataset/capture/source/figure inventories and flags. Catalog labels are supplied evidence, so matching them is not a blinded benchmark. The same public numerical discrepancy is recomputed offline.

The four-state Grover regression amplifies one marked finding from 0.25 to approximately 1.0 after one iteration. Larger reports are fully batched, and no classical finding is discarded. This is a local statevector simulation; probabilities refer to search outcomes, not truth or confidence. No quantum hardware or end-to-end advantage was demonstrated.

## Boundaries

Not established: the product's 95% fabricated-citation recall / 5% false-flag target, 85% expert agreement, broad scientific accuracy, automatic fraud discovery, exhaustive independent literature review, advanced or arbitrary statistical methods, real-world image-manipulation detection accuracy, clinical/physics correctness, or legal validity. The independent-search implementation is bounded and fixture-tested, but its research_queries option was not used in these live runs.

Verbose protected audit reports and fetched source texts remain in the workspace. The ZIP includes compact summaries and a source-fixture preparer; original papers and verbose text-bearing audits are not redistributed. Run the documented examples to regenerate full evidence reports. Earlier results in outputs/real-world-validation are historical and should not be combined into a current accuracy score.

### Luminal integration check — 2026-10-11

90 automated tests pass, including ten Luminal adapter tests: provider selection, structured output, local schema rejection, extra fields, truncation, malformed JSON, authentication-error redaction, redirect rejection, JSON-mode fallback, and no retry for unrelated validation errors.

The initial `luminal.cloud` endpoint returned HTTP 401. After the user supplied the dashboard's `https://flash.luminal.cloud/v1` endpoint, authentication and structured generation succeeded. The current pipeline extracted three real invalid original-v1 bibliography entries; all three returned `NOT_FOUND`. This is bibliography-only extraction plus public lookup, not an expert accuracy benchmark or full-paper evaluation.

The first scientific run using the public Reinhart–Rogoff replication fixture returned HTTP 503. The report preserved the local `DATA_MISMATCH` (-0.1% versus computed approximately 2.168%) and marked scientific review incomplete. Luminal scientific accuracy cannot be inferred from that failed model request. OpenAI and offline checks remain available; Qiskit prioritization does not establish scientific truth.

Scientific fixture retry: a second attempt also returned HTTP 503. Scientific assessment remains incomplete; citation smoke testing succeeded. See `demo/luminal_validation_summary.json`.
