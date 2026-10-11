# UI-P1 — product photos, grounded copy and brighter green

Enhanced both supplied prototype photos with built-in image_gen; preserved the visible white enclosure, logo, lens, unlit display and cutout arrangement. Placed the angled studio image in the hero and the mint-background top view next to the hardware description. Retouched imagery is labelled. Original photographs remain unchanged.

Rebuilt the homepage narrative from the supplied 21-page Product Documentation: intended audience, reference/claim/data review model, optional hardware, documented capture/sign/connect architecture, human ownership, and product FAQs. Source pages and boundaries: docs/product-content-sources.md. Exact image edit prompts: docs/product-image-prompts.json. Internal market assumptions, target accuracy, pricing and future security features are not advertised as established facts.

Changed muted sage to #78F59B spring green, with #0C1B14 forest background and matching surfaces, motion accents, controls and native Streamlit theme. Retained animated demo, flow illustration, accessible motion controls and single-source model.

Validation:
- pytest: 66 tests + 7 subtests passed; two existing upstream warnings. compileall passed.
- Both WebP images return HTTP 200 / image/webp, ~130 KB each; fixed aspect ratios and alt text, lazy detail loading.
- Browser screenshots inspected at 1280px, 390px and 320px; images loaded, no horizontal page overflow; demo cards retain their full content bounds.
- Product anchor navigation and native FAQ open state checked. Local-demo sign-in reaches Overview with current API records.
- Primary action contrast 12.82:1; secondary text on main ground 10.09:1.
- Reduced-motion rules cover the new product image entrance/hover; existing surface pause controls continue to apply.

No backend contract changes. Hardware signing/cloud readiness remains explicitly unvalidated in the local demo. Publication should preserve collaborator changes to verifier code and exclude environment/runtime files and the original private product PDF.
