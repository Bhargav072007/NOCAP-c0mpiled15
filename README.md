# NoCap hybrid verifier — Segment 3

OpenAI or Luminal supplies citation/claim linking and evidence-grounded scientific review. Local Python checks signatures, files, images and explicitly specified statistics. Qiskit runs a local Grover circuit over the resulting review flags. Anthropic is not used.

This implements the analyser described in Product Documentation pages 8–10, with an additional scientific-review layer. It produces evidence and reviewer actions; it does not certify that a paper is true or prove misconduct.

## Run

Use Python 3.12 or newer. From this directory:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

For a fresh installation, copy `.env.example` to `.env` and configure `OPENAI_API_KEY`. Set `NOCAP_MODEL` to an available model supporting strict structured outputs; the tested default is `gpt-4.1-mini`. The current workspace has a local credential configuration. Credentials and the virtual environment are excluded from the ZIP. Original paper texts and verbose audit reports are also excluded; run the fixture preparer and example to regenerate them. Compact validation summaries are included.

```sh
# Prepare public source fixtures on a fresh ZIP installation
.venv/bin/python demo/prepare_public_sources.py

# Complete hybrid example: live A/B, OpenAI data linking/science, local C, Qiskit
.venv/bin/python -m verifier demo/hybrid_paper.txt --context demo/hybrid_context.json --output demo/hybrid_report.json

# Isolate scientific review on real original/replication evidence
.venv/bin/python -m verifier demo/hybrid_science_input.txt --context demo/hybrid_science_context.json --output demo/hybrid_science_report.json --skip-live-citations --skip-data-extraction

# Use Luminal for the complete hybrid example
.venv/bin/python -m verifier demo/hybrid_paper.txt --context demo/hybrid_context.json --output demo/luminal_report.json --provider luminal

# Fully offline local-catalog/data assessment
.venv/bin/python -m verifier demo/paper.txt --context demo/context.json --output demo/offline_report.json --mode offline

.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python demo/run_live_reference_checks.py
```

The live evaluation command uses public services and the selected model provider. Its source metadata are independently prepared; bibliography extraction is separately tested on three actual original-v1 references. See VALIDATION.md. Installation downloads dependencies; optional transcription downloads Whisper weights on first use.

For your paper, replace the demo paths with your PDF/DOCX/TeX/Markdown/text and its context JSON. Add `--assets asset-directory` to extract embedded figures. Use `--domain academic`, `legal` or `mixed`; mixed is the default. `--no-quantum`, `--skip-live-citations`, `--skip-data-extraction` and `--skip-science` explicitly skip those stages and record missing coverage. The CLI and public Python functions default to hybrid; `mode="offline"` explicitly disables network analysis.

```python
from verifier import analyse, analyse_document, verify

report = analyse_document("paper.pdf", context=context, asset_dir="assets")
flags = verify(text, context=context)  # entry point for Avishkar
report = analyse(text, context=context, mode="offline")
```

Missing/broken OpenAI credentials produce review flags while preserving local checks. No missing abstract, failed lookup or API outage is treated as proof that a reference is fabricated.

## What is implemented

| Product requirement | Implementation and boundary |
|---|---|
| Parse and link | PDF/DOCX/TeX/Markdown/text parser, tables/figure extraction, bounded overlapping text windows, OpenAI citation/claim extraction. Whitespace-only model changes are recovered from unique contiguous original spans; changes to words or punctuation are rejected. Scanned PDFs require OCR text. |
| A: references | Crossref metadata with Semantic Scholar/OpenAlex fallback, DOI/title/author/year checks, retraction signals, process-local caches. An unrelated search result does not establish a mismatch. Local reviewed catalogs remain available for academic, legal, NGO and policy reports outside index coverage. |
| Legal references | Eyecite US case parsing, CourtListener citation resolution and opinion retrieval. Live access requires `COURTLISTENER_API_TOKEN`; absent credentials abstain. Non-US cases, statutes, subsequent treatment and current good-law status need additional resolvers/reviewer research. |
| B: source support | Open full text when available, abstract fallback, OpenAI support/partial/contradiction judgments, exact contiguous evidence quotes, confidence threshold and one bounded quote repair. Source identity and legal majority-opinion limitations remain visible. |
| C: signed data | Ed25519 record signatures, file/record hashes, per-device chains, trusted starting points/heads, organization/project scope. Every supplied capture is checked, including unlinked captures. |
| C: numbers | Explicitly linked counts, means, sample SD, individual readings, two-sided Welch/paired tests, rounding-aware comparisons, units and significance wording. Paired complete cases preserve row alignment. Methods/links are not guessed. |
| C: figures | Exact file hashes, perceptual/resize/crop comparisons, automatic crop proposals and possible reuse across conditions. Transformations require review; similarity is not authentication. |
| Scientific review | Design/methodology, statistics/uncertainty/multiple-testing concerns, causal inference/confounding, plausibility, reproducibility, external consistency and limitations. Model selects manuscript/source IDs; the server materializes original sentences and contiguous evidence passages. Invented IDs/quotes and inconsistent positive labels abstain. |
| Dataset diagnostics | Every column gets missingness, numeric/nonfinite counts and ranges; duplicate rows and constant numeric columns are disclosed. These diagnostics are not accusations or exhaustive statistical validation. |
| Evidence/review/audit | Flags with severity, uncalibrated confidence, fixes, source evidence, hashes, request IDs/model versions/prompts/usage, source-sampling disclosures, unassessed inputs and human-review requirements. No aggregate probability of paper truth. |
| Qiskit | Local Grover amplitude-amplification circuit, QASM2, exact statevector probabilities, seeded simulated measurements and complete batching. All classical findings remain in the report. |

