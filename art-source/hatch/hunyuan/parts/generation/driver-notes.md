# Driver notes on Hunyuan hatch inputs (prev-inputs.jpg)
- FLUX inputs drifted from the concept: mostly intact green paint (fine for shape, paint comes later),
  but B-front has a small wheel and a centre seam; concept wheel is ~300 px of a 510 px leaf.
- A-left (side view for multiview) is a deep cabinet/box: would push the assembly into a thick box.
  Compare single-view vs multiview A carefully.
- B-left is a thin slab with the wheel standing off: good for the leaf.

## Driver judgement, category A (whole hatch), prev-A-all.jpg
- A-s410-sv: keep. Front reads as a real hatch (rounded riveted frame, strap hinges, dogs, six-spoke wheel); edge-on is a plate with the wheel on a short axle.
- A-s413-sv: keep. Similar to 410, slightly cleaner silhouette.
- A-s411-sv: reject. A stray flat plate sticks out of the back on a long stalk.
- A-s412-sv: reject. Back filled in as a deep box/cabinet.
- A-s410-mv: reject. The box-shaped side view made the whole thing a deep cabinet, as feared. Multiview with the current A-left input hurts.
- All A meshes fuse leaf and frame; the front plate is thin (structure will need the leaf slab thickened / split in Blender).

## Driver judgement, category B (door alone), prev-B-all.jpg
- All four reject. The FLUX input had a small off-centre wheel and a centre seam, and the meshes copied it:
  a mostly blank slab with a small wheel near the latch edge; the projected concept (big centred wheel)
  does not line up with the mesh wheel. Edge-on they are a thin plate.
- If a separate door is needed, regenerate B from a better input (the concept leaf crop with the frame
  painted out, wheel centred and about 60% of the leaf width), or split the door out of A-s410/A-s413.

## Driver judgement, category C (frame alone), prev-C-all.jpg
- All three usable: a clean rounded ring with a raised bead, evenly spaced rivets, open through the middle,
  one hinge knuckle/plate on the right edge. C-s410-sv and C-s412-sv cleanest.
- Only one hinge mount (concept has two, top and bottom); band width looks close to the concept's,
  check it against the 90 mm target after scaling. A frame from C plus a door from A (or a regenerated
  B) is the likely route.

## Driver judgement, paint (prev-paint.jpg)
- Hunyuan Paint followed the FLUX inputs' pale green paint, not the concept's rust: reject for this asset.
- Concept projection on A-s410 reads close to the concept from the front; at 30 degrees the wheel shows a
  doubled ghost because the front projection smears onto off-plane geometry. Production paint should stay
  the concept-derived atlas on proper UVs (as design.md says), not a raw front projection.

## Licence (read from the exact model card + Tencent Hunyuan 3D 2.0 Community License)
- Commercial use allowed under 1M MAU; outputs are owned by us.
- Territory excludes the EU, UK and South Korea; section 5.c forbids using, distributing or displaying
  outputs outside the Territory. Pushing generated meshes to the public GitHub repo, or shipping the game
  where EU/UK/KR players can get it, conflicts with that. Needs Andrew's call before any push.
- Distribution needs the licence copy + Notice file; AUP 12 asks machine-generated content to be identified
  in public contexts.

## Driver judgement, leaf2 (prev-overview.jpg) and a coordinate error of mine
- All six leaf2 meshes are cut off on the right: square top-right corner, no hinges, the wheel against the
  right edge. Cause: the crop I gave, [365,77,875,960], is wrong. Measured on a pixel grid
  (concept-grid.jpg), the concept door spans about x 385..990, y 65..1094 (the worker's own outline fit
  found [384.6, 65.0, 990, 1094]); the wheel centre is about (687, 540) and ~340 px across; the hinge
  barrels straddle the right seam out to x ~1045; latch dogs on the left at x ~400..540.
- The whole-hatch crop [255,25,985,1050] also clipped the right frame/hinges and the sill; the A meshes
  only looked whole because FLUX redrew the image.
- Next: regenerate the leaf from crop about [365,45,1060,1110] with the mask = fitted door outline plus
  the hinge hardware that crosses the right seam. Use the corrected numbers in every later brief.

