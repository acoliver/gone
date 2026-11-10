# Her dresses visual QA

## Verdict

**The delivered dresses are recognizable as a blue sleeveless dress and a rose cap-sleeved dress beside the central tunic in both actual game views.** The wardrobe view is less clear than the doorway view, but neither dress is reduced to a coloured sliver. In aged game lighting, both dresses read pale and visibly aged, not black. The close-ups show substantially improved ragged hems, softened shoulder damage, and textured fibre heaps. The principal remaining weaknesses are that the aged deposits lose their soft/fibre character at game scale, dust on upward-facing folds is hard to distinguish in the actual game captures, and the rose dress has a conspicuously large open shoulder/neckline tear in neutral close-up.

The baseline aged wardrobe panel has the central tunic and dark side garments, but no individually readable blue and rose dresses; the before-aged dress-specific ratings reflect that. The unchanged grey tunic debris is not counted as a dress-owned deposit.

## Scores

Scale: 1 poor, 10 excellent. Recognition and all-three visibility are judged from the corresponding actual game panel(s); aged craft criteria use the neutral Blender comparison and close-ups. A remembered aged-condition score is n/a because the remembered captures do not depict aged dresses.

| Criterion | Before remembered | After remembered | Before aged | After aged |
|---|---:|---:|---:|---:|
| Recognition | 8 | 9 | 2 | 8 |
| All-three visibility | 8 | 9 | 2 | 8 |
| Hem quality | 7 | 7 | 3 | 7 |
| Shoulder quality | 7 | 7 | 3 | 6 |
| Dry fabric credibility | n/a | n/a | 3 | 7 |
| Upward-fold dust | n/a | n/a | 1 | 5 |
| Soft floor deposits | n/a | n/a | 2 | 6 |
| Freedom from rendering defects | 7 | 8 | 4 | 7 |
| Overall | 7 | 8 | 3 | 7 |

## Actual game-camera evidence

| View | All three individually recognisable? | Either dress looks black? | Dress-owned deposits read soft? | Readiness |
|---|---|---|---|---|
| Remembered wardrobe | Yes. The rose dress, tunic and blue dress each have a distinct hanging silhouette; the blue dress is narrower and partly behind the tunic. | No. The two dresses read olive/rose under the warm light. | n/a | Ready; all three read as separate garments. |
| Remembered doorway | Yes. Both dresses and the central tunic remain separate and clearly visible in the open wardrobe. | No. | n/a | Ready. |
| Aged wardrobe | Yes, though the tunic overlaps the inner edges of the dresses; the blue dress remains a distinct pale blue garment and the rose dress a pale pink garment. | No. Both are pale, not black. | Weakly. Two pale tan patches are visible on the wardrobe floor, but their fibre softness is not legible at this scale. | Usable, with reduced detail readability; deposits need stronger readable soft silhouette/contrast at game scale. |
| Aged doorway | Yes. The two pale dresses and blue-grey central tunic have distinct silhouettes and colors. | No. Neither reads black. | Weakly. Small tan patches under the wardrobe are visible, but appear as small flat scraps from this distance. | Usable. Improve floor-deposit readability; dress identification itself passes. |

## Craft details and scale survival

- **Hems:** In `decay-comparison.png`, the delivered blue hem (top row, right half) has uneven small scallops and several short edge losses rather than the baseline's narrow hanging strips. The delivered rose hem (same row, far right) has a broader irregular contour. These read as damaged fabric rather than long dangling fringe. Grain-aligned raggedness is present but modest. At game scale, the hems are not individually resolvable; the overall uneven lower outlines survive.
- **Shoulders:** Delivered shoulder close-up shows damaged shoulder edges on both garments. The blue dress has a small edge break; the rose dress has a much larger open split at the viewer-left shoulder/upper arm and a broad exposed neckline/back opening. Damage is softer and less spike-like than the baseline torn shoulder in the middle row of `decay-comparison.png`, but the rose opening remains abrupt and large. At game scale only the garments' shoulder silhouettes survive, not the split detail.
- **Dry fabric:** In the neutral close-ups the cloth is matte, faded and visibly textured, with irregular discoloration and stiff hanging folds. The aged wardrobe game panel also renders both garments pale against the dark closet. The neutral captures support a brittle, dry read; fine weave and mottling are lost at game scale.
- **Upward-fold dust:** `controls-comparison.png`, bottom row, shows a visible difference: the delivered shoulder view at left has light dusty color on the raised folds; the fold-dust-disabled view at right is more uniformly saturated. This is a real but restrained improvement. In game captures the folds are too small and lighting too dim for dust to read as a distinct layer. The shoulder close-up alone does not make the dust strongly legible without the control.
- **Floor deposits:** `decay-comparison.png` bottom row and `aged-heap.png` show delivered deposits as raised, irregular, fuzzy fibre piles, visibly softer than the baseline's flat pale shapes with edge threads. The control's upper-left wardrobe pair confirms that edge fibres and side deposits are visible when enabled and absent in the disabled image. However, both actual game views reduce them to pale tan floor patches. In the close-ups, isolated tiny specks sit near the left heap; these read slightly detached from the main deposit. The central grey debris in the aged game wardrobe is unchanged tunic debris, not a dress deposit.

