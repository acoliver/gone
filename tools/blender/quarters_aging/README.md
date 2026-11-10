# Quarters geometry aging

## Sofa pass 11: rejected, 14 of 22 gates pass

The fixed reference is `docs/art/quarters/sheets/sofa/aged-target.png`: this
sofa after 1000 years. Ignore its wall socket and wall corner. The final
candidate remains a scratch export at `tmp/age/pass11/final-fringe/sofa-preview.glb`.
The game GLB, shipped textures and fitted Blender source remain unchanged.
The requested visual result is not achieved.

### Measurement findings and geometry changes

The previous contour decoder required nearly pure red or green pixels. It
classified antialiased cloth/fringe mixtures as holes. On the retained centre
back, strict labels reported eleven enclosed holes; combined cloth coverage
reported two. The sofa now decodes combined R+G coverage before tracing the
visible alpha/lip boundary near physical tear components. Open lips are not
closed with a synthetic line. Constant-width open and closed slot controls
still fail the unchanged 12 px limit. G4 retains 0.35; G6 retains 1.15 to 1.40
on contours at least 64 px across. Existing seam gape/fringe requirements
remain required and cannot be bypassed by the panel-outline result. This
agrees with the R+G finding recorded in the tunic README's shared-code section.

The retained pass-10 solve is the source. Enclosed small wear holes are
patched, detached specks removed, and one broad physical gash is cut into each
seat front and each back seam. Seat openings span 17.95 to 24.99 cm and are
7.48 to 10.73 cm wide; back openings span 11.98 to 13.99 cm and are about
6.8 to 7.0 cm wide. Each has a closed, nonplanar 144-triangle tan foam core.
Rear-fold depth limits avoid cutting through the entire back cushion.
Existing slit-like damage is not completely removed, and the captures still
show substantially less broad foam exposure than the target.

Each seat receives its own shallow bowl while its already-collapsed middle
stays above its support. The backs are pitched forward by 15/14/12 degrees
and their ties lowered, without scaling the envelope. After cutting and
finishing, back area is 101.235/100.521/100.659% of the retained source,
within the unchanged 97% to 103% control. This is explicit finishing of a
retained solve, not a new gravity simulation. A 14 cm physical split is cut
at the throw's arm crease; the hanging sheet remains connected.

The new openings add protected boundary vertices, increasing the pressure
on reduction and exposing seat faceting. Source and reduced surfaces receive
bounded fairing. The right-back G1 defect is fixed, at 5.644% versus 8%, but
all three seats now fail G1. The contact finish also fails to converge:
335/316/341 crossings before export, with 362 in the exported asset. These
include 285 back/seat crossings, 26 right-back/throw crossings, eight frame/
centre-seat crossings and 43 changed self crossings. Rigid baseline counts
remain exact. No pair or cloth region is excluded.

Debris uses eight reductions of the existing cut-fragment templates, with
nine hull vertices and fourteen triangles each. All 198 exported fragments
are measured directly rather than accepted from template metadata. There
are 42 floor fragments, versus pass 10's 18, with broader supported powder
cards. Lit first-hit hero crumb pixels increase from 42 to 275, and seat-front
pixels from 17 to 253. Floor distribution and radial falloff still pass.
Despite that increase, image-comparer finds the seats and floor too sparse.

Fringe is sampled at physical arclength rather than once per tiny cut edge.
Twenty thin bundles per card vanished under MASK mip filtering, despite
being present in the export. A failing hero-scale filtering control exposed
this. Eight wider bundles pass that control and affect the lit capture.
Pure-green diagnostic pixels also discarded antialiased fringe coverage.
The corrected measurement subtracts cyan crumb coverage from green coverage
and still requires an eight-level disabled-effect difference: 312.075
coverage-weighted first-hit pixels pass that condition. This does not certify
the target's frayed-lip appearance. The geometry budget stays at 28,697
triangles. Compact residue reduction leaves a visible planar patch on the
right seat, so G7 regresses. Float64 barycentric clearance transfer prevents
unstable skinny-triangle weights, but final boundary error still reaches
2.317 mm and fails G32.

### Final measurements

Seat and back triplets are centre/left/right. G20 to G29 are tunic-only.
Per-opening samples, unresolved contours and all per-part values remain in
`tmp/age/pass11/final-fringe/gates.json`, mirrored to `tmp/age/pass11/gates.json`.
Every numeric threshold is retained.

| Gate | Final measured value | Threshold | Result |
| --- | --- | --- | --- |
| G1 | Sharp pairs: seats 11.887/10.473/8.276%; backs 6.809/4.046/5.644%; throw 8.583% | Covers <=8%; throw <=9% | Fail |
| G2 | Largest normal-jump fraction 1.094% | <=2% each | Pass |
| G3 | Longest visible runs: seats 74.061/47.671/76.059 px; backs 45.260/34.234/64.070 px; throw 7 px | <=12 px; seam gape/fringe still required | Fail |
| G4 | Minimum paired CV: seats 0.070/0.135/0.250; backs 0.044/0.042/0.168; throw unpaired | >=0.35 each; missing measurement fails | Fail |
| G5 | Lifted lip length: seats 40.289/27.557/36.077%; backs 32.112/36.609/32.884% | >=30% above 3 mm each | Fail |
| G6 | Resolved contour dimensions span 0.932 to 1.236; throw has no resolved contour | 1.15 to 1.40 each; one resolved contour per part | Fail |
| G7 | Visible planar residue: seats 0/2.225/8.176%; backs 0/0/0% | <=5% each | Fail |
| G8 | Dense crust RMS: seats 1.850/1.675/1.910 mm; backs 3.074/3.034/2.913 mm; maps present | >=1.5 mm and normal map | Pass |
| G9 | Eight templates, 198 exported crumbs, fourteen triangles each | >=8 templates; 14 to 40 triangles, not 20; thickness/width 0.25 to 0.70 | Pass |
| G10 | R 1.252140; largest cluster 0%; 42 floor crumbs | R 0.8 to 1.4; cluster <=20% | Pass |
| G11 | Radial rho -1/-1/-1; supported powder per spill | rho <=-0.6 and powder present | Pass |
| G12 | Hero/front boxing: centre 0/0%; left 3.206/1.831%; right 1.173/0.623% | <=25% each camera | Pass |
| G13 | Rounded-box RMS 12.799/19.728/16.693 mm | >=12 mm each seat | Pass |
| G14 | Seat centre-height retention 17.694/11.921/11.417% | 10% to 25% each | Pass |
| G15 | Back height retention 58.214/57.153/60.891% | 40% to 65% each | Pass |
| G16 | Back residue in lowest third 98.765/98.824/98.428% | >=60% each | Pass |
| G17 | Back front folds 2/2/2, >=8 mm prominence | >=2 each | Pass |
| G18 | Arm-crest split 89.298% | 60% to 90% | Pass |
| G19 | One connected arm-to-near-floor sheet; four folds; 76.153 mm above floor; zero arm gap | >=3 folds; <=250 mm arm gap; hang <=100 mm above floor | Pass |
| G30 | 362 changed crossings; rigid Frame self 522 and Frame/Rivets 272, exact baseline | Zero changed; rigid counts equal unaged | Fail |
| G31 | 28,697 triangles; 1.467877 times fitted | <=29,325 and <=1.5 times fitted | Pass |
| G32 | Seat boundary errors 1.976/1.184/2.065 mm; backs 1.867/2.317/1.727 mm; throw 0.526 mm | <=1.5 mm each | Fail |

### Captures, review and verification

The before/after, turntable and 0.6 m close-up retain the pass-10 cameras.
`sofa-target-match.png` places a new target-angle render beside the complete
1024 by 1024 reference. Its angle is an approximation from the fitted hero;
the generated target has no measured camera metadata. Image-comparer notes
that the candidate is still viewed from too high an angle.

The four requested outputs are `tmp/age/pass11/sofa-before-after.png`,
`sofa-turntable.png`, `sofa-closeup.png` and `sofa-target-match.png`. Their
headers identify a rejected, unshipped candidate. The full corresponding
run, raw captures and visual review stay under `tmp/age/pass11/final-fringe/`.
The renderer preserves exported materials; its optional argument defaults
to the previous behavior for existing callers.

Image-comparer estimates a 38% target match and recommends rejection.
It finds narrow or fragmented tears, limited tan foam exposure, sparse
debris, uniformly bowl-shaped seats, blockier backs and no convincing arm-
crease split. It also reports upholstery/frame color and camera differences.
These are visual judgments, not measured gate values. The requested damage,
debris and collapse appearance remains unfinished even where numeric gates
pass. The next geometry work must improve those visible features while
removing the new contacts, seat faceting and boundary drift.

