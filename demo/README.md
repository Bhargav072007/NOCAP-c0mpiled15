# Synthetic fixture rehearsal

Every asset in this directory is synthetic and unsigned. `captures.json` stores
empty signatures and `fixture: true`. `photo.jpg` is a generated calibration
graphic, not a photograph. `photo_ai_edited.jpg` is a deterministic altered copy,
not an AI edit; its name follows the supplied build-plan convention. The tone
and temperature reading were generated, not captured by a device.

`paper_real.txt` contains **fictional** references with scripted mixed outcomes;
the filename follows the build plan and does not mean real citations.
`paper_fake_refs.txt` has three explicitly invented references, each mapped to
a fixture NOT_FOUND result. No provider, AI or scholarly lookup runs.

Regenerate assets: `.venv/bin/python scripts/make_demo_assets.py`. Fixture hash
identifiers do not implement Sanjay's canonical record signing.

Rehearsal (repeat twice):

1. Start in fixture mode. State that all data and verdicts are synthetic.
2. Live captures: select the photo, inspect its original graphic and full hashes;
   select the audio or reading, then refresh. No cryptographic signature exists.
3. Verify a file: download the synthetic original and edited copy; upload
   `photo.jpg` and select Verify file (DEMO VERIFIED = registry byte match).
   Upload `photo_ai_edited.jpg` (DEMO CAP = no fixture registry match).
4. Citation check: Load mixed demo, Check citations, inspect all four scripted
   statuses and their reasons. Load three fake references and repeat; all three
   are fixture NOT_FOUND. Arbitrary text is rejected in fixture mode.
5. Audit ledger: inspect count, zero signed records, unknown chain verification
   and the real computed Merkle root of the synthetic record identifiers.
   Download `nocap_ledger.json`. It must equal the fixture adapter snapshot.
6. Settings: try Empty, Disconnected, Malformed, then Populated. Try Slow to see
   actual waiting indicators, or Long list for 60 records. Return to Populated.

This is a fixture rehearsal, not the team's hardware/API/verifier integration.