## Driver judgement, slice-2 ring registration probe (slice12/prev-clay.jpg)
- The probe flattened the frame: rivets gone, edge-on it is paper thin. Squashing the generated ring
  (bead depth roughly ten times the 20 mm protrusion target) into 20 mm erases its relief, exactly the
  "fitting erases the generated shape" risk in design.md.
- Decision: preserve relief. Do not scale the ring's depth down by more than half relative to its in-plane
  scale. The ring may stand up to 50 mm proud of the wall (inside Andrew's <=60 mm limit); any extra
  depth goes into the wall behind it (the pocket and wall are hidden by the ring). Update the sim frame
  recipe constant (HATCH_RING_FRONT and related) to the chosen protrusion with the reason in code and
  tests, keeping band 80..100 mm, flushness <=30 mm and reveal <=20 mm (the leaf face moves with it).
- Rivets and the hinge mounts come from the generated source, not re-added primitives.
- connector-route timed out (issue #90) while a Hunyuan generation was running on the same GPU; rerun it
  with nothing else on the GPU before treating it as a regression.

## Driver judgement, leaf3 (leaf3/prev-overview.jpg, prev-pick.jpg)
- The corrected input fixed it: all six are a complete rounded door with two strap hinges crossing the
  right edge, latch dogs on the left, a six-spoke wheel with the hazard band, the concept's vertical rib,
  and the wheel on a short boss (no long axle). Backs are a plain flat face (expected from a front view;
  the reverse face and reverse wheel come from the fitting step).
- Pick: seed 430 (cleanest silhouette, three dogs, two hinges, rib). Alternate: 433 (wheel stands
  proudest at 60 deg). Reject 434 (doubled outline/edge) and 435 (extra dotted rivet line on the left).
- Slab is thin (plate); slice 3 must thicken the body between the sim's face planes without stretching
  the hardware, per design.md.

## Driver judgement, slice-2 fitted frame candidate (slice2b/prev-clay.jpg) - REJECT, do not promote
- Rivets are gone again; the rounded bead is reduced to a thin flat strip.
- The visible mass at 30/60/90 deg is the old flat interface boxes (collar/stop/pocket skins) standing
  far proud of the generated ring, so it reads as boxes again - the thing Andrew rejected.
- Bottom: a thick block and a protruding cylinder below the sill.
- Two existing Blender suites fail (construction, round3).
- What to fix: the generated ring must be the visible front surface; interface/seal pieces sit behind or
  flush with it (hidden from the front and from 30-60 deg), never in front of it. Rivets and bead relief
  survive (depth scale >= half in-plane, as already decided); verify by clay renders matching the raw
  source's rivet count and bead profile before any game capture.

## Driver decision after the slice-2 contract stop (contract-conflict.log)
Why the conflict happened: my "depth scale >= half the in-plane scale" rule was applied to the source's
whole depth (0.167 units), which includes the hidden back half of the generated tube. The worker had to
push the ring 100 mm back into the wall (HATCH_RING_BACK), where its corner reservation boxes overlap the
door slab's corners (3.3 x 79.6 mm) and the reveal ranges. The rule measured the wrong thing: only the
part of the ring in front of the wall is ever seen.

Decision (replaces the earlier depth rule):
- The ring keeps its original depth range in front of the wall: front at 28 mm proud
  (HATCH_RING_FRONT = -0.028, 2 mm margin inside the 30 mm flushness limit, which the 30 mm attempt
  exceeded by 65 micrometres), rear plane unchanged at HATCH_RING_REAR = -0.006. Remove HATCH_RING_BACK.
  No ring reservation behind the rear plane; lip/throat/collar interfaces unchanged.
- Use only the source's visible front relief: cut the generated ring at the plane where its outer and
  inner flanks meet the band (discard the hidden back), then scale that front relief into the 22 mm
  between front and rear planes. Measure the ratio of front-relief depth scale to in-plane scale and
  report it; no fixed minimum, but rivets and the bead crown must stay distinct: in the clay renders
  (front, 30, 60, 90) rivet heads stand at least 5 mm proud of the band face around them and the bead
  profile is visibly rounded edge-on. Add these as measured checks on the fitted mesh.
- Interface/seal pieces sit behind or flush with the generated ring surface, never in front of it.
- Fix the other defects found: fixed normals, outline excess, seal and pocket misses, zero tangents
  (Khronos), sub-texel contour UV islands. No gate changes.

## Driver decision after the slice-2 attempt-3 stop (slice2c/report.md)
Conflict: the legacy collar boxes FRAME/LEFT/RIGHT/TOP stand 60 mm proud and the STOP pieces 31.25 mm
proud, 32 mm and 3.25 mm ahead of the 28 mm generated ring. Their exact extents are pinned because they
are the closed-door collision solids (part of the 1,013 colliders and the replay digests).
Why it matters: the old primitive art drew each collision solid as visible geometry, so "collision box"
and "what you see" were the same object. That coupling is what keeps the frame looking like boxes.

Decision: split them. Collision stays exactly as it is in sim (extents, IDs, order, count, digests,
1 um pins on the sim/export records, all unchanged). The rendered frame is the generated ring plus
rendered interface surfaces that are trimmed so they lie inside their collision reservation and behind or
flush with the generated ring front; nothing rendered stands ahead of the ring. An invisible collision
margin of up to 32 mm in front of the visible ring is accepted (the player capsule radius is 300 mm, so
it cannot be perceived).
Tests: the Blender construction guard that the RENDERED collar boxes equal their reservation extents is
a test of the old primitive art and is replaced by (a) sim/export collision extents unchanged to 1 um
(kept), (b) every rendered interface triangle inside its reservation and not ahead of the ring front,
(c) all seal/pocket ray tests unchanged with zero misses from both sides. Record this replacement and the
reason in the test file.

## Driver decision after the slice-2 attempt-4 pre-scan (slice2d/report.md)
1. and 2. tests/hatch_seal_test.gd test_rendered_collar_boxes_match_collision_within_one_micrometer and
   the extent half of tools/blender/test_hatch_finish_construction.py
   test_collar_and_stop_edges_are_modelled_roundovers_with_the_same_extents enforce the same old
   "drawn box = collision box" equality as the round3 guard. The attempt-3 decision covers all three
   sites: replace the extent equality at each with the three replacement checks (sim/export collision
   extents unchanged to 1 um; every rendered interface triangle inside its reservation and not ahead of
   the ring front; seal/pocket rays zero misses both sides). Keep the roundover requirement for the
   rendered interface edges that remain visible. Record the reason in each test.
3. The floor threshold is exempt from the "nothing ahead of the ring" rule. The rule was about the frame
   posts and top around the door. The sill/coaming/STEP pieces are the floor-level threshold you step
   over (the concept has a heavy base there); they stay rendered at their full collision extent and
   tests/hatch_threshold_test.gd stays unchanged. STOP-BOTTOM follows the stop rule (trim 3.25 mm) only
   if that does not open a gap in the threshold grid; otherwise it is part of the threshold too.
No other gate changes. Everything else in the earlier decisions stands.

## Driver clay check of the slice-2e candidate snapshot (driver-check/prev-clay.jpg, prev-6090.jpg)
Copied at the worker's build ~21:34 and rendered with its own render_clay.py (no edits to its files).
- Better than every earlier attempt: rounded ring with rivets visible all round (scalloped edge-on), no
  flat boxes in front of it from the front.
- Three knuckle blocks on the hinge edge (top, middle, bottom). Only two hinge stations (0.48 m, 2.24 m)
  are wanted; the middle one looks like the source's original mount left in place. Remove it.
- Two long horizontal rods stick straight out of the frame on the other edge at about the two hinge
  heights, ~150 mm forward into open space at 60 and 90 degrees. Identify them; anything that is not
  attached to a visible part and not inside a reservation is a defect.
- The ring band reads narrow next to the raw source; that is Andrew's 80..100 mm band, accepted.
- In isolation the collar interfaces show as deep slabs at 30/60 deg; they run into the wall thickness,
  so judge them only in the in-game captures.

## Driver clay check of build 9 (driver-check2/prev-clay.jpg)
- Still three blocks on the left edge (top, middle, bottom) and still two ~150 mm rods sticking straight out
  of the right edge at about 0.48 m and 2.24 m. The "original mount removed" test passes, so either the
  middle block is something else or the test does not catch what is drawn.
- New: at 60/90 deg the interface layer shows a thin plate standing off the top-left corner at an angle.
- Required next: a labelled clay render (each fixed part in its own colour with its ID in a legend) at
  front, 30, 60, 90 so every visible piece is identified; then each piece is either justified (attached,
  inside its reservation, matching the concept) or removed. Rods into open air and stand-off plates are
  defects regardless of which test passes.

## Correction after identifying the build-9 parts (driver-check2/identify.py)
- The three blocks on one edge are KEEPER/0..2 (latch keepers for the three dogs, 68..28 mm proud,
  160 mm tall): intended, not a leftover hinge mount. My earlier note was wrong.
- The two "rods" are HINGE/PLATE-0 and PLATE-1: 40 mm tall frame-side hinge plates running from the ring
  front (28 mm proud) back 210 mm through the jamb to the hinge axis. In an isolated clay render they
  look like rods into space; in the game they lie along the doorway jamb. Judge them only in the in-game
  hinge captures (open and closed); defect only if they read as floating there.
- The worker's original-mount test is therefore consistent with what is drawn.

## Driver check of the promoted generated frame in game (slice2f/prev-before-after.jpg)
- Measured against round-11 captures: the close-up changes 29,886 of 2,985,984 pixels (1.0%); the bay
  door three-quarter 0.14%; edge-on 0.03%. The generated frame looks almost the same as the old one.
- Why: Andrew's proportions (80..100 mm band, <=30 mm proud, door flush) plus the old frame already being
  a rounded riveted band leave little room for the frame to change the look. The door, its hinges and the
  wheel fill most of the view, and those are still primitive-built.
- Consequence for the plan: finish verifying and checkpoint slices 1-2 (provenance and pipeline are
  needed anyway), but move straight to the door (slice 3, leaf3 seed 430) and wheel (slice 4); they are
  where the visible change is. Judge every later slice by a before/after pixel diff plus my own look,
  not only by gates.
- Hinge plates and the corner plate: not visible as defects in these views.

## Warning on the "1% change" finding (slice2f/guarded.log)
The guarded suite on the promoted asset reports hatch_model_test: "actual imported geometry matches the
freshly built asset: expected 39531, got 35478". 35,478 is the OLD c2a0157 triangle count. So the running
game (and very likely the slice2f captures) still loaded the old imported mesh, not the generated frame;
the bake-coverage (19,521 uncovered) and part-bounds failures fit the same stale-import explanation.
My 1% pixel-change conclusion is therefore unproven until captures are rerun after a confirmed reimport
(check .godot/imported/hatch.glb-*.scn hash/time, and that runtime triangle count = 39,531).

## Re-measured after the verified reimport (slice2f/prev-before-after2.jpg)
The worker found and fixed the stale import (fixed-import-1/2 + tally) and re-captured. Change against
round 11: close-up 2.76% of pixels, bay three-quarter 0.63%, edge-on 0.22%. Visually still almost the same
frame. The earlier conclusion stands: the door, hinges and wheel are where the visible change has to come
from; go to slice 3 next.

## Perf during slice-2 verification
The clean c2a0157 baseline itself failed the absolute perf policy (mean 25.0 ms, p95 102 ms) while another
session's `stranded --engine-capture` was running (pid 66175, ~96% CPU, GPU). That is external contention,
not our change; never signal it. Judge slice 2 by the three alternating baseline/candidate pairs (candidate
mean within the baseline's own spread) and record the contention with the numbers; rerun absolute perf
later on an idle GPU.

## Perf owed by 436071a: settled (perf2/report.md)
Five alternating pairs, no foreign GPU jobs, policy 10/10 PASS. Median mean frame 2.194 ms (c2a0157) vs
2.700 ms (436071a): +0.506 ms, inside the baseline's own 0.959 ms spread; p95 +3.5 ms inside the baseline's
6.4 ms spread. Both far below the 25 ms / 50 ms limits. No regression established.

## Driver decision after the slice-3 pre-scan (slice3/report.md): the rib becomes a physical leaf part
Conflict: the generated door's central vertical rib stands 19.9 mm (seed 430) proud of the broad face that
is registered to the 220 mm approach plane; no moving reservation owns it.
Decision: add the rib to sim/hatch_parts.gd as physical leaf parts on the approach face, like straps and
dogs: own IDs and local boxes, included in sight, swept/parked bounds and clearance, NO collider (closed
colliders stay 1,013; replay digests must stay unchanged, investigate any change). Size the parts from the
fitted source rib (depth = measured fitted relief, ~20 mm; width from the source); split around the wheel
boss and cut out of the label patch plus 30 mm (label X 0.13..1.11, Y 1.60..2.12 in the representative
frame), so it does not cross the wheel hub or the label. Check the wheel still clears the rib through its
full 270 degree rotation.
Rejected alternatives: recessing the broad face 20 mm behind the plane would push the face past the
<=30 mm flushness limit; flattening the rib into paint discards the generated relief that is the point
of this work.
Tests pinning the leaf part count (279 per variant) change only by the added rib parts, with this reason
stated in the test. Everything else in slice3-brief.md stands. If the pre-scan finds a further conflict,
report the full list; otherwise proceed to the build.

## Driver decision on the strap-hinge fit (slice3b/uniform-straps-red.log)
Finding: scaled uniformly to span the 400 mm strap, the generated straps come out thicker than the 55 mm
strap reservation: seed 430 needs scale >= 0.877/0.915 for the span but <= 0.727/0.705 for the thickness
(433: 0.886/0.914 vs 0.815/0.813).
Decision: hardware pieces (straps, dogs, keepers, rib) may be compressed in depth only, keeping their
in-plane scale uniform, provided the depth scale is at least 0.70 of the in-plane scale (seed 430 needs
about 0.83 and 0.77). Measure and report the ratio per piece and keep a test that pins it >= 0.70.
The 55 mm strap reservation, the swing clearance and every other gate stay unchanged. Rejected:
enlarging the strap reservation (changes the swing envelope and sight for every hatch) and shortening
the straps (the concept's straps run well across the door).
If the worker's stop report lists other conflicts, they come back to the driver together.

## Driver decision after slice 3c (upper strap depth bound 0.662 < 0.70)
The 0.70 floor was my own number, not one of Andrew's limits. The slice3c bound for the seed-430 upper
strap is conservative (it counts every vertex of every triangle touching the plate rectangle, including
slab and background), and it still allows a ratio up to 0.662. The difference between 0.66 and 0.70 of
natural depth is not visible on a strap that stands a few centimetres proud.
Decision: the hardware depth floor becomes 0.60 of the in-plane scale. Measure the actual fitted ratio
per piece on the raised skin only (not slab/background), pin it in a test (>= 0.60), and report it.
Below 0.60 for any piece: stop and report. The 55 mm strap reservation and all gates stay unchanged.

## Driver decision after the actual strap fits (slice3d/strap-fits.json)
Measured fits (raised skin, uniform in-plane scale to span the 400 mm strap): depth ratio 0.455 (430 upper),
0.516 (430 lower), 0.587 (433 upper), 0.660 (433 lower). The earlier 0.662 figure was a bound that assumed
the whole plate rectangle; the retained raised skin is smaller, so it needs a larger in-plane scale.
I have now set two floors that the source could not meet. A fixed ratio is the wrong control: the strap ends
up 55 mm proud either way, which is plenty of relief at play distance. What matters is whether the
squashed strap still reads as the concept's strap, and that is a visual judgment.
Decision: floor 0.40 (a guard against flattening into a decal), each piece's measured ratio recorded in
SOURCES.md and pinned by test to its built value +-0.01, and the driver judges the result in the clay and
in-game captures. If the straps read wrong there, the next step is to change the strap reservation size,
not the ratio.

## Driver watch item (slice3e/hardware-solved.log)
The seated solver fits small hardware pieces (bolts, necks, caps) with free 3D rotations, e.g. a bolt
rotated ~45 deg about two axes to fill its box. A generated fragment turned sideways to fill a box will read
as junk. Judge in the clay renders; if any piece is visibly tumbled, the rule for the next pass is: hardware
keeps the source's facing (front stays front, rotation only about the face normal), and a small piece that
cannot fill its reservation that way is drawn smaller inside its reservation rather than rotated.

## Slice 3e rejected (slice3e/prev-game.jpg, image-comparer-w9daoh)
In game the generated door body changed only ~4% of the close-up, while the hardware got worse: the top
strap/latch pieces read as a jagged merged bar and the bottom-right latch as a crumpled lump. The
image-comparer independently rated the current game (before) closer to the concept than the candidate.
Set aside as stash@{0}; tree back to 436071a.

Root cause: the slices cut the generated door mesh into the 279 primitive-era part boxes (24 strap subparts,
36 dog subparts, 96 rivets, 72 contour pieces) and forced each fragment to fill its box. Hunyuan does not
model those subparts; a lumpy region of the door scaled and rotated to fill a box is a lump. The frame worked
because it is one continuous form. The door body barely changes because the flat slab is dominated by the
paint atlas.

Decision: the unit of generation becomes the whole object, not a slice of the door.
- Prototype first (no production change): generate each hardware type as its own object from its concept
  crop (strap hinge; latch dog with keeper; the handwheel), isolated on a plain background, Hunyuan
  full model, octree 512. Judge clay renders against the concept crops before any fitting.
- If the pieces are legible, the hardware reservations in the sim are re-sized from the generated objects'
  proportions (uniform scale, no squashing), with collision/sight/swing tests rerun unchanged; Andrew's
  proportions (frame band, flushness, slab thickness) stay fixed.
- If Hunyuan cannot produce legible small hardware at that resolution, say so to Andrew with the renders;
  the alternative is modelled hardware in Blender to the concept's proportions on the generated frame
  and door body.

## Parts prototype inputs (parts-proto/prev-inputs.jpg)
FLUX isolation worked: clean strap hinge (plate, knuckle, bolt holes), clean latch dog with pivot boss,
clean handwheel. Two differences from the concept to remember: the isolated wheel has 5 spokes where the
concept and the game have 6, and the hazard band was dropped (the band stays a separate game part anyway).
Judge spoke count in the meshes; a 5-spoke wheel would need a re-edit before use.

## First whole-object result (parts-proto/prev-hinge600.jpg): legible
Strap hinge seed 600 (octree 512, 634 s, 1.08M faces before reduction) is a clean, recognisable part from
every angle: rounded plate with four bolt holes, full-length knuckle barrel, folded strap returning to the
barrel. Nothing like the slice-3e lumps. It is a short plate hinge crossing the seam, as in the concept,
not the game's 400 mm strap; when fitting, the reservation follows this object's proportions.

## Hinge pick (parts-proto/prev-hinges.jpg)
All four hinge seeds are clean and nearly identical except 602, whose plate stands far off in depth
(reads as a bracket, rejected). Pick: seed 600 (clearest bolt holes and folded strap), alternate 603.
Latch seed 600 (parts-proto/prev-latch600.jpg): legible from every angle - pivot barrel, flat arm with a
rounded end, raised boss, a small block on top. Matches its input. Waiting for seeds 601-603 before picking.
Latch pick (parts-proto/prev-latches.jpg): all four seeds clean and nearly identical. Pick seed 601
(fullest boss and clearest pivot barrel edge-on), alternate 600.
Wheel seed 600 (parts-proto/prev-wheel600.jpg): clean rim, spokes and hub, readable edge-on with a hub
boss both sides. But it has 5 spokes, copied from the FLUX isolation; the concept and the game wheel have
6. Decision: keep the generated rim/hub/spoke forms and make it six-fold in Blender (one generated spoke
plus its rim sector, repeated at 60 degrees, hub kept whole). That is an edit of the generated model, not a
primitive replacement. Pick the seed after all four finish.

## Hardware picks final (parts-proto/prev-wheels.jpg)
All 12 meshes exist (worker hit its 2 h limit just before writing sheets/DONE; meshes, renders, recipe.md
and stats.json are complete). Wheel: all four seeds clean, all 5-spoke. Pick wheel seed 600 (roundest rim,
hub boss both faces), alternate 602, to be made six-fold in Blender as decided.
Final picks: hinge 600 (alt 603), latch 601 (alt 600), wheel 600 (alt 602). Door body + rib: leaf3 seed 430.

## Driver decisions after the slice-3 v2 pre-scan (slice3v2/report.md)
1. Hinge axis. The game's hinge axis sits 220 mm behind the approach face, inside the jamb; that was laid
   out for the primitive-era long strap arm. The concept's hinges are surface hinges: one leaf on the frame,
   one on the door, the barrel at the seam on the face. No uniform scale of the generated hinge can reach a
   buried axis (153 mm deep at the largest possible scale vs 220 mm needed), and stretching it would bring
   back the distortion we just rejected.
   Decision: move the hinge axis to where the concept puts it - on the approach side at the seam between
   frame ring and door edge, at the generated barrel's centre at concept scale - in the sim (door hinge
   frame / HatchParts), for every hinged hatch. The swing changes accordingly. Every swing/clearance/seal/
   sight/label/budget gate stays as written and must pass with the new axis; collider count stays 1,013.
   If open-door solids change, the scenario captures and replay digests are regenerated through their
   compilers (as when the connector digest changed before), with all beats, checks and budgets unchanged;
   record the before/after digests and why.
2. Hinge leaves. A surface hinge has a fixed leaf and a moving leaf. Split the generated hinge once, at the
   barrel axis plane: the frame-side leaf is a fixed frame part (replacing the c2a0157 presentation-only
   frame knuckles/plates), the door-side leaf and barrel move with the door. One clean cut per hinge, no
   other cutting.
3. Scale from the actual silhouette. Measure each object's silhouette in the concept (not the generous
   crop) for its scale. If the upper hinge then still sits within 30 mm of the label, move the hinge
   station down until it clears; the label does not move.
4. Wheel clearance uses the actual vertices' radial bound, not a rotating box (design section 2 already
   says so). Describe the wheel as one part with a radial clearance.
5. Parked-reservation changes follow from 1-3 and are expected; they must pass the unchanged clearance
   gates, and any digest change is handled as in 1.

## Driver decision after slice-3 v2 attempt 2 (slice3v2b/report.md): keep the proven axis
Moving the axis to the approach face fails clearance in both swing directions for the 220 mm slab (all 90
sensitivity cases). Decision 1 of the previous section is withdrawn; the existing axis stays (ship-layout.md:
the layout fixes hinge side and swing direction into the connector; the hinge stands 0.30 m off the
wall-band centre toward the swing space). Swing, stops, pockets, parked solids and digests are unchanged.
Why this still matches the concept: a door's hinges are on the side it swings toward. The concept shows the
pull side. Our hatches swing into the connector, so the surface hinges belong on the swing-side face, with
the generated barrel on the existing axis and its two leaves on the frame and on the door's swing-side
face. From the push side (section side) no hinges show, as on a real door; the old design's straps on both
faces were the primitive-era workaround.
So: hinges (s600, split once at the barrel) only on the swing-side face, barrel coaxial with the existing
axis, scaled from the concept silhouette; latches (s601) on both faces at the existing dog stations; the
wheel (s600 made six-fold) on both faces as now; door body + rib from seed 430. If the generated hinge
leaf cannot reach from the axis to the swing-side face at concept scale, report the distance; do not
stretch it.

## Slice 3 v2 attempt 3 (slice3v2c/report.md): hinges blocked, needs Andrew
The existing axis is 40 mm INSIDE the door slab behind its swing-side face. A surface hinge's barrel sits
in front of the face it is screwed to, so with the barrel on this axis its leaves end up behind the axis,
inside the door, for every positive scale. Moving the axis out to the face fails swing clearance for the
220 mm door in both directions (attempt 2). The thick door (Andrew's >=160 mm leaf) and the concept's
flat surface hinges are kinematically incompatible. This is a product choice for Andrew (thinner leaf,
stand-off hinge brackets, or no visible hinges), asked 2026-11-06.

Meanwhile, not blocked: latches, wheel and door body. Scales: silhouette isolation by GrabCut was unstable
(reported), so use the game's already-proven sizes instead of new concept measurements - the wheel at the
current 0.888 m rim diameter, each latch scaled so its arm length matches the current dog arm length.
Hinges keep the current production parts until Andrew answers.

## Driver decision after slice3v2d (wheel spokes sweep through the middle latch)
Measured the concept on a pixel grid (slice3v2d/concept-wheel-grid.png, image-comparer-0sqp0y):
outer rim x 555..865, y 365..715 px (~330 px, +-8) and hub (710,540); the latches are at x ~425..500, all
LEFT of the rim's left edge (555), i.e. clear of the wheel, about 210 px (0.41 m) from the hub.
At 1.949 mm/px the concept wheel is ~0.64 m across, not the game's 0.888 m (round-7 choice), and the
concept's latch pivots sit ~0.14 m in from the free edge, not 0.31 m. The conflict comes from the game's
oversized wheel and inboard latch stations, not from the generated parts.
Decision:
- Wheel outer diameter 0.643 m (330 px x 1.949 mm/px), uniform scale; the hazard band part scales with it
  (same proportion of the rim as now). Wheel centre stays where it is.
- Latch stations move toward the free edge so each pivot sits 0.14 m in from the free edge (concept
  position); heights unchanged. The frame keepers move with them (whole parts, repositioned, no reshaping).
- Wheel clearance by actual-vertex radial bound; latch-to-rim clearance must be positive through the full
  crank rotation; everything else unchanged (parked boxes, colliders 1,013, digests). If the smaller wheel
  still cannot sit inside the parked reservation, report the numbers.
- Parked collision: the open door's parked box is derived from the leaf's parts, so new hardware sizes move
  it (slice3v2d measured up to 29.3 mm). That is expected: keep the derivation as it is, let the parked box
  follow the new parts, and require every clearance gate to pass with it. If open-door solids change, the
  scenario captures and replay digests are regenerated through their compilers (all beats, checks and
  budgets unchanged), with before/after digests and the reason recorded. Closed colliders stay 1,013.

## Driver decision after slice3v2e (latch tip past the free edge; keepers off the frame)
1. Latches: keep the inherited arm alignment (arm pointing toward the free edge and the keeper, as a dog
   engages). Rotating it instead points the arm at the wheel or stands it vertical, which the concept does
   not show. Move each pivot inward just enough that the whole latch clears the stop/ring reservations by
   5 mm (the 0.14 m figure ignored the latch's 33 mm overhang past its pivot). Expected inset about 0.18 m;
   if it needs more than 0.22 m, or wheel clearance falls below 20 mm at the middle station, stop and report.
   The concept latches span roughly 80..225 mm in from the free edge, so ~0.18 m still matches it.
2. Keepers: my earlier note to move them with the pivots was wrong. Keepers are fixed on the frame; the
   latch moved on the door, not the frame. Keepers stay exactly where they are now, unchanged.

## Driver decision after slice3v2f (upper latch in the rounded crown)
Lower and middle latches fit at a 193.6 mm inset. The upper latch at 2.24 m sits where the aperture's
0.24 m corner radius curves in, so it needs 283 mm. Moving the pivot further toward the wheel is the wrong
fix; the latch is in the wrong place. In the concept all three latches sit on the straight part of the
edge, around the wheel's height band, none in the curved corner.
Decision: lower and middle stations unchanged (0.40 m, 1.17 m) at the 193.6 mm inset. The upper station
moves down to the highest height that (a) passes the 5 mm stop/ring gap at the same 193.6 mm inset and
(b) keeps the whole latch 30 mm clear of the label rectangle (unchanged label). If no height between the
middle station and the crown meets both, use the highest that meets (a) and lies below the label by 30 mm;
report the height chosen and why. All three latches use one inset.

## Driver decision after slice3v2g (generated hub has no hex nut)
Latch placement is solved: inset 193.619 mm, stations 0.40 / 1.17 / 1.496046 m (the upper one sits just below
the label; above it the crown fails by 54 mm). The three latches cluster around the wheel's height, which is
also how the concept places them. Accepted.
The hub test's six-corner retention nut was added in an earlier round because the hub read as a soft blob at
play distance; the generated hub's front is a rounded dome, so it fails that test. Keep the test. Decision:
keep the generated hub whole and seat the game's existing hex retention nut part on its front, as one whole
part, scaled by 0.643/0.888 like the hazard band, seated where the dome's cross-section is at least the nut's
across-corners width so it reads as screwed onto the hub (no floating gap, no burying beyond its chamfer).
The nut turns with the wheel. Every hub test, including the 8 mm relief and chamfers, stays unchanged.

## Driver decision after slice3v2h (nut cannot seat on the whole dome)
The scaled nut is 137.6 mm across corners, about 21% of the 643 mm wheel, which is also the size of the hub
boss in the concept. The generated hub's narrow pointed dome is the part the concept shows as that boss.
Decision: one planar cut, perpendicular to the wheel axis, through the generated hub at the outermost plane
where its section reaches the nut's across-corners width; remove the dome beyond it; seat the whole nut on
that flat face. That cut and the six-fold sector repeat are the only edits to the wheel. Record the cut depth
on each face. Every hub test (six corners, chamfers, 8 mm relief) stays unchanged.