The final focused and regression checks pass 51 tests: six contour/coverage,
seven mesh, five fringe/foam/fragment, fourteen acceptance, three collision-
policy and sixteen pass-10 tests. Python compilation and diff whitespace
checks pass. Acceptance exits 1 because eight gates fail. Fixed rigid geometry,
origins, byte-identical re-export, retained source simulation records, no
self-collision exclusions, exported fringe, lit fringe/crumb coverage and
back-area retention pass. Retained simulation records do not establish a
new settled solve after the explicit pose edits. No game asset is published.

## Sofa pass 10: rejected, 18 of 22 gates pass

Pass 10 retains pass 9 (`bdd5171`) as its cloth-simulation base. The work
repairs the retained throw corner, fairs reduced covers without moving their
open boundaries or stitches, adds tan residue with local cavity shading, and
adds smaller deposited fragments and fine powder. Scratch previews are not
shipped assets. `sofa_aged.glb`, its shipped textures, and the fitted Blender
source remain unchanged.

### Root causes and retained limits

The same-camera face-ID comparison separates geometry from shading. Visible
sharp-pair percentages on the unmodified pass-9 dense/game surfaces are:

| Part | Dense | Reduced |
| --- | --- | --- |
| Centre seat | 2.929% | 8.134% |
| Left seat | 3.926% | 10.786% |
| Right seat | 3.417% | 8.940% |
| Centre back | 4.940% | 9.111% |
| Left back | 8.934% | 15.400% |
| Right back | 6.082% | 8.233% |
| Throw | 14.469% | 19.749% |

Reduction is the main faceting source on five covers. The left back and throw
also contain above-limit sharp geometry before reduction. These face-ID
measurements do not depend on baked normal maps. Whole-sheet sharp shares
are higher, but are not substituted for the visible-pair gate. Bounded
one-ring fairing preserves boundaries and retained stitches and transfers
the resulting displacement back to the dense bake source. The centre and
right backs use paired smoothing/expansion steps to retain broad folds.
The left back permits up to 8 mm of displacement; the other cloth permits
6 mm. A 2,150-triangle right-back reduction still has 8.436% visible sharp
pairs and loses one of its two qualifying front folds. That trial is rejected;
the final right back retains the pass-9 2,000-triangle topology.

The throw crossings are a fold pinched around retained stitches. Both the
dense and reduced solved meshes cross there; the prepared dense mesh does
not. Crossing triangles have ordinary millimetre-scale edges, rather than
an isolated sliver. The repair restores the nearby prepared fold inside a
22 mm radius, blends into the solved hang by 55 mm, and leaves the retained
stitches fixed. It then rebuilds the reduced throw and applies normal
contact clearance. No collision pair is excluded.

The dark residue had two causes: a dark brown provisional diffuse colour
and a surrounding-cover AO bake with median zero in the inspected centre
seat and back atlases. Residue now uses linear tan-brown (0.32, 0.18, 0.075),
roughness 1, and an 8 mm residue-only cavity bake. Cavity modulation retains
55% diffuse contribution at maximum occlusion. Seat crust gets continuous
three-axis relief and explicit shallow relief on broad planar top patches.
This removes the near-black insert treatment; the captures still determine
whether the residue reads as crumbs.

Editing packed cover images left stale embedded PNG alpha. A regression
reloads the packed payload after unpack/edit/save/repack. Rasterized
stress openings also had inconsistent noise between parallel plies; noise
is now evaluated in their shared opening plane. The old fixed erosion cap
is replaced by a continuous surface-space torn-edge field. These changes
improve exposure but do not establish acceptable tear contours or lifted,
fibrous borders everywhere. The throw opening remains an acceptance result,
not an assumed success from its authored mask.

Non-floor fragments use a 4 mm median instead of pass 9's 11 mm. Fine grain
cards are contact-fitted below openings and on the floor, with open alpha
between grains and small agglomerates that survive minification. The 18
pass-9 floor fragments and their sampling record are retained, preserving
the floor-distribution control. The shared powder-card function keeps its
48-sector default; only the additional sofa floor cards request 16 sectors.
The final supported fine cards retain 30/48/27 seat triangles, three right-back
triangles, and 16 triangles per floor spill. The centre/left-back fine cards
are rejected by support/contact clipping, so fine deposition there remains
unfinished. The local hold repair moves 82 vertices, by at most 35.001 mm.
Contact clearance then converges through 10/6/0 changed crossings.

More back collapse was tested rather than assumed safe. A finer continued
centre-back trial loses the 97% area floor by frame 60. The retained coarse
backs with softer bending, a 1 mm contact shell, and stronger pressure fail
the same control on the left back at frame 240 (95.737% area). Neither trial
is adopted. Pass 9's settled collapse remains the base; broad seat slabs,
pillow-like back volume, and uneven apparent sag are not claimed fixed.

### Verification and captures

The final Blender regression run passes 34 cloth, lip, pass-8, pass-9 and
pass-10 tests. The Python acceptance, image-gate and collision-policy run
passes 18 tests. No acceptance assertion or threshold is relaxed.

The matching-camera outputs are `tmp/age/pass10/sofa-before-after.png`,
`tmp/age/pass10/sofa-turntable.png`, and `tmp/age/pass10/sofa-closeup.png`.
They use the pass-9 renderer and remain provisional-material diagnostics.
`tmp/age/pass10/gates.json` retains all per-opening values; G20–G29 are
tunic-only. The preview GLB stays under `tmp/age/pass10/`.

Image-comparer, configured with `gpt-6-luna`, inspected all six matching
pass-9/pass-10 captures. Within this comparison it scored pass 9 at 4/10
and pass 10 at 5/10. Tan residue and throw wear are more visible, but broad
seat shells, inflated backs, abrupt or slot-like tears, and sparse angular
debris remain. Fine powder is not visually established. This candidate
has no art acceptance. The full findings remain in
`tmp/age/pass10/final-visual-review.json`.

### Final pass-10 measurements

The final preview passes **18 of 22** gates, up from pass 9's 15. G5, G7
and G30 now pass, and every collapse gate G12–G19 still passes. G1, G3,
G4 and G6 remain failures. The acceptance command exits 1 as expected for
this rejected candidate. Seat and back triplets below are centre/left/right.
The face-ID control above and final alpha-aware acceptance have different
material visibility; their percentages are not interchangeable.

| Gate | Final measured value | Threshold | Result |
| --- | --- | --- | --- |
| G1 | Visible sharp pairs: seats 5.008/6.874/3.956%; backs 6.783/7.873/9.427%; throw 7.060% | Covers ≤8%; throw ≤9% | Fail |
| G2 | Normal jumps: seats 0.605/0.659/0.627%; backs 1.846/1.902/1.558%; throw 0.037% | ≤2% each | Pass |
| G3 | Longest panel-tear runs: seats 16.000/28.399/26.173 px; backs 19.300/21.225/10.198 px; throw absent; seam gape/fringe requirements still fail | ≤12 px / 4.5 mm, with seam gape and fringe | Fail |
| G4 | Minimum width CV: seats 0.361/0.327/0.305; backs 0.368/0.488/0.429; throw absent | ≥0.35 each opening, with an opening per part | Fail |
| G5 | Lip length lifted >3 mm: seats 30.921/45.144/52.602%; backs 30.574/46.749/43.393% | ≥30% each | Pass |
| G6 | Resolved contour ranges: seats 1.128–1.223 / 1.061–1.321 / 1.136–1.266; backs 1.105/1.118/1.195; throw absent | 1.15–1.40 every resolved contour, with one per part | Fail |
| G7 | Visible large planar residue: 0% on all six parts | ≤5% each | Pass |
| G8 | Dense crust RMS: seats 1.860/1.678/1.926 mm; backs 2.935/2.948/2.977 mm; normal maps present | ≥1.5 mm and map | Pass |
| G9 | Eight cut templates, 24 triangles each, thickness/width 0.2663–0.4592 | ≥8; 14–40 triangles, not 20; ratio 0.25–0.70 | Pass |
| G10 | Clark-Evans R 1.007235; largest cluster 0%; 18 floor crumbs | R 0.8–1.4; cluster ≤20% | Pass |
| G11 | Radial-density rho -1/-1/-1; powder per source | rho ≤-0.6 and powder present | Pass |
| G12 | Hero/front boxing ratios: centre 0/0%; left 10.376/6.322%; right 3.534/2.099% | ≤25% in each camera | Pass |
| G13 | Rounded-box RMS 13.162/18.252/18.522 mm | ≥12 mm each seat | Pass |
| G14 | Seat centre-height retention 17.318/12.129/11.178% | 10–25% each | Pass |
| G15 | Back height retention 64.793/58.390/59.683% | 40–65% each | Pass |
| G16 | Back residue in lowest third 100/100/100% | ≥60% each | Pass |
| G17 | Back front folds 2/2/2, each ≥8 mm prominence | ≥2 each back | Pass |
| G18 | Arm-crest split 89.298% | 60–90% | Pass |
| G19 | One connected pinned-corner sheet; 0 mm from arm; four folds ≥10 mm; lowest point 76.153 mm above floor; no detached remnant | ≤250 mm from arm; ≥3 folds; connected arm-to-near-floor hang ≤100 mm; ≤1 remnant | Pass |
| G30 | Zero changed intersections; rigid baseline exact: Frame self 522, Frame/Rivets 272, other rigid counts zero | Zero changed; rigid counts equal unaged | Pass |
| G31 | 28,958 triangles, 1.481228 times unaged | ≤29,325 and ≤1.5 times unaged | Pass |
| G32 | Dense/game boundary upper bound ≤0.1251 mm on all seven cloth parts | ≤1.5 mm | Pass |