The scientific model can still reason incorrectly or select irrelevant evidence. Exact quotation proves where evidence came from, not that the interpretation is correct. Missing controls, unreported methods, advanced statistics, field-specific expertise and unavailable underlying data remain unresolved. No universal accuracy guarantee or product accuracy target has been demonstrated.

## Context

Required: `org_id`, `project_id`. Optional: `references` (strings), `catalog`, `sources`, `support_claims`, `datasets`, `captures`, `figures`, `claims`, `public_keys`, `chain_starts`, `expected_heads`, `research_queries`.

- Sources: `id`, `text` or local `path`, `source_url`, `identity_reviewed`, optional `doi`, `citation`, `scope`. Source paths accept text/PDF/DOCX/TeX. Confirm source/version identity in the authenticated backend; an author-controlled Boolean is not independent authentication.
- Support claims: verbatim `claim`, `source_id`, exact source `quote`. In hybrid mode OpenAI also assesses semantic support.
- Datasets/figures/captures: `id`, local `path`, `org_id`, `project_id`. Datasets can include `capture_id`, `label`, `columns`, `unit`. Raw observations currently accept CSV/JSON; convert spreadsheets using an explicit recorded transformation.
- Data claims: verbatim `claim`, `dataset_id`/`figure_id`, `column`, `metric`, `reported`, `operator`, `decimals`, `test`, group fields, `paired_column`, `unit`, `significant`, `alpha` as applicable. Automatic links require an explicit dataset/figure ID or label in the sentence. Manual links handle tables or methods that cannot be safely inferred.
- Captures use the NoCap signed-record contract: id/type/file_name/file_sha256/captured_at/device_id/location/prev_hash, canonical JSON hash and Ed25519 signature. Public keys and chain heads must come from trusted backend/device enrollment, not self-approved manuscript uploads. This package does not implement AWS tenant authentication, device enrollment, storage or a reviewer UI.
- Catalog entries: `id`, `reference`, optional `aliases`, `status`, `reviewed`, `source_url`, `basis`. Catalog results are explicitly supplied reviewer evidence, not newly discovered independent validation.
- `research_queries`: optionally up to three reviewer-defined strings, each at most 300 characters. Search retrieves up to two Crossref candidates per query and their available evidence. Query/candidates/errors are recorded. Ranking does not establish relevance, and separate publications may share data. This bounded search is not an exhaustive literature review.

Every source, dataset, capture and figure is inventoried; unlinked evidence and unassessed columns/statements remain visible. Scientific category coverage concerns reviewed windows, not a guarantee that every possible error was found.

## Quantum interpretation

The Grover oracle marks already-computed review flags. Circuits use up to eight qubits per 256-finding batch. Padded states, no-marked/all-marked cases, iterations, circuit depth, probabilities and measurements are recorded. When amplification would not help, zero iterations is valid.

This uses a classical statevector simulator, not IBM hardware. Quantum probabilities are search probabilities, not scientific confidence. Constructing the oracle still requires classical evidence assessment. No accuracy gain or end-to-end quantum speedup is demonstrated.

## Real examples and limits

The hybrid scientific demo uses actual Reinhart–Rogoff source/replication text and published observations. The supplied links reproduce an unweighted mean of 110 numeric country-years: 2.167971692398155%. The original -0.1% table value differs; 2.2% matches after rounding. The discrepancy involves sample/weighting choices as well as an acknowledged spreadsheet coding error. This implementation does not independently discover/isolate that formula bug or establish causality/fraud. Historical observations stay unsigned.

`demo/context.json` additionally supplies 35 reviewed reference records from the earlier academic, withdrawn policy, legal and NGO corpus; the disputed wb-12 record is deliberately excluded. This offline catalog demonstration is not a blinded accuracy test. Previous corpus results in `outputs/real-world-validation` describe an earlier implementation and should not be presented as current general accuracy.

OpenAI uses strict Responses structured outputs and `store=False`. Audit reports contain submitted manuscript/source text; protect them appropriately in deployment. Public full-text retrieval is bounded and restricted to public HTTPS destinations; deploy workers with egress restrictions against DNS rebinding. Publisher access restrictions and provider rate limits remain applicable.

References: [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs), [IBM Grover tutorial](https://qiskit.qotlabs.org/docs/tutorials/grovers-algorithm), [Qiskit Statevector](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.quantum_info.Statevector).

### Luminal provider

Set `LUMINAL_API_KEY` in your private `.env`; optionally set `LUMINAL_MODEL` (default `deepseek-ai/DeepSeek-V4.1-Flash`). Select it with `--provider luminal` or `NOCAP_PROVIDER=luminal`. OpenAI remains the default and can be selected with `--provider openai`.

The adapter targets `https://flash.luminal.cloud/v1/chat/completions`, requests structured JSON, validates returned schemas locally, rejects truncated responses, and records provider-specific audits. It uses the same citation, source-support, scientific-review and data-linking pipeline; local statistics, signatures, image checks and Qiskit remain available. Credentials are never sent through redirects. Provider retention is unverified. There is no automatic switch to another paid provider.

Live check on 2026-10-11: the dashboard-confirmed Flash endpoint authenticated and returned valid structured JSON. The verifier extracted three exact invalid original-v1 bibliography entries and publication lookup returned `NOT_FOUND` for all three. This is a small smoke test, not a general accuracy benchmark. Some requests reject strict schema mode; only an explicit response-format-unavailable error triggers a JSON-object retry, and every output still undergoes local schema validation. The scientific fixture initially received HTTP 503; local numerical assessment remained available and flagged the -0.1% / 2.168% discrepancy. API failures remain review-required findings. Provider retention remains unverified.

Scientific fixture retry: a second attempt also returned HTTP 503. Scientific assessment remains incomplete; citation smoke testing succeeded. See `demo/luminal_validation_summary.json`.
