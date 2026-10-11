# UI-M1 — NoCap motion update

Implemented ten animated UI components and one continuous Gemini-inspired colour ribbon on the existing landing, sign-in and workspace pages.

## Reference and implementation

Inspected [Jitter UI elements](https://jitter.video/templates/ui-elements/) and its [Animated UI Kit](https://jitter.video/template/animated-ui-kit/) in the browser. Button, toggle, navigation, badge, list and progress patterns informed original native CSS. No template files were exported, copied or embedded. The ribbon is an original interpretation, not an exact Gemini asset.

| # | Component | Motion |
|---|---|---|
| 1 | Landing headline | Two-line masked entrance |
| 2 | Primary action buttons | Highlight sweep and directional hover |
| 3 | Evidence illustration card | Entrance, layered edge and hover lift |
| 4 | Workflow steps | Scroll entrance and step-marker movement |
| 5 | Sidebar navigation | Growing active rail and label movement |
| 6 | Evidence tabs | Drawing selected underline |
| 7 | Upload target | Focus/hover border, lift and icon response |
| 8 | Native switches | Track and thumb transitions |
| 9 | Returned verdict badges | Single arrival animation per new result identity |
| 10 | Review progress | Masked fill reveal preserving the actual API value |

The ribbon loops every 12 seconds; there is exactly one rendered instance per page. Landing uses the larger version; login and workspace use the compact version. The native checkbox/label control pauses and resumes it without a server rerun. Workspace display preferences and operating-system reduced-motion CSS disable authored animation. Navigation and result controls remain native Streamlit controls.

## Validation

- 66 tests and 7 subtests passed, with two existing upstream deprecation warnings. Python compilation passed.
- Browser inspected desktop landing/dashboard and 390px landing, login and dashboard; no horizontal page overflow.
- Open local demo successfully authenticated and loaded the existing API-backed workspace.
- Pausing produced animation-play-state: paused; the computed transform stayed identical between reads. Resume restored the loop.
- Exactly one infinite animation was found in the settled workspace DOM: nc-aurora-ribbon.
- Reduce motion disabled the ribbon (computed animation-name: none) and hid its control; preference was restored to allow the requested motion.
- Native switch thumb transitions, selected tab underline, upload transitions and result-badge animation matched the actual rendered DOM.
- The review progress retained the native translateX(-100%) at zero approved reviews. The reveal uses clipping so it cannot override the actual completion value.
- Screenshots were reviewed inline in the task. Operating-system reduced-motion rules were inspected in code; manual preference was exercised in the browser.

Files: dashboard/motion.py, dashboard/motion.css, dashboard/shell.py, dashboard/workbench.py, dashboard/ui.py. Existing one-source model and four workspace sections are preserved. No backend contract changes or extra frontend dependencies.

## Access and boundaries

Open http://localhost:8501 → Sign in → Open local demo. Local Streamlit and FastAPI services remain running; existing SQLite data is preserved. This update does not establish live hardware, AWS connectivity, real signature verification, citation-provider verification or Sepolia completion.