Fixed rigid geometry bytes, origins/pivots, byte-identical re-export,
retained all-six simulation and settled records, no self-collision
exclusions, exported fringe nodes, lit hero fringe/crumb visibility and
seat-front crumb visibility all pass. These checks do not establish adequate
fine powder coverage or remove the remaining visual defects.

## Sofa pass 9: collapse improves, candidate still rejected

Pass 9 continues pass 8 (`5a16e5b`). The candidate passes **15 of 22**
sofa gates, compared with 11 in pass 8. Seat height, back height, throw reach
and folds, boundary accuracy, and stillness now pass. Faceting, tear shapes,
one back lip-lift result, right-seat residue planarity, and throw self-contact
still fail. `assets/props/quarters/sofa_aged.glb`, its shipped textures, and
the shipped Blender source remain unchanged. Preview export is scratch only.

### Causes and controls

The tied back covers had no remaining filling-loss driver after pass 8
removed the stretching envelope. Gentle inward pressure alone left the side
boxing supporting the pillow. Two zero-area side releases let each cover
fold while retaining the existing rear tie vertices. Blender's automatic
initial-volume term also opposes collapse, so the sofa-only setup explicitly
uses a zero pressure-volume target. Pressure ramps from zero at frame 1 to
-0.01 at frame 40 and -0.65 at frame 180. These are Blender pressure settings,
not a measured physical vacuum. Residue stays static in the lower return.
No animated back collider or self-collision exclusion was introduced.

The final 40-frame control ran before the joint-back solve. Its frame-20
sharp share is **4.738%**, below 5%; sampled area is **99.916–100.000%**,
within 97–103%; initial SAT contacts are zero. The earlier C1–C5 controls
remain passing. The production back solve preserves 99.387–100.005% area
across its per-cover checks. Back height reaches 64.793/58.772/59.683%,
with all residue in the lowest third and two qualifying front folds each.

Seat bending softens after the early controls, over frames 200–600. Immediate
softening was rejected by the area/motion controls. The final seats retain
16.555/11.357/10.944% centre height and no longer retain the left boxing
failure. Their sampled per-cover areas stay at 99.565–100.000%.

The fringe failure had two demonstrated causes. Sparse single-pixel atlas
yarns disappeared under the exported 0.5 alpha cutoff after minification,
and editing an already packed image left its earlier PNG payload in place.
The new material uses tapering yarn bundles with over 55% root coverage,
unpacks before editing, then saves and repacks. A regression compares the
reloaded packed alpha with the edited pixels. Backface culling remains off;
contact-tested placement remains enabled. The final close diagnostics now
contain 240/139/259 seat, 106/70/154 back, and 1,356 throw fringe pixels.
The broad hero still resolves only 14 first-hit fringe pixels,
12 with at least eight RGB levels of lit contrast against the disabled-fringe
control. That proves visibility, but does not establish sufficient visual
coverage or satisfy the failed seam/tear gates.

Opposing tear lips now curl into their own connected panels. A nearest-point
field could associate coincident lips with the wrong panel and close a tear.
The topological curl regression checks that the two sides separate. This
change does not fix every opening: centre-back lifted lip length is only
28.157%, and several openings remain too straight or unresolved in the
unchanged diagnostics.

Crumbs were mostly hidden below the cover, and their previous 5 mm median
size gave little broad-view coverage. Sofa-only visible deposition includes
the solved seat covers as landing supports and uses an 11 mm median for
non-floor fragments. Floor sampling and its thresholds are unchanged.
The final hero has 275 first-hit sofa crumb pixels, all with at least eight
levels of lit contrast, including 160 at the seat fronts. G9–G11 still pass.
The new deposition argument is optional; existing callers retain their
previous behavior.

G32's 3.125 mm seat error came from repairing only the reduced mesh after
baking-source capture. The same barycentric clearance field now deforms the
dense source and the game mesh. The measured boundary bound is 0.125 mm for
all seven cloth parts. Seat SAT clearance reaches zero after one repair.

The throw retains only its outer rear arm corner, rather than the broad cap
hold. It reaches 76.153 mm above the floor with five folds of at least 10 mm
prominence, and remains one connected arm-to-near-floor sheet. The crest
split length passes G18, but its visibility along the arm is not signed off.
The final throw fails G30 with **eight self-intersections**, all in wool near
the retained corner (approximately x 1.109–1.115 m, y 0.124–0.135 m,
z 0.750–0.760 m). Clearance counts 10/9/6/8 did not converge. This local
contact regression is unresolved; no contacts were excluded to pass it.

Solves allow 2,400 frames and ramp air damping to six times its initial
value over frames 300–600. All three satisfy the unchanged requirement of
three successive checks below 1 mm over five frames: seats stop at frame
1,550 with 0.481 mm final motion; backs at 925 with 0.977 mm; throw at 750
with 0.190 mm. A larger damping trial was rejected rather than using drag
to conceal an unfinished collapse.

### Final measurements

Values are from `tmp/age/pass9/gates.json`. Triplets are centre/left/right.
Missing resolved openings count as failures. G20–G29 remain tunic-only.
No acceptance thresholds or rigid-baseline allowances were relaxed.

| Gate | Measured value | Threshold | Result |
| --- | --- | --- | --- |
| G1 | Visible sharp pairs: seats 8.283/10.744/8.986%; backs 9.283/15.619/8.317%; throw 19.789% | Covers ≤8%; throw ≤9% | Fail |
| G2 | Normal jumps: seats 0.728/0.722/0.712%; backs 1.400/1.629/1.623%; throw 0.251% | ≤2% each | Pass |
| G3 | Longest panel-tear runs: seats 27.203/28.714/33.526 px; backs 19.300/16.031/20.797 px; throw absent; seat seam gape/fringe also fails | ≤12 px / 4.5 mm; seams require gape and fringe | Fail |
| G4 | Minimum width CV: seats 0.4530/0.2879/0.3532; backs/throw absent | ≥0.35 each opening, with a measured opening per part | Fail |
| G5 | Lip length lifted >3 mm: seats 35.369/55.360/49.235%; backs 28.157/36.983/51.304% | ≥30% each | Fail |
| G6 | Resolved contour ranges: seats 1.1688–1.2443 / 1.0560–1.3102 / 1.1224–1.3381; backs/throw absent | 1.15–1.40 each resolved contour, with one per part | Fail |
| G7 | Visible large planar residue: seats 2.699/4.935/6.159%; backs 0/0/0% | ≤5% each | Fail |
| G8 | Dense crust RMS: seats 1.848/1.680/1.914 mm; backs 2.935/2.948/2.977 mm; all normal maps present | ≥1.5 mm and normal map | Pass |
| G9 | Eight cut templates, 24 triangles each, thickness/width 0.2663–0.4592 | ≥8; 14–40 triangles, not 20; ratio 0.25–0.70 | Pass |
| G10 | Clark-Evans R 1.007235; largest cluster 0%; 18 floor crumbs | R 0.8–1.4; cluster ≤20% | Pass |
| G11 | Radial-density rho -1/-1/-1; powder present per source | rho ≤-0.6 and powder per source | Pass |
| G12 | Hero/front boxing ratios: centre 0/0%; left 0/0%; right 3.059/2.413% | ≤25% in each camera | Pass |
| G13 | Rounded-box RMS: 13.591/18.467/19.215 mm | ≥12 mm each | Pass |
| G14 | Seat centre-height retention: 16.555/11.357/10.944% | 10–25% each | Pass |
| G15 | Back height retention: 64.793/58.772/59.683% | 40–65% each | Pass |
| G16 | Back residue in lowest third: 100/100/100% | ≥60% each | Pass |
| G17 | Back front folds: 2/2/2 | ≥2 each, ≥8 mm prominence | Pass |
| G18 | Crest split 89.298% | 60–90% | Pass |
| G19 | One connected arm-to-near-floor sheet; 0 mm footprint distance; lowest point 76.153 mm; five folds | ≤250 mm; lowest point ≤100 mm; ≥3 folds ≥10 mm; ≤1 remnant | Pass |
| G30 | Eight throw self-intersections; all other changed self/pair counts zero; rigid counts exact | Zero changed intersections; exact rigid baseline | Fail |
| G31 | 28,478 triangles; 1.456675 times fitted | ≤29,325 and ≤1.5 times fitted | Pass |
| G32 | 0.125 mm boundary bound for all seven parts | ≤1.5 mm | Pass |

