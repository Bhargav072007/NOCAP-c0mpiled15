# UI-M2 — Interactive 3D demo and responsive layout

Replaced the landing page's static evidence illustration with a working, interactive workflow preview. Capture, review and export cards cycle every 15 seconds through a layered CSS 3D scene. A sample signal draws into view, rear panels move gently in depth, and the scene responds to pointer hover on devices that support it.

Visitors can choose any stage with native radio controls, use arrow keys, return to the automatic tour, or pause/resume the entire scene and its colour ribbon. The preview is explicitly labelled as sample data. “Try the workspace” leads through the existing sign-in/local-demo flow.

Responsive improvements include fluid hero typography, a two-column desktop/tablet layout, a stacked phone layout, smaller perspective angles on phones, responsive panel dimensions and room for controls on narrow screens. Workflow cards have a restrained 3D hover response. No external assets, WebGL runtime, JavaScript injection or new dependencies were added.

## Validation

- Python compilation passed. Final regression suite: **66 tests and 7 subtests passed**, with two existing upstream deprecation warnings.
- Browser inspected at 1440px desktop, 820px tablet, and 390px/320px phone widths. No horizontal document overflow or overflowing demo-card content at those widths.
- Capture, review and export selection worked; ArrowRight moved the selected radio from Review to Export and displayed the correct card.
- Automatic tour uses actual matrix3d transforms and staggered panel animation; the sample signal's rendered CSS element and animation were confirmed.
- Pause set every animated scene element and ribbon to paused. Repeated reads showed identical transforms. Resume restored playback.
- The initial SVG signal was removed by Streamlit's HTML sanitizer. Replaced it with a native CSS polygon and clipped drawing animation, then visually verified it in the actual browser.
- Manual Reduce motion preference set all seven scene/ribbon animation names to none. Pause control was hidden; selecting Export still displayed the export card. The preference was restored afterward.
- Operating-system reduced-motion CSS also supplies a static view. This system rule was reviewed in code; manual preference was exercised in-browser.
- The preview's workspace link and Open local demo button successfully opened the authenticated local Overview.
- Screenshots were reviewed inline. This was local synthetic-data validation, not hardware/cloud/verifier acceptance.

## Files and access

Added dashboard/demo.py and dashboard/demo.css. Updated dashboard/shell.py and dashboard/ui.py; documented this milestone in README.md, reports/README.md and context.md. Existing evidence workflows, API contracts, source configuration and stored data are preserved.

The new request expands UI-M1's ambient-only continuous motion into a coordinated moving demonstration. The authenticated dashboard keeps its existing compact ribbon. One-source navigation remains unchanged, with no Devices tab.

Open http://localhost:8501/ and select **Explore the demo**. Local UI/API services remain running. The illustration creates no records and performs no verification or export. Live AWS, physical source integration, real signing/verifier providers and durable Sepolia orchestration remain external.
