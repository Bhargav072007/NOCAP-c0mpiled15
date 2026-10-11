# Design sources — UI-R3

This revision applies the three repositories requested by the project owner to the existing Streamlit interface. It does not install a new UI framework or embed third-party templates.

- [Impeccable](https://github.com/pbakaus/impeccable), commit `c63b8dd7dd5a5f3c32eaabe1af76d0694f863ed2`: refinement workflow, polish checklist and craft floor informed spacing, contrast, hierarchy and responsive inspection. Ran its context and manual detect commands. Apache-2.0 license retained under `docs/licenses/`.
- [Taste](https://github.com/Leonxlnx/taste-skill), commit `d237dd399d57524945c0c81327da5da19f7a468d`: existing-project redesign guidance informed the workflow list, flatter dashboard, single sage accent, consistent neutral surfaces and tabular numbers. MIT license retained under `docs/licenses/`.
- [Emil Kowalski skills](https://github.com/emilkowalski/skills), commit `2d228630ba1446365f614a108cb8252f1feda202`: adapted the animate skill's `cubic-bezier(.23,1,.32,1)`, 160ms button press feedback and `scale(.97)` recipe in `dashboard/motion.css`. Removed repeated dashboard entrance animations and hover sweeps. MIT license retained under `docs/licenses/`.

The requested continuous ribbon and explanatory 3D tour are retained as deliberate exceptions to generic anti-decoration advice. Both have native pause controls; system and saved reduced-motion preferences stop animation. Real records, progress and verdicts never derive from the illustration.

Instrument Sans (400/500/600) and Newsreader italic (400) are locally served from `dashboard/static/fonts`. Their SIL Open Font Licenses are included alongside the font files. No third-party font request is required at runtime.

The detector reports one warning for Instrument Sans as an overused face. This was reviewed and retained: its readable UI forms pair with Newsreader's editorial headline, while layout and motion are specific to evidence review. No critical detector finding was emitted. The warning is not represented as a clean detector pass.

## UI-M3 — visible explanatory motion

Further adaptations of Emil's animate skill and RECIPES.md: masked marketing entrance (700ms with 70ms stagger), 160–180ms retargetable pointer feedback, and the 250ms dialog starting-style recipe. Reused `--nc-ease` and introduced the exact recommended on-screen movement curve as `--nc-move`. Original CSS document illustration combines transform-only floating layers, a scanner, linear packets and opacity/scale node pulses. Long loops are confined to labelled illustrations and decorative ribbon filaments, with native pause controls; actual metrics and review data remain stationary. No new library, bitmap download or third-party asset dependency. Existing MIT notice covers adapted recipes.