Fixed geometry bytes, origins/pivots, byte-identical re-export, all six
covers simulated, all cloth settled, no self-collision exclusions, exported
fringe nodes, and the three lit visibility invariants pass. Final acceptance
returns exit 1 and `publication_allowed: false`. The measurements show a
faceting regression despite the improved collapse; no visual sign-off is
claimed. Review skipped per Andrew 2026-10-09.

The final regression runs pass 18 Blender tests and ten Python camera and
visibility tests. Logs are `tmp/age/pass9/final-blender-tests.log` and
`tmp/age/pass9/final-python-tests.log`. Both the rejection and captures were
produced from the final round-tripped preview, not a Blender-only material.

Captures retain the pass-8 cameras:
`tmp/age/pass9/sofa-before-after.png` (3200 × 1422),
`tmp/age/pass9/sofa-turntable.png` (3200 × 2844), and
`tmp/age/pass9/sofa-closeup.png` (1100 × 1000).
The rejected candidate is `tmp/age/pass9/sofa-preview.glb`; the full gates,
SAT pairs and controls are `gates.json`, `collisions.json` and `controls.json`
in the same scratch directory. Nothing was pushed.

## Sofa pass 8: coarse cloth controls and gate scope

Pass 8 follows `tmp/age/advice/STALL_DIAGNOSIS.md`. The runner is
`sofa_pass8.py`; it writes only to `tmp/age/pass8/` and refuses production
until the early controls pass. The previously shipped sofa stays in place
unless every final gate passes. Existing shared function signatures remain
compatible with the concurrent tunic work. `decimate` adds an optional
`keep_factor` argument; its previous defaults are unchanged.

### Gate decisions for this pass

These changes apply to the sofa's visual-design measurements. They do not
relax contact checks, geometry invariants, or the other thresholds.

- **G12:** measure visible box-wall pixels on the cover/residue silhouette in
  the hero and front cameras, relative to the unaged silhouette. Do not count
  every near-vertical fabric face. A 0.72 m² cover inside a 0.46 m² footprint
  has slack that must fold or hang; the intended front-edge hanging strips
  must not be treated as upright cushion boxing.
- **G3:** the 12 px / 4.5 mm straight-run limit applies to panel tears only.
  Released stitched seams may follow a straight seam line. Their lips still
  need to gape under G5 and carry fringe. G4 and G6 keep their thresholds.
- **G7:** measure coplanar residue only where first-hit camera visibility
  shows it through openings inside that part's original cover silhouette.
  Hidden residue and exposed residue outside that silhouette contribute zero.
- **G19:** accept one connected throw from its pinned arm corner to within
  100 mm of the floor. Keep the 250 mm footprint-distance limit, the three
  folds with at least 10 mm prominence, and at most one detached remnant.
- **G30:** zero changed contacts after clearance push-out, with no exclusions.
  Frame, Feet and Rivets must match the rigid baseline exactly. The rigid
  geometry bytes, object origins and pivots also remain unchanged.
### Early controls

All early controls were exercised before production. The final complete set
finished at 23:05:05 UTC on 2026-11-08, within 21 minutes of the first
worktree inspection at 22:45:04 UTC. Its measured runtime was 27.55 s.

| Control | Result | Limit |
| --- | --- | --- |
| C1, centre back with corrected contact drivers | 3.440% sharp dihedrals at frame 20 | ≤5% |
| C1b, Frame only | 0.932% at frame 20 | ≤5% |
| C2, free fall | 0.300000 m/s, relative error 0.000102% | within 20% of measured drag relation |
| C2, 200 mm cantilever, 1× versus co-scaled | 0.000 mm maximum profile difference | ≤3 mm |
| C3, frame 1/20/40 area | 100.000–100.174% of fitted area | 97–103% |
| C4, largest sampled substep motion | 0.909 mm | ≤1.5 mm |
| C5, initial triangle SAT | zero; both the BVH check and AABB/SAT check | zero |

The clean back has 1,987 vertices and 3,944 triangles. Its minimum triangle
altitude is 6.101 mm, its first percentile is 6.335 mm, and its median edge
is 18.004 mm. There is no self-collision exclusion group.

The first pass through the controls failed. Contact-free probes isolated
bending damping: a value of 5 made angular bending buckle even without
colliders. Structural damping remains 5; bending damping is 0.3. Linear
bending was rejected because it lost more than 3% area. The final setup
retains angular bending and the source quad layout where cleanup permits it.

The proposed `100*m*g/air` terminal-speed formula did not match Blender's
RNA air setting in the fixture. The measured relation at 24 fps and
`time_scale=0.5` was `2.4*m*g/air`; air values 0.24, 0.5 and 1.0 produced
0.58859, 0.28253 and 0.14126 m/s for a 0.006 kg vertex. Production uses
that measured coefficient to target 0.3 m/s. The centre-back vertex mass
is 0.004582 kg and its air setting is 0.359618, below the RNA maximum.

A regression fixture also exposed a BVH broad-phase miss for a crossing
triangle against a planar support. The clearance pass uses triangle AABBs
followed by SAT. Its regression proves a crossing exists before repair,
checks zero afterward, bounds movement to 3 mm, and checks unchanged rigid
vertices. This changes no rigid-baseline allowance.


### Production preparation

The seat welt release is checked against its measured 55–75% perimeter
range. The longer side releases leave rear stitching rather than adding
partitions. Back ties select existing rear-panel vertices at 0.60–0.62 m;
moving nearby vertices into that band produced 4.3 mm triangle altitudes,
so that approach was removed. Each nominal 30 × 20 mm tie patch currently
resolves to one vertex on the coarse rear grid. The centre back retains its
6.101 mm minimum altitude after tears and welt release.

The throw has one continuous crest split, reaching the front boundary,
and 351 cap pins. The split is 89.298% of the grid-edge crest length.
The remaining rear bridge is 67.500 mm wide along the crest axis; its
zigzag grid-edge arc is 82.025 mm. Measuring that arc as the bridge's
physical width incorrectly rejected the intended corner hold. The
post-split throw minimum triangle altitude is 6.163 mm, with no exclusions.
Back residue is compressed into the lower return without applying its
height shrinkage a second time to its lateral dimensions.

The right residue initially crossed eight triangles at the return's front
lip (y 0.333–0.340 m, z 0.428–0.436 m). Its depth was narrowed to
approximately y 0.343–0.359 m inside the same lower return. C5 then passed
for all three backs, including residue against the solved seats.

A second controlled comparison isolated a conflict between the back's
animated envelope and its fixed ties. With both present, frame 40 reached
107.678% area and 2.231 mm per substep. Uniform bending still failed
(104.647%, 1.551 mm), and disabling self-collision still failed (103.504%,
3.605 mm). Removing only the envelope passed (100.039%, 0.187 mm, 2.477%
sharp dihedrals); removing only pins also passed, but discarded the required
physical hold. Production therefore retains the ties and the static
lower-return residue, without an animated back envelope. This is a change
from the proposed shape driver, based on the controlled result. The seat
envelopes are unchanged. Failed probes remain under `tmp/age/pass8/`.

The back solve also uses the actual fitted throw as a contact surface.
Without that surface, the right back entered the throw's future starting
pose, and the throw's C5 check stopped before frame one. The throw's cap
will remain pinned in that region. Using its existing geometry during the
back solve fixes the missing interaction without another partition or a
post-solve pose edit.


### Final acceptance: rejected, shipped sofa unchanged

The final preview passes 11 of 22 gates. It has zero changed SAT contacts,
and Frame, Feet and Rivets match the unaged geometry and rigid counts
exactly. Those contact results do not establish an accepted drape. The
left seat stays too high and retains visible boxing; the tied backs retain
too much height; the throw stops 118.619 mm above the floor with one
qualifying fold. All three solves reach the 900-frame cap without three
consecutive stillness checks. No game GLB, shipped texture or baked source
was replaced.

The first seam classifier discarded boundary edges below the lip-weight
cutoff. On the coarse seat meshes it therefore missed released welt seams
and counted their straight contours as panel tears. The final classifier
retains every boundary edge and distinguishes panel tears from seam
failures. It exempts 5/11/3 seat openings from the tear straight-run limit,
but their seam gape and visible-fringe proof still fail. The original
8 mm lip mask does not reliably mark the snapped coarse welt path; its
missing seam lift/fringe remains a construction defect for a later pass.

The seven fringe nodes exist in the GLB. The initial suspicion that preview
cleanup removed them was wrong: `fabric_mesh.new_object` already sets the
export flag. Redundant export assignments were removed. Acceptance now
checks the seven exported node names explicitly, but the diagnostic images
still contain zero green fringe-category pixels. Their camera-visible
coverage is not proven by the authored-card coverage numbers. No visual
sign-off is claimed.

All values below come from `tmp/age/pass8/gates.json`. Triplets are
centre/left/right. An absent resolved opening is a measured failure.
G20–G29 are tunic-only and do not apply to this sofa.

