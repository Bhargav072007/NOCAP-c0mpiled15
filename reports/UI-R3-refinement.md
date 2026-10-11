# UI-R3 — typography, layout and motion refinement

Applied the user-requested Impeccable, Taste and Emil Kowalski repositories. Exact source revisions, adapted motion recipe and licenses are documented in docs/design-sources.md.

## Changes
- Self-hosted Instrument Sans and Newsreader italic; clearer hierarchy and tabular metrics.
- Warm charcoal surfaces, one muted sage accent, readable secondary text and consistent focus rings.
- Replaced repeated feature columns with an editorial workflow list; removed unnecessary eyebrow labels and nested dashboard panels.
- Enlarged 3D preview controls and labels; preserved automatic tour, manual steps, native pause and continuous decorative ribbon.
- Replaced hover sweeps/springs and repeated navigation entrances with 160ms control feedback and 180ms result feedback.
- Kept token sign-in, local demo, data contracts, stored data and one-source settings intact.

## Validation
- pytest: 66 tests and 7 subtests passed; two existing upstream deprecation warnings.
- Browser inspected at 1440, 820, 390 and 320px. Fixed phone horizontal overflow from projected 3D layers by clipping the scene, with card text retaining its full bounds.
- Native Capture selection and shared pause verified; scene and ribbon both pause. Saved Reduce motion stops the ribbon. Preference restored after inspection.
- Empty token validation and Open local demo verified in browser; dashboard records loaded from the local API. No Devices tab.
- Locally served font returned HTTP 200 / font/ttf.
- Impeccable detector: one warning for Instrument Sans; deliberately retained with Newsreader pairing. No critical finding. This is not a zero-warning result.

This is local synthetic validation, not proof of hardware/cloud connectivity or end-to-end verification. Backend integration work remains separate.
