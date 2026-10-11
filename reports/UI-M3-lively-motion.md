# UI-M3 — visible, purposeful motion

Used Emil Kowalski's animate skill and recipes (source revision and MIT notice in docs/design-sources.md).

## Added effects
1. Staggered masked headline reveal.
2. Short supporting-copy and action entrance.
3. Orbiting filament around the existing ambient ribbon.
4. Floating three-layer document illustration.
5. Scanning light across the document.
6. Travelling packets along the capture/review/export rail.
7. Sequential node rings on the illustrated workflow.
8. Compact animated workflow guide in Overview.
9. Metric underline that draws on pointer hover.
10. Review-row highlight crossfade.
11. Collaborator avatar tilt on pointer hover.
12. Upload icon lift on pointer hover.
13. Active evidence-tab underline transition.
14. Native review/member dialog scale-and-fade entrance.
15. Directional link-arrow hover feedback.

CSS only, using existing ease-out and the exact recommended movement curve. Marketing motion explains a labelled illustration; frequent controls use 160–180ms feedback; dialogs use 250ms. Native surface pause controls stop the diagram, demo and ribbon loops. System and saved reduced-motion settings stop the new motion. Real metric values are not animated or fabricated. One-source model and access flows preserved.

## Validation
- 66 tests and 7 subtests passed, with two existing upstream warnings; compileall passed.
- Desktop and phone screenshots reviewed. Corrected mobile headline spacing and compact document clipping.
- Document and scanner transforms sampled at separate times, confirming movement. Native homepage and workspace pause confirmed on packet/document/ribbon/filament effects.
- Saved Reduce motion confirmed: stack, packets and filament animation names become none; scanner and motion toggles hidden. Preference restored.
- Open local demo and native Create a review dialog checked without creating records. Dialog transition is the intended 250ms curve.
- No backend changes or additional package dependencies. Local synthetic validation, no new hardware/cloud claim.