| Gate | Final measured value | Threshold | Result |
| --- | --- | --- | --- |
| G1 | Visible sharp pairs: seats 5.087/4.193/5.008%; backs 1.944/10.390/4.526%; throw 12.937% | Covers ≤8%; throw ≤9% | Fail |
| G2 | Normal jumps: seats 0.773/0.472/0.588%; backs 1.857/1.891/1.688%; throw 0.024% | ≤2% each | Pass |
| G3 | Longest panel-tear runs: seats 43.012/22.136/82.873 px; backs/throw no resolved opening; 5/11/3 seam openings exempt, but seam gape/fringe proof fails | Tears ≤12 px / 4.5 mm; seams retain G5 gape and fringe | Fail |
| G4 | Minimum opening-width CV: seats 0.3195/0.3306/0.4002; backs/throw absent | ≥0.35 each opening, with a measured opening per part | Fail |
| G5 | Lip length lifted >3 mm: seats 33.349/26.362/39.867%; backs 31.825/51.479/60.913% | ≥30% each | Fail |
| G6 | Resolved contour ranges: seats 1.0812–1.2670 / 1.0546–1.3345 / 1.1341–1.3787; backs/throw absent | 1.15–1.40 each resolved contour, with one measured per part | Fail |
| G7 | Visible large planar residue: seats 5.308/0/2.534%; backs 0/0/0% | ≤5% of residue visible through game-camera openings | Fail |
| G8 | Dense crust RMS: seats 1.848/1.680/1.914 mm; backs 2.935/2.948/2.977 mm; all maps present | ≥1.5 mm and normal map | Pass |
| G9 | 8 cut templates; 24 triangles each; thickness/width 0.2663–0.4592 | ≥8; 14–40 triangles, not 20; ratio 0.25–0.70 | Pass |
| G10 | Clark-Evans R 1.269008; largest cluster 0%; 18 floor crumbs | R 0.8–1.4; cluster ≤20% | Pass |
| G11 | Radial-density rho -1/-1/-1; powder present for each source | rho ≤-0.6 and powder per source | Pass |
| G12 | Hero/front box-wall pixel ratios: centre 3.204/3.421%; left 31.697/10.160%; right 0/0% | ≤25% in each camera, relative to fitted boxing | Fail |
| G13 | Rounded-box RMS: 15.810/15.593/21.544 mm | ≥12 mm each seat | Pass |
| G14 | Exported seat centre-height retention: 21.272/32.708/14.022% | 10–25% each | Fail |
| G15 | Exported back height retention: 90.464/86.450/87.603% | 40–65% each | Fail |
| G16 | Back residue in lower third: 100/100/100% | ≥60% each | Pass |
| G17 | Back front folds: 2/2/2 | ≥2 each, ≥8 mm prominence | Pass |
| G18 | Crest release: 89.298% | 60–90% | Pass |
| G19 | 30.214 mm from arm; one connected sheet, lowest point 118.619 mm; one fold ≥10 mm | ≤250 mm; one connected pinned-corner hang to ≤100 mm from floor; ≥3 folds; ≤1 remnant | Fail |
| G30 | Zero changed contacts; rigid self/pair counts exact, including Frame 522 and Frame/Rivets 272 | Zero after clearance; exact rigid baseline | Pass |
| G31 | 29,036 triangles; 1.485217 times fitted | ≤29,325 and ≤1.5 times fitted | Pass |
| G32 | Seat boundary error bounds 3.125 mm each; backs/throw 0.125 mm | ≤1.5 mm | Fail |

G32 includes the clearance push-out. The seat repair changes 18 contacts to
zero in one iteration, but moves boundary vertices enough to fail the
unchanged 1.5 mm boundary limit. Backs and throw already have zero contacts
before their final clearance step. No contact exclusions were added.

Fixed geometry bytes, origins/pivots, byte-identical re-export,
all-six-simulated status, zero self-collision exclusion groups and all seven
exported fringe nodes pass their invariants. `all_cloth_settled` fails.
Final five-frame maximum motions are 0.987 mm for seats, 12.243 mm for backs
and 4.199 mm for the throw. A single under-1 mm seat check does not satisfy
three successive checks.

### Measured runtimes and captures

| Stage | Runtime, seconds |
| --- | ---: |
| Final early-control set | 27.546 |
| Joint seats, 900 frames | 892.669 |
| Joint backs, 900 frames | 390.142 |
| Throw, 900 frames | 374.678 |
| Back stage including preparation and reduction | 448.498 |
| Throw stage including preparation and reduction | 383.317 |
| Final cushion detail bake | 121.362 |
| Final throw detail bake | 31.084 |
| Final debris deposition | 6.567 |
| Final atlas and preview/re-export | 12.153 |
| Final lit/diagnostic renders | 33.355 |
| Comparison composition | 1.666 |
| First-hit visibility captures | 3.507 |
| Exported SAT | 2.911 |
| Final acceptance, expected exit 1 | 19.598 |

These are measured selected-run stage times, not a sum of every discarded
control and failed attempt. Finishing was repeated from the same frozen
solves while checking fringe export and repairing seam metadata. Final
acceptance finished at 00:14:25 UTC on 2026-11-09; the worktree inspection
started at 22:45:04 UTC on 2026-11-08. `phase-times.json` records the stage
boundaries. The final software checks pass 35 Blender tests and five Python
camera-gate tests. Review skipped per Andrew 2026-10-09.

The pass-7 camera setup is unchanged. Final images are
`tmp/age/pass8/sofa-before-after.png`,
`tmp/age/pass8/sofa-turntable.png` and
`tmp/age/pass8/sofa-closeup.png`. The closeup is at 0.6 m. The rejected
candidate is `tmp/age/pass8/sofa-preview.glb`; the full gate and SAT results
are `gates.json` and `collisions.json` beside it. All scratch data and
textures remain under `tmp/age/pass8/`.

## Sofa pass 6: fitted six-cover collapse

`sofa_decay_joint.py` starts all six covers from `sofa/sofa-working.blend` in one dense cloth system. Each cover has its own seed. Inter-cover contact uses self-collision across all resolvable panels; the exclusion group contains split lips and triangles below Blender's 2 mm contact diameter, rather than whole top panels. The working system has 131,148 triangles. It contains no sofa-k geometry.

The filling contacts animate from the fitted volumes into the residue envelopes. A static, already-settled back residue intersects an inflated seat at frame one, so that final residue is not also added as a premature collider. Back-envelope roof heights are sampled from the actual residue, not a box. Exported covers and residues still require the complete G30 SAT test.

The fitted back's front bulge has downward normals as high as 650 mm. Removing every downward face deleted that front panel and stopped a grain walk after 109 mm. The back opening is now confined to faces below the 432 mm hem. The fitted-asset regressions in `test_sofa_decay_geometry.py` verify both the preserved front panel and a 160 mm grain walk across it.

`sofa_full_decay.py` retains the ordered fallback and the isolated seat controls. Keyed cloth is frozen from evaluated data because Blender cannot apply a cloth modifier to a mesh with shape keys. A folded-rest control found that Blender 4.5.11 transfers the rest coordinates only when a real level-1 Subdivision modifier precedes Cloth; an absent or level-0 modifier leaves the same control flat. The joint path reduces the carrier first, then subdivides it back to the working density. This second subdivision uses SIMPLE because the cover was already smoothed before cutting: another Catmull-Clark pass bends opposite split lips through each other at frame one. The initial surface and collider SAT checks pass with SIMPLE. Vertex mass uses the evaluated count. Per-cover vertex groups survive subdivision and restore the original pivots when the solved mesh is separated. A solved checkpoint is saved before reduction or baking, and `--finish <joint-solved.blend>` resumes that work without another simulation.

The pass-6 controls, checkpoints and captures stay under `tmp/age/pass6/`. Missing or failed gates block publication. The game asset is not replaced by a preview.

The pass-6 collapse milestone failed. The ordered centre and left seats completed 360 frames in 220.251 s and 281.616 s. Their centre-height ratios are 21.727% and 14.732%, inside G14's 10% to 25%, but wall-area ratios remain 38.831% and 33.168%, above G12's 25%. The next fitted right seat crosses the settled centre mesh at initial triangle pair 5165/418, so the initial-contact check stops it. The other four diagnostic covers are explicitly recorded as unsimulated fitted poses. The flat-rest joint trial reached 51.459% sharp adjacencies at frame 60; both joint trials were stopped and retained when the ordered fallback advanced faster. These failed trials do not replace the game asset.

`sofa_decay_finish.py --stage detail` bakes each reduced cover and residue from its dense source, applies the original upholstery albedo `(0.055, 0.060, 0.066)`, and adds collision-tested fringe at the authored lips. The rendered round-trip material control differs from the same constant reference by at most 0.000638 per linear RGB channel, below one 8-bit step. The texture contains AO rather than relying on colour-math nodes that glTF cannot export. A completed one-seat material integration does not certify the six-cover tear or residue gates.