## Ranked remaining defects and remedies

1. **Deposit softness and ownership are weak at game scale.** In `comparison.png`, lower-right aged wardrobe, two pale tan patches sit on the floor beneath the dresses; in `game-doorway-comparison.png`, aged/right panel, the same deposits are tiny pale marks under the wardrobe. They do not retain the fluffy edge visible in `aged-heap.png`. Increase the visible soft, irregular perimeter and fiber contrast at the actual camera distance, while keeping the two heaps individually placed under their respective dresses and distinct from the central tunic debris. Validate in both game views, not only the neutral close-up.
2. **Rose shoulder tear is overly open and sharply defined.** In `aged-shoulder.png`, right dress, viewer-left shoulder/upper arm area, a large angular loss exposes the interior, with a hard dark boundary. Reduce the opening or break its contour into a softer, fabric-grain-aligned split; preserve a clear aged tear without making the shoulder look cut away. Confirm it still reads as a cap-sleeved dress in the game view.
3. **Fold dust is subtle and does not survive game scale.** In `controls-comparison.png`, bottom-left delivered shoulder, pale dust is visible mainly on raised fold ridges; the actual wardrobe and doorway images do not show a clearly separable dust deposit. Increase restrained ridge-localized contrast or coverage enough to survive the game camera and existing lighting, retaining the aged fabric colors. The control establishes a visible neutral-render difference, but the game views do not yet establish an equally readable effect.
4. **A few detached fibers/specks sit beyond the heap edge.** In `aged-heap.png`, around the upper/left edge of the left heap, several tiny isolated marks are separated from the main fuzzy deposit. Remove them or gather them closer to the edge so they read as shed fibers connected to the settled pile rather than floating debris.

## Image reads

All six requested absolute paths were read directly, one at a time. Each tool response was `Binary content provided (1 item(s)).`; image pixels were available for visual inspection. No read failures.

1. `/Volumes/XS1000/acoliver/projects/gone/branch-2/tmp/wt-95s/docs/art/quarters/sheets/her_dresses/comparison.png`,actual wardrobe before/after, remembered/aged panels.
2. `/Volumes/XS1000/acoliver/projects/gone/branch-2/tmp/wt-95s/docs/art/quarters/sheets/her_dresses/game-doorway-comparison.png`,actual game doorway, remembered/aged.
3. `/Volumes/XS1000/acoliver/projects/gone/branch-2/tmp/wt-95s/docs/art/quarters/sheets/her_dresses/decay-comparison.png`,neutral before/after hems, shoulders and deposits.
4. `/Volumes/XS1000/acoliver/projects/gone/branch-2/tmp/wt-95s/docs/art/quarters/sheets/her_dresses/aged-shoulder.png`,delivered neutral shoulder close-up.
5. `/Volumes/XS1000/acoliver/projects/gone/branch-2/tmp/wt-95s/docs/art/quarters/sheets/her_dresses/aged-heap.png`,delivered neutral dress-owned deposits.
6. `/Volumes/XS1000/acoliver/projects/gone/branch-2/tmp/wt-95s/docs/art/quarters/sheets/her_dresses/controls-comparison.png`,matched effect-off controls.

## Causal hypothesis

**Hypothesis:** the mismatch between close-up craft and game-scale readability comes from the damaged-fiber and dust details occupying too few pixels under the existing game camera and lighting. The captures show the scale/readability difference; they do not establish the implementation cause.