The throw has three zero-area crest split runs, leaving two 18/19 mm bridges and end corners. G18 passes at 78.556% split against 60% to 90%. Its unpinned 480-frame solve took 776.333 s. It reached the floor, then its collision response ejected it upward and away; the final reduced surface has no area below 0.30 m, so G19 fails with no fallen centroid and zero measurable floor folds. Its final 3,200-triangle surface has 58.918% all-sheet sharp adjacencies and 50.891% visible sharp adjacencies. The solver cause is unresolved; the failed result is retained without a manual pose correction.

The crumb/powder milestone passes G9 to G11. Nine cut-residue templates use 24 triangles each, with thickness/width 0.2663 to 0.4592. Deposition places 90 floor crumbs, 24 crumbs under actual tear lips, and three powder cards. G10 measures Clark-Evans R 1.162946 and largest DBSCAN cluster 0%. G11 radial-density correlations are -1.000000, -0.900000 and -0.974679, each below -0.6. The initial uniform-width strip failed the centre source at -0.2 because lateral sampling did not decline radially. The final half-disc fans stratify decreasing area densities while retaining the 24 mm minimum spacing and contact rejection. The exported components match the placement record.

### Pass-6 final acceptance: rejected, game asset unchanged

The 4096-square albedo/normal atlas is packed, and the diagnostic GLB passes geometry-byte, pivot and byte-identical re-export checks. It has 29,272 triangles. Publication is blocked by the failed gates and by the explicit requirement that all six covers were simulated. No pass-6 GLB or textures were copied into the game's asset paths.

In the table, seat triplets are centre/left/right; back triplets use the same order. The four fitted diagnostic covers have no simulated aging. Full per-opening values, face counts and collision details are in `tmp/age/pass6/ordered/gates.json` and `collisions.json`.

| Gate | Measured value | Threshold | Result |
| --- | --- | --- | --- |
| G1 | Visible sharp adjacencies: seats 9.667/7.170/0%; backs 0/0/0%; throw 50.891% | Covers ≤8%; throw ≤9% | Fail |
| G2 | Cover normal jumps 0.0993% to 0.2422%; throw 6.4609% | ≤2% | Fail |
| G3 | Longest alpha-aware straight runs: seats 34.300/79.765/31.780 px; no resolved back or throw openings | ≤12 px | Fail |
| G4 | Minimum opening width CV: seats 0.3627/0.4306/0.2974; no back or throw openings | ≥0.35 each | Fail |
| G5 | Lifted lip length: seats 38.340/44.777/0%; backs 0/0/0% | ≥30% | Fail |
| G6 | Resolved contour dimensions: centre 1.1043–1.2938, left 1.0221–1.2543, right 1.2542; none for backs or throw | 1.15–1.40 each | Fail |
| G7 | Planar residue area: seats 33.876/29.858/30.221%; backs 7.847/4.202/4.983% | ≤5% each | Fail |
| G8 | Dense plane-fit RMS: seats 1.712/1.712/1.712 mm; backs 2.494/2.478/2.478 mm; all normal maps present | ≥1.5 mm and map | Pass |
| G9 | 9 templates; 24 triangles each; thickness/width 0.2663–0.4592 | ≥8; 14–40 triangles; ratio 0.25–0.70 | Pass |
| G10 | R 1.162946; largest cluster 0%; 90 floor crumbs | R 0.8–1.4; cluster ≤20% | Pass |
| G11 | Radial density rho -1.000000/-0.900000/-0.974679; 3 powder cards | ≤-0.6 per source, with powder | Pass |
| G12 | Seat vertical-wall area 38.831/33.168/89.132% of fitted | ≤25% each | Fail |
| G13 | Exported rounded-box RMS 18.187/16.361/7.367 mm | ≥12 mm each seat | Fail |
| G14 | Seat centre-height retention 21.727/14.732/99.938% | 10%–25% each | Fail |
| G15 | Back height retention 99.883% each | 40%–65% each | Fail |
| G16 | Back residue volume in lower third 100% each | ≥60% each | Pass |
| G17 | 1 front fold per back at ≥8 mm prominence | ≥2 per back | Fail |
| G18 | Crest split 78.556% | 60%–90% | Pass |
| G19 | No final throw area below 0.30 m; no fallen centroid; 0 floor folds | Distance ≤0.25 m; ≥3 folds | Fail |
| G30 | 1,490 changed contacts; exact rigid baseline retained: 522 frame self and 272 frame/rivets, other rigid counts zero | Zero changed contacts; exact rigid baseline | Fail |
| G31 | 29,272 triangles; 1.497289 times fitted | ≤29,325 and ≤1.5 times fitted | Pass |
| G32 | Dense/game boundary bound 0.125 mm for all covers and throw | ≤1.5 mm | Pass |

G20 to G29 are tunic-only. Of the changed contacts, 549 are throw self-contacts, 46 are in the two settled seat nodes, 4 are in the fitted left-back node and 13 are within crumb templates. Pair contacts include the retained fitted neighbours and 12 frame/settled-seat crossings. The residue's remaining large planar underside facets still fail G7 despite its dense roughness and baked normal maps. Fringe covers about 76% to 79% of the authored lip length, but its alpha-aware contours still fail G3 and G6. Presence and coverage do not establish a convincing torn edge.

Captures of this rejected preview are `tmp/age/pass6/sofa-before-after.png`, `sofa-turntable.png` and `sofa-closeup.png`. The closeup is at 0.6 m. The throw diagnostics follow its actual failed position, rather than rendering the empty fitted arm location. These are diagnostic images, not an accepted art replacement.

Verification: 39 Python tests, 12 Blender tests, the rendered albedo/keyed-cloth integration control, the one-seat material integration and the final export acceptance runner completed. Acceptance exits 1 because the measured asset fails; the software tests pass. No OCR review was run, per the standing instruction.

## Pass 5 calibration and contact policy

The 200 mm cantilever now compares 21 width-averaged material stations in 3D, rather than only the free-tip height. At 150 frames and 24 fps, the maximum dense/reference profile difference is 1.926 mm for upholstery and 4.409 mm for wool, against a 10 mm limit. Both fits retain total swatch mass. The requested 6 mm grid is actually 5.882 mm (34 cells); the reference is 22.222 mm (9 cells).

The upholstery reference is the selected fitted `seat-u` record: structural 500, shear 350, bending 10, vertex mass 0.015 kg. The wool reference uses structural 150, shear 80, vertex mass 0.15 kg and bending 0.25, as specified for the fitted throw in the #95 task. The older `throw-l` trial records a different bending experiment (0.7); it must not replace the task's 0.25 reference.

Spring-only sweeps failed to reproduce the upholstery drape. Damping had also been left constant while vertex mass fell with resolution, so the dense swatch was still moving toward its drape at frame 150. Joint spring/damping sweeps and independent mass, structural and bending perturbations found a mass-conserving fit. At the measured edge ratio 9/34, upholstery uses structural 160, shear 56 and bending 1.6; wool retains 150/80/0.25. Both use structural damping 1.44, bending damping 0.36 and air damping 0.6.

`cloth_stage.calibrated_config` records the empirical formula `q(h) = q_ref * (h / h_ref)^p`. Upholstery exponents are 0.857274446 for structural springs and 1.378776541 for shear and bending. Wool spring exponents are zero. Both fabrics use 1.595219466 for damping and air damping. Mass remains `mass_ref * N_ref / N_dense`. These coefficients describe this Blender version and fixture; they are not a general resolution law. The full sweeps, selected settings, profiles and exponents are under `pass5_calibration` in `sofa/cloth-trials.json`. Reproduce with `swatch_calibration.py`; raw exploratory runs stay under `tmp/age/pass5/`.

G30 now uses the owner's rigid-assembly decision below. `collision_policy.py` compares all six rigid self/pair counts against the unaged SAT report and separately totals every changed-part contact. The controls reject an added changed contact and either an increase or decrease in rigid baseline counts. Supply the unaged report explicitly with `sofa_gates.py --baseline-collisions`; `collision_export.py --baseline` can perform both inspections in one Blender run.

## Reusable soft-prop stages

## Pass 5 centre-seat initialization diagnosis

The old centre seat is already crumpled before decimation: the proxy-residue run has 52.727% dense sharp adjacencies and 60.985% after reduction. Decimation adds faceting but does not create the outlier at 1.138 m. The x=1.455 m and below-floor outliers belong to the unchanged sofa-k throw, not the centre seat.

The fitted cover begins with 1,765 SAT crossings against the already-aged centre back and 18 against the right back. The collapse envelope, residue, frame, feet and rivets have zero initial crossings. These mixed-time initial poses cause collision impulses before the foam has collapsed. Disabling self-collision or slowing the collider without clearing the initial contacts still leaves more than 40% dense sharp adjacencies.

`neighbour_colliders.py` starts seat simulation against the fitted back contacts. The maintained `--uncut-control --settings <self-collision-off.json>` regression at 360 frames, with collapse over 240 frames, measures 1.174% dense and 6.920% game sharp adjacencies, below the 8% limit. All vertices are within the frame bounds expanded by 0.15 m; G32 is 0.125 mm. The grain-tear production seat is a separate run. Fitted contacts do not certify final clearance against the comparison backs: G30 must still inspect those actual exported meshes.

The stage now also uses Blender's self-collision group as an exclusion, as its API specifies. The old group excluded boxing walls instead of enabling their contacts. Lip shrink now interpolates from zero outside the authored band to the configured lip shrink, rather than applying the same 4% shrink everywhere. These API fixes have direct Blender controls in `test_cloth_stage.py`.

The centre-seat bake is still experimental. `seat_render.py` imports the actual trial GLB and records alpha-tested close and hero face IDs, material IDs and normals. `seat_gates.py` measures visible G1 adjacencies, G2 normal discontinuities, G3's 1 px Douglas-Peucker contours, G4 medial-axis widths, G6 box counts, dense lip lift and crust roughness, exported shape, and final SAT contacts. G6 reports all opening dimensions; its acceptance fit uses contours at least 64 px across so the largest 32 px box has two samples. Smaller opacity openings remain reported. Missing measurements fail. `card_contacts.py` tests complete card triangles against the cloth, residue, comparison parts and earlier cards before accepting placement. The baked lip-control seat has zero cover/residue self-crossings and zero fringe contacts, but 616 contacts with neighbouring comparison cushions; it is rejected and has not replaced the game asset.

A translated aged-back contact is also rejected: its long hanging skirt reaches the seat before the back body, then the later body compresses the cloth against the deck. The staged control rises from 3.47% dense sharp adjacencies at frame 620 to 42.46% at frame 700. The `morph` experiment instead moves an unexported contact surface from the fitted back envelope to the exact comparison-back vertices during the foam collapse. This is an experiment, not an accepted replacement. Reducing boxing bending below the calibrated baseline produced further unstable runs, so it is not the default.

`densify.py` subdivides working surfaces and optionally refines projected bands. `tear_paths.py` snaps paths with Dijkstra and splits edges without removing area. `grain_paths.py` derives physical warp/weft directions from the pattern UV gradient. `cloth_stage.py` preserves explicit lip, welt and collision groups, scales per-vertex mass and records every frame's elapsed compute time.

`bake_down.py` protects a 6 mm **surface-distance** band around open boundaries, then reduces the interior. Euclidean distance incorrectly protected nearby folds in the centre-seat test, freezing reduction at 4,886 triangles. Blender decimates weighted vertices, so the `Keep` group must be inverted. A conservative sampled Hausdorff upper bound includes half the sampling interval; the control and centre-seat result are both 0.125 mm against a 1.5 mm limit. The stage creates `BakeUV` and selected-to-active Cycles tangent normal and AO maps, with 4 mm cage extrusion, 12 mm ray range and an 8 px margin.

`residue_sdf.py` builds a continuous powder base, noisy lumps, Voronoi cracks and tilted skin slabs, then extracts the dense surface with marching cubes. Overlapping lumps initially exceeded 80 mm; bounded lump heights and an unbroken powder base bring the current source below 35 mm. A 13 micrometre isovalue offset avoids grid-aligned zero-thickness contacts. The pore-rich source contains hundreds of small handles, which cannot survive a 700-triangle budget. A vertically filled height-field proxy carries the outer envelope into the collider/game mesh; the detailed pore surface remains the normal/AO bake source. The game mesh uses this filled proxy because collapse alone preserves the pore topology.

Full-size proxy testing also exposed a numeric topology defect that the small fixture missed. Marching cubes returned a closed indexed surface, but ordinary vertex merging identified distinct float32 grid-corner tips. The proxy now reconstructs a single-valued top, fills footprint holes, keeps at least two voxel cells of thickness, quantizes the field to 1 micrometre and places the isovalue halfway between quantized values. Field clipping bounds interpolation near grid corners; world-origin addition uses float64. The full-size regression remains closed with Euler characteristic 2 after vertex merging. Blender reduces the current proxy to 700 triangles with the same closed topology. This fixes topology, not appearance: its G7 planar fraction is still 33.233%, above 5%, dominated by underside facets. The revised dense source measures 1.655 mm plane-fit RMS against G8's 1.5 mm geometry requirement, but it has not yet been baked into an accepted seat.

The rear-approach contact experiment also fails. At frame 1200 its dense sharp-adjacency share is 39.594%, so it is retained as a failed simulation checkpoint under `tmp/age/pass5/seat-rear-contact/`. No experimental seat has replaced `assets/props/quarters/sofa_aged.glb`. The centre seat, remaining cushions, throw, crumb deposition and final shared atlas remain unfinished.

`fragment_library.py` takes connected skin pieces cut from 12 Voronoi cells in that same SDF. An 8 mm skin depth produced nine accepted templates at 24 triangles each; three thinner pieces remain rejected in the measurement record and are not exported. Deposition onto final sofa surfaces has not been implemented.

`fringe_cards.py` generates eight 1024 by 256 strand variants in numpy, their normal map and boundary cards. `opacity_bake.py` rasterizes 0.5 to 2 mm lip breakup into the game's `BakeUV`. `powder_cards.py` provides an irregular 48-triangle floor deposit with alpha coverage and a normal map from a 0.5 to 2 mm height field. The Blender control exports cloth opacity, fringe and powder as glTF `alphaMode: MASK`, and checks byte-identical re-export from a saved blend. This control does not certify card collision clearance or appearance.

The single-seat pilot currently uses a 4096-square normal/AO/opacity set for that seat and 2048-square residue maps. Packing all six covers into the shared 4096-square atlas remains unfinished. Coverage-preserving alpha mip generation and a Godot back-face-normal check also remain unfinished.

Run the Python tests with the Hunyuan environment. `test_bake_masks.py` requires Blender's `bpy`, so it cannot run under ordinary Python. Run `blender_soft_controls.py` in background Blender for integration coverage. Logs, fixtures, maps and experimental blends stay under `tmp/age/pass4/`.

## Sofa pass 4: dense simulation and bake-down

The pass-3 sofa trials `sofa-a` through `sofa-k`, including the failed `sofa-e`, are retained in `sofa/cloth-trials.json`. They are comparison inputs, not accepted pass-4 results. The fitted source and shipped GLB remain untouched until a new bake passes.

`sofa_gates.py` replaces sofa acceptance in both old gate entry points. Every G1 to G19 and G30 to G32 has an explicit threshold. Missing measurements are `not_measured` and fail; declaring a threshold does not implement its measurement. The current geometry checks measure G1, G7, G10, G12, G13, G14, G15, G16, G30 and G31. G1 currently reports all-sheet adjacency and remains failed until visible-face filtering is implemented. Render, dense-source and story checks remain to be implemented.

Gate changes and reasons:

- Remove crumb clustering >=70% and spacing CV >=0.50. These rewarded three compact piles. G10 instead requires Clark-Evans R 0.8 to 1.4 and no DBSCAN cluster above 20%; G11 requires a decaying spill with powder.
- Remove perimeter/sqrt(area) as a tear acceptance test and the 30 mm straight-run allowance. Slots passed both. G3 requires <=12 px/4.5 mm straight runs; G4 width CV >=0.35, G5 >=30% lifted lips and G6 contour dimension 1.15 to 1.40 prevent acceptance based on perimeter alone.
- Remove the 35% to 45% seat-height target and the pass-3 >=50% drop proxy. G14 requires 10% to 25% centre height above the deck. G12 limits surviving vertical wall area to 25%; G13 requires >=12 mm rounded-box residual.
- Remove the >=65% retained back-height target and hero-area proxy. G15 requires 40% to 65% retained height, G16 >=60% residue in the lowest third and G17 at least two 8 mm folds.
- G1 and G2 limit exported cloth faceting and normal-pass discontinuities. G7 limits large planar crust facets to 5%; G8 requires dense crust roughness plus a normal map.
- G9 checks cut-residue fragment templates rather than jittered icosahedra. G18 and G19 require the crest failure and nearby folded fall that explain the throw's pose.
- G30 requires zero SAT intersections for every pair involving any changed or new part, including covers, residues, throw, fringe, crumbs and powder against Frame, Feet and Rivets. The unchanged rigid set is reported separately, with every self and cross-part count required to equal the unaged export exactly. Its fitted overlapping steel primitives have 522 Frame self-crossings and 272 Frame/Rivets crossings. These joints are acceptable because this rigid assembly is never deformed. Removing an existing rigid crossing also fails the exact-baseline check. G31 retains the 29,325 triangle cap; G32 limits dense-to-game open-boundary error to 1.5 mm.

`Frame`, `Feet` and `Rivets` are all cloth colliders without changing their mesh. Neighbouring settled covers and the floor remain colliders. Fixed meshes and pivots are checked independently of the changed-part SAT test and the exact rigid baseline comparison.

The sofa and tunic represent 1000 years in dry, sealed, sterile, oxygenated air. Foam oxidises into crust and crumbs; wool splits at seams and hanging stress points. There is no biological or water damage. Locker materials and `bake_masks.py` belong to a separate pipeline.

Author in Blender's native Z-up frame, with front toward -Y, then export with `export_yup=True`. The GLBs have +Y up and front +Z. Existing object names, transforms and pivots are retained. Crust and cover share their cushion node; debris has separate named nodes.

## Cut-first physics
### Swatch measurements

`swatch_tests.py` runs 200 by 200 mm cantilevers for 150 frames at 24 fps. The first fixture uses 24 mm requested edges; dense fixtures use 6 mm and 3 mm. Vertex mass scales by reference vertex count divided by dense count. Upholstery uses 180 structural stiffness and 0.2 bending; wool uses 150 and 0.5. These are candidate settings, not accepted calibration against the fitted wool's 0.25 bending.

| Material | Edge | Uncut s/frame | Split s/frame | Uncut tip drop | Reference drop |
| --- | --- | --- | --- | --- | --- |
| Upholstery | 6 mm | 0.0605 | 0.0472 | 56 mm | 154 mm |
| Upholstery | 3 mm | 0.2504 | 0.2476 | 16 mm | 154 mm |
| Wool | 6 mm | 0.0528 | 0.0529 | 193 mm | 198 mm |
| Wool | 3 mm | 0.2260 | 0.2233 | 93 mm | 198 mm |

Raw frame costs, mass, slit gape and local lip-plane distances are recorded in `sofa/cloth-trials.json` under `pass4_swatches`. Drape differs by more than the 10 mm fixture tolerance in three cases. The settings are not production-ready; no calibration success is claimed. The first attempt stopped at an outdated bmesh lookup table after splitting. Refreshing that table fixed the tool error; its log remains under `tmp/age/pass4/swatches/run.log`.


`pass3.py` loads the unchanged fitted source. `stress_cut.py` releases shared armhole stitches and cuts stress-aligned rips before simulation. Its seeded boundary field has four octaves and a requested 6 mm amplitude, limited locally by edge length. It separates face fans that meet at a point, since a point contact is not a surviving stitch.

`tunic_pass3.py` removes about 60% of the near-side armhole stitches and weakens the wool. Pins are confined to a narrow top seam projected onto the hanger's actual upper wire surface, with 6 mm clearance. The shoulder mesh is refined to resolve the 7 mm wire. Blender cloth moves the body, sleeve and attached tear flaps under gravity. Neighbouring source cloth is lifted 12 mm before simulation to clear the wire. Both contact adjustments occur before gravity starts. There is no post-simulation garment pose deformation.

`sofa_pass3.py` derives shrunken closed crust from each unaged cushion. All six cut covers are simulated together with inter-cover self-collision, zero pressure and no pins. Their continuous collision envelopes start 8 mm inside the fitted filling surfaces and shrink linearly to the final crust over frames 1 to 480. Surface-normal offsets clear the concave back cushion returns, which a centre-based scale left crossing the cloth. The cover geometry is not narrowed or shifted to produce its aged pose. Underside loss clears starting cloth from the deck. The throw has no retained pins; reduced frame friction lets it slide. Its cut corner is simulated separately against the floor, furniture and settled main throw. The non-overlapping crumb clouds start at 0.50 to 0.62 m in the front spill zones and fall using Blender rigid bodies. Cushion surfaces are passive colliders; a solid floor volume prevents particles from tunnelling through a zero-thickness plane.

Some geometry is constructed rather than simulated. Crust shrinkage and Voronoi cracks are constructed. Fray fibres are added after cloth settling, with crossing thread tips removed. The fibre/dust heap is a seeded closed mound placed forward of the hem, toward the hero camera, above the unchanged 0.95 m floor drop. `detail_fit.py` clips visible simulated support triangles to the reinforced cloth details' footprints and lifts those patches 3 mm. It trims facets crossing underlying folds and opens point-only contacts by 0.2 mm. Brass follows rigid best fits, with the medal transformed as one rigid assembly. These details and the fibre heap have no separate physics simulation.

Fabric uses double-sided midsurfaces rather than sub-millimetre closed sections that can fold through themselves and spend the triangle budget on invisible back plies. Crust remains closed. Volume gates measure the closed crust against the unaged cushion envelope; an open cloth surface has no defined enclosed volume.

## Run and record a trial

Use the installed Blender with no additional packages:

```sh
nohup <blender> --background --factory-startup --python-exit-code 1 \
  --python tools/blender/quarters_aging/pass3.py -- \
  --prop sofa --trial <name> --frames 300 \
  > tmp/age/pass3/<name>.log 2>&1 &
```

Substitute `dress_uniform` for the tunic. All scratch outputs stay below `tmp/age/pass3/`. Every start, failure and completed bake is retained in the prop's `cloth-trials.json`, including actual simulator settings. Failed trials are not selected by their existence alone.

The tunic saves `simulated.blend` before fitting details. `--finish-tunic <checkpoint>` reuses that cloth bake to fit details without rerunning or changing the cloth. Its trial record identifies the reused simulation. The `--publish` option writes a completed bake to the prop source and game paths; use it only after inspecting the measured gates.

The normal prop exporters load baked sources: `sofa/build.py -- --aged --output <file.glb>` and `dress_uniform/build.py -- --aged --output <file.glb>`. Re-export is compared byte for byte with the delivered GLB.

## Export and camera gates

`collision_export.py` imports the actual GLB, builds triangle BVHs, then tests candidates with triangle-triangle SAT, including coplanar overlap. Only shared-vertex adjacency is omitted from self checks. No cloth, cushion or attachment is exempt from intersection tests. Sofa frame, feet and rivet joints remain reported as the unchanged rigid baseline; their counts must match the unaged export pair by pair, and their original geometry bytes are checked independently. The tunic's collision policy is unchanged. Cloth boundaries must be unbranched, without nonmanifold or degenerate edges; crust must be closed.

Run `pass3_gates.py` with the installed Hunyuan Python:

```sh
<python> tools/blender/quarters_aging/pass3_gates.py \
  --prop sofa --input <aged.glb> --reexport <repeat.glb> \
  --collisions <collisions.json> --out tmp/age/pass3/<name>/gates
```

Failures retain their values and exit nonzero. Displacement is measured on exported geometry: cuff and cap pattern islands, nearest unaged cloth surface distance, area-weighted throw centroid and central seat cover rays. Seat outlines are fitted against a rotated rectangle. Crumb checks use connected components, physical sizes, projected cluster distances and nearest-neighbour spacing variation.

The first-hit raster uses the same orthographic hero camera as the lit captures, at 1600 by 1422 pixels. It includes all prop parts and the studio floor. Lossless `before-hero-ids.png` and `after-hero-ids.png` encode integer labels in RGB; `hero-labels.json` maps those values to part/material names. The corresponding `*-hero-mask.png` files use a readable palette. Individual binary masks show the counted crust, crumbs, floor remnant, fibre heap, armhole gap and back silhouettes. Crust counts are restricted to projected internal tear boundaries, so exposed outside edges cannot satisfy the split-visibility gate.

The sofa framing remains 2.85 m wide. Both tunic states use 1.30 m rather than 1.15 m: the heap projects below the bottom of the 1.15 m frame. This widens the framing without changing the hero angle or target. Camera direction, placeholder colours and neutral lighting are unchanged. Armhole pixels are counted only within the unaged near-side cap's projected region, where cloth was the first hit before and background or a different part is the first hit afterward.

Pass 2's gates missed the visible defects because seam-cut length, heap dimensions, small shoulder displacement and projected shape measurements did not require a moved cuff, a rotated sleeve or visible first-hit debris. Its hand-shaped aged cloth also bypassed the simulator decision in `PLAN.md`.

## Captures and controls

`render.py -- --prop <sofa|dress_uniform> --out tmp/age/pass3` imports the exports for fixed-camera before/after pairs and four-view turntables. `--aged-input <trial.glb>` renders a trial without publishing it. `sofa-closeup.png` is 0.6 m from the split-seat target; `tunic-closeup.png` frames the shoulder and armhole from 0.5 m. Run `compose.py --out tmp/age/pass3` to make the comparison sheets, with unaged left and aged right.

`test_pass3.py` controls first-hit occlusion, area-weighted centroid, cuff/cap pattern selection and rectangle residuals. `test_pass2.py` retains continuous SAT and hem-variation controls; `test_verify.py` retains export and reference-surface controls. Geometry gates do not establish visual readiness. A separate image review is still needed.

`pass2.py`, the prop-specific `*_pass2.py` files, `build.py`, `cloth_decay.py` and `foam_collapse.py` retain earlier methods for their recorded trials. They do not substitute for the third-pass physics.
