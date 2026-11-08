# Dense aging for the pilot tunic

The dense-aging pipeline is experimental. No candidate has replaced the game
asset. Acceptance requires every measured gate and a visual concept comparison;
passing local controls does not certify a trial's geometry or appearance.

The tunic represents 1000 years of dry aging. Its cut, collar, shoulder boards,
buttons and medal must remain recognizable. The source is `tunic-working.blend`,
with `body-p` as the wool reference. `ShoulderChestForm` remains an invisible,
unexported collider.

## Tunic7 settling controls

The source-grid carrier removes the old masked-face workaround. The runtime
rest check now rejects any evaluated triangle smaller than the contact diameter;
it never installs an exclusion group. A resolved free-fall control must match
the same mesh without self collision, while a sub-diameter mesh must fail.

At frame 200 the unmasked dense body had two strict self contacts but still
moved 14.41 mm over five frames. Extending that control to 1500 frames produced
52 contacts and 49.70 mm motion, so extension alone failed. Its damping still
came from the finer 2.985 mm swatch, rather than the measured working grid.
The next control measures evaluated edge length and fits damping through both
existing swatches, without changing the 500/500/350 springs or 0.3 bending.
Residual motion remains concentrated in free lower cloth after the opening
phase. A separate settle control restores the source wool's damping from frame
601: structural 5, bending 0.5 and air 10. It retains the same rest shape,
springs, mass, contact radius, pins and force field. A falling-plane test checks
that this transition continues physics rather than freezing or resetting the
mesh. The final dense control still requires fewer than 50 self contacts and
less than 1 mm motion; the exported changed-part contact requirement is zero.

## Tunic7 tear and deposit construction

The old hanger tear followed nearly constant pattern V with only ±0.0006
variation in that pattern coordinate. Its opening had a 270.6 px straight contour and dimension 1.1105.
The opacity stage interpolated distances measured only at triangle vertices.
On the tunic6 baked sheet, that interpolation missed 2,745 texels inside the
physical 3 mm lip band. The new wrapper measures distance per texel instead.
It retains the shared breakup frequencies and gain, uses pattern-grain
coordinates, and adds two 30 mm grain walks with 18 mm branches. Crack widths
remain 1.3 mm, carried by opacity; the main gaping lips remain geometry.
Fringe is still generated and contact-tested on those physical lips. These
changes require alpha-aware contour measurement on the finished export.

The fallen strips previously landed away from the mound's centre. For example,
the first and third pieces occupied y=-0.129 to -0.065 m and y=-0.113 to -0.061 m,
while the mound is centred at zero with a 0.072 m half-width. They also used
straight strip rest shapes, so floor friction preserved slab-like pieces.
Released source allowances now receive a regular working grid and an
arclength-curled rest, start over the deposit, and settle under gravity against
the mound, body, floor and earlier strips. Their minimum rest altitudes are
3.002, 2.656 and 3.442 mm; none needs a self-contact exclusion. The mound gets
normal/AO bakes from its dense SDF source, in addition to its floor skirt and
contact-tested loose fibre cards. These controls do not establish appearance.

## Tunic7 attachment and projection controls

Attachment offsets were stored in world coordinates. A 90-degree support
rotation left a 10 mm offset pointing in its old direction, putting the test
attachment 10 mm off its intended position. Offsets now carry the source
triangle frame and rotate into the deformed support frame. The rotation
regression fails before the change and passes after it. Translation, sewn
column and closed-ribbon controls also pass.

Shoulder boards and the placket are fabric facings in the source, authored as
surface-fitted grids. Treating either as one rigid object replaced the local
cloth shape with a whole-object fit. They now follow their sewn points and
local normals, keeping the original topology. Their source bindings also
remove the 1.75 mm offset belonging to the original body's Solidify shell.
Metal details remain rigid. Their seating can move inward as well as outward,
so an excessive original offset is not preserved as a gap.

The old G21 split hull used a stale camera matrix. Its recorded image bounds
were x=892.93 to 1137.56, y=674.15 to 748.65. Updating the view layer before
projection gives x=873.84 to 1078.49, y=362.42 to 629.99. Both previously flagged
pixels, (904,370) and (905,371), lie inside the correctly projected split hull.
This fixes the projection error without changing the hull selection, threshold,
hanger, camera or cloth. Visible wire inside an actual split still needs visual
inspection; a zero poke-through count does not establish that it looks right.

## Tunic7 rest-grid control

The rest probe isolates the tessellation defect. The source has 2,268 quads
and no triangle altitude below 2 mm. Graded refinement produces 197 such
triangles after splitting. Decimation to 5,000 triangles creates a 0.225 mm
minimum altitude; SIMPLE subdivision then produces 15,247 sub-2 mm triangles
out of 30,000, with a minimum altitude of 0.0695 mm. The prior contact exclusion
masked these faces instead of repairing them.

The trial now preserves the source grid and triangulates it without a collapse
stage before SIMPLE subdivision. The evaluated pressed garment has 26,964
triangles, no sub-2 mm triangle, and a minimum altitude of 2.0259 mm. The rest
regression failed on the old carrier (15,248 sub-2 mm faces) and passes on this
carrier. All body faces participate in self-collision. This is a rest-mesh
control, not a claim that the dense solve or final export passes.

The shoulder seam and hanger wear line share one released seam. The previous
second slit sat about 5 mm forward of that seam and created a narrow strip
between coincident lips. The starting lips now receive the same opening as
their bending rest, including the shoulder. The pressed sleeve is widened by
20% while retaining 40% depth, and its broad face is oriented toward the close
camera. These changes are undergoing a fresh gravity solve. Settling records
the last-five-frame maximum motion every 25 frames and can stop after frame
600 only after three successive measurements below 1 mm.

## Tunic7 sleeve diagnostic correction

The previous G22 accepted a thin cross-section without checking its orientation
in the close camera. Its origin was the mean of vertices in pattern V 0.45 to
0.60, not a camera-facing width measurement. The tunic6 sleeve's principal-axis
ratio was 0.2708, but its mid-sleeve camera-depth/width ratio was 2.254:
69.61 mm deep and only 30.88 mm wide. At quarter and three-quarter stations the
ratios were 2.746 and 1.349. A flattened sleeve viewed edge-on therefore passed
while looking like a narrow tube.

G22 now uses transverse mesh-plane intersections at pattern-length stations
0.25, 0.50 and 0.75. Each section is measured along camera depth and camera
width after projection perpendicular to the sleeve axis. The largest ratio
must remain at most 0.45. Section extents replace vertex covariance, so uneven
mesh sampling cannot make the ratio smaller. The same close-camera direction
is used by the renderer. Three unit controls cover a visible pressed section,
an edge-on section and biased sampling. The old candidate fails this corrected
gate. This diagnostic milestone does not replace the delivered GLB.

## Recovered checkpoint (2026-11-08)

The inherited `tmp/age/tunic5/carrier/` trial reached all scratch stages, not
just preparation. It simulated a 30,000-triangle body for 600 frames with the
chest form, a working subdivision rest carrier and 3 fallen hem strips. The
shoulder seam split is 60.56%, armhole release 58.93%, and retained arc 41.07%.
It baked normal/AO, added rim geometry, fringe, stitch opacity, a 22.45 mm mound,
a floor skirt and 65 fibre cards. Saved-blend re-export was byte-identical.
All 9 local test scripts passed again under `tmp/age/tunic6/`.

This is unfinished work. The carrier candidate passes 11 of 19 gates. Failures
are G1 (12.57% visible sharp edges versus 6%), G3 (289.70 px versus 12 px), G6
(1.1467 versus 1.15 minimum), G20 (10.44% versus 10%), G21 (1060 exposed hanger
pixels versus zero), G24 (89.94% chest width versus 92% minimum), G30 (683
changed-part contacts versus zero), and G31 (21,919 triangles versus 20,652).
The unchanged hanger matches its baseline exactly at 28 self contacts. Most
remaining contacts are in the body/rim and collar, not the fringe. The latest
600-frame simulation still moves 6.96 mm over its last five frames.

`cloth-trials.json` still ends its old pass-3 series at `tunic-o`; those older
records are not the dense carrier trial. The carrier's actual stage records
and gates are in its scratch directory. No delivery export or visual approval
is claimed by this recovery checkpoint. New work uses `tmp/age/tunic6/`.

## Continuation controls

A stage-by-stage SAT probe found zero body/hanger crossings in the inherited
dense simulation, then 94 after reduction. The old unconstrained interior
relaxation also reduced the measured chest width from 533.04 to 467.53 mm.
The local reducer now preserves sampled body outlines and the hanger crest,
limits relaxation to 1 mm, and keeps `Keep` vertices fixed. Simplifying redundant
boundary samples at 0.5 mm chord tolerance before decimation makes room for
these constraints and the rim. On that same dense source, the new reduction
has 10,799 sheet triangles, 533.04 mm chest width, zero body/hanger crossings,
and 0.634 mm boundary Hausdorff upper bound. These are pre-rim controls, not
final candidate gate results.

The sleeve initially retained only 10% of its depth although its bending rest
retained 40%. A regression control demonstrated that mismatch. Both now retain
40%, avoiding that extra structural compression. A fresh 600-frame trial is
being measured separately. Collar layering now uses 2 mm along the sewn
support normal, comprising half the 3 mm collar thickness and 0.5 mm clearance.
It has no added world-Z translation. A source-normal probe reduced collar
contacts but did not eliminate them; zero contacts are still required.

G30 also checks the exported hanger's triangle geometry against the unaged
export exactly, rather than relying on equal self-contact counts alone.
Positive and negative controls reject changed cloth, card pairs and a moved
hanger. Shared modules have not been edited by the tunic continuation.

## Dense milestone: tunic6-main

The new trial completed 600 frames with the chest form and baked the body and
three fallen strips to normal/AO maps. The body reduces from 30,000 working
triangles to 10,799 sheet triangles. Fallen pieces have 249, 249 and 59 sheet
triangles. Their maximum boundary Hausdorff upper bound is 0.639 mm, below
1.5 mm. Shoulder and armhole releases remain 60.56% and 58.93%; the three hem
runs release 36.41% of the pattern. Lip lift covers 46.40% of the open edge,
above 30%. Both structural and bending sleeve rest retain 40% depth.

The simulation is not a clean final cloth result. Its last five frames still
move 15.05 mm, and sharp-adjacency shares are 18.45% on the dense body and
24.40% on the reduced sheet, before visibility filtering. The inherited trial
had 787 dense self contacts; 780 touched a face excluded from Blender contact.
The fresh carrier still excludes 9,303 of 15,781 evaluated vertices. These
measurements identify rest tessellation and its contact exclusions as work
that remains; they do not justify exempting those contacts from G30.

`cloth-trials.json` now records this trial separately under `dense_aging`.
Preparation, simulation and bakes are saved under `tmp/age/tunic6/main/`.
The delivered asset is unchanged. Final geometry, cards and rendered gates
are measured after the finishing stage.

## Cards and heap milestone

`tunic6-main` now has fringe on the body and all three fallen pieces, a saved
2048-square opacity map with 197 stitch-hole centers, a mass-balanced mound,
a 400 by 300 mm floor skirt and 65 heap fibre cards. Body hem, seam allowance
and long-edge root coverage measure 70.38%, 84.79% and 73.76%. The fallen
pieces measure 64.25%, 58.36% and 77.24%; the first two miss the local 70%
coverage control because placements crossing surrounding geometry are rejected.
Contact avoidance also moves some roots up to 3.98 mm from the sheet, exceeding
the recipe's 0.2 mm normal offset. This finishing stage is not visually approved.
Wool lengths now follow the specified 7 mm median recipe and 3 to 18 mm limits.

A plane control showed that centered rim-only Solidify shifts the retained
sheet by 1.5 mm. The local implementation therefore departs from the plan's
zero offset: offset -1 preserves the baked, collision-tested surface and puts
the nominal 3 mm rim inward. Thickness is compressed where an inward ray meets
another support, including the floor. Tests verify the unchanged sheet, a
single shell, `WoolCutEdge` assignment and floor clearance on a plane. This
does not establish clearance on the folded candidate; final SAT still finds
contacts, including three fallen-strip/skirt contacts.

The scratch export has 18,219 triangles against 20,652 allowed, and reopening
`finished.blend` re-exports byte-identically. No delivered file was replaced.

## Final measurements: rejected candidate

`tunic6-main` passes 13 of 19 gates. It must not replace the delivered tunic.
All values below come from `tmp/age/tunic6/main/gates.json` and the actual
scratch GLB. G1 uses the close camera plus four turntable face-ID views, with
output dithering disabled. The 6% threshold is unchanged.

| Gate | Measured | Requirement | Result |
| --- | --- | --- | --- |
| G1 | 27.4034% visible sharp adjacency | At most 6% | Fail |
| G2 | 0.830892% normal-jump pixels | At most 2% | Pass |
| G3 | 270.601 px longest straight contour | At most 12 px | Fail |
| G4 | 0.559545 opening-width CV | At least 0.35 | Pass |
| G5 | 46.3956% lip length lifted over 3 mm | At least 30% | Pass |
| G6 | 1.110458 contour dimension | 1.15 to 1.40 | Fail |
| G20 | 27.2378% near-hanger sharp adjacency | At most 10% | Fail |
| G21 | 2 hanger pixels outside split hull | Zero | Fail |
| G22 | 0.270766 transverse sleeve axis ratio | At most 0.45 | Pass |
| G23 | 41.0679% retained arc; 84.7863% fringe | At least 35%; at least 70% | Pass |
| G24 | 99.9561% of unaged chest width | 92% to 108% | Pass |
| G25 | 70.3762% open-hem fringe coverage | At least 70% | Pass |
| G26 | 0.0 hem-height autocorrelation peak | Below 0.30 | Pass |
| G27 | 22.4458 mm heap height | 15 to 35 mm | Pass |
| G28 | 3 fallen cloth pieces | At least 2 | Pass |
| G29 | 0.9625 times expected mound volume; 5.195% inferred packing | Volume within factor 2 at 5% to 15% packing | Pass |
| G30 | 1,878 changed-part contacts; hanger 28/28, geometry exact | Zero changed contacts; exact hanger baseline | Fail |
| G31 | 18,219 / 13,768 triangles, ratio 1.323286 | At most 20,652, ratio 1.5 | Pass |
| G32 | 0.638654 mm boundary Hausdorff upper bound | At most 1.5 mm | Pass |

The final contacts are 1,805 body self contacts, 30 fallen-piece self contacts,
32 collar/body contacts, 8 collar/hanger contacts and 3 strip/skirt contacts.
Body/hanger crossings are zero. The fresh dense simulation has 4,326 self
contacts before reduction; 4,171 touch excluded rest faces. Repairing that
rest tessellation is necessary before another settling attempt. The long,
insufficiently irregular opening also fails G3 and G6. The export checker
additionally reports three nonmanifold body edges. No threshold or contact
exemption was added to accept this candidate.

All 13 local test scripts pass, including six strict-contact unit tests.
The original part names, node transforms and pivots are retained. Re-export
from the saved candidate is byte-identical. Lit navy-wool captures use the
baked normal/AO maps:

- `tmp/age/tunic6/tunic-before-after.png` (3200 by 1422).
- `tmp/age/tunic6/tunic-turntable.png` (3200 by 2844).
- `tmp/age/tunic6/tunic-closeup.png` (1600 by 1422, camera at 0.5 m).

Independent visual review is unavailable: the configured image-comparer
endpoint refuses connections, and the installed local model service returns
HTTP 500 even for a minimal text request. These files have no visual sign-off.
The delivered GLB, aged blend and textures remain unchanged.

Shared modules were not edited. Their reusable renderer should disable output
dithering for face-ID diagnostics. The shared topology policy also needs
explicit intended-boundary rules for fallen cloth, fringe cards and the dust
skirt; it currently marks those intentionally open surfaces as failures. That
policy change must retain all SAT checks and must not exempt the body's three
reported nonmanifold edges. The remaining rest-mesh and collar/rim clearance
work belongs in the tunic-local pipeline.

## Attachment constraints

The collar follows neckline edges without a vertical lift. Closed fittings
retain their topology and are seated against the reduced sheet
and its rim, rather than against the dense bake source alone. Clearance uses
continuous projected triangle overlap, including support triangles whose
vertices and centroids all lie outside the fitting. Collar top and bottom
vertices bind to the same sewn column; selecting the nearest base point for
the top ring attached it to a different station.

## Calibration

`aging-calibration.json` records 200 mm wool swatches. Maximum profile error
against the coarse `body-p` reference is 4.114 mm at 5.882 mm edges and 5.588 mm
at 2.985 mm edges, below the 10 mm limit. Tension/compression remain 500,
shear 350 and bending 0.3. Per-vertex mass preserves the reference total mass.
The measured damping factors are specific to the free-hanging swatch. Fallen
allowances use the original contact damping because the swatch factor makes
floor contact inject persistent lateral motion.

## Scratch pipeline

Run Blender with `--background --factory-startup --python-exit-code 1` and
`--python <script> -- <arguments>`. Long stages use `nohup` and separate logs
under `tmp/age/tunic6/`.

1. `age_tunic.py --stage prepare --out <scratch>` refines the stress bands,
   splits the shoulder, armhole and three hem runs without deleting their area,
   separates fallen allowances, adds detail stiffness and initializes the empty
   sleeve. Its bending rest key and structural starting section both retain
   40% depth. A 5,000-triangle carrier plus a real level-1 SIMPLE
   subdivision passes rest coordinates to Cloth at 30,000 working triangles.
   Attachment indices and vertex mass use the evaluated mesh. A stored rest
   key without this modifier does not affect Blender 4.5 cloth bending.
   Initial crossings fail preparation.
2. `age_tunic.py --stage simulate --frames 600 --out <scratch>` retains the
   hanger and chest form, simulates lip shrink, fits the details, generates a
   mass-balanced SDF mound and drops the allowances onto the floor at -0.95 m.
3. `age_tunic.py --stage bake --out <scratch>` reduces with `Keep` weights,
   relaxes only interior game vertices and bakes 2048-square body normal/AO maps.
   Boundary Hausdorff error must remain at most 1.5 mm.
4. `finish_aging.py --out <scratch>` adds alpha-scissor wool fringe, stitch
   holes, rim-only 3 mm `WoolCutEdge` geometry, a floor dust skirt and 65 fibre
   cards. Rim opacity follows the sheet opacity. The saved `finished.blend`
   must re-export byte-identically to `candidate.glb`.
5. `render_aging.py --input <scratch>/candidate.glb --out <images>` produces
   lit comparisons and alpha-aware diagnostics, including a 0.5 m close camera.
   Use the shared `compose.py --out <images> --prop dress_uniform` for sheets.
6. Run the shared `collision_export.py` on the actual GLB, saving
   `<scratch>/collisions.json`. Then run `measure_aging.py --out <scratch>
   --images <images>` with the supplied numpy/trimesh Python environment.
   Any failed or missing gate returns a failing exit status.

The game asset and `tunic-aged.blend` must not be replaced until all nineteen
G-gates pass and the concept comparison has been visually reviewed. Scratch
exports are candidates, not approved delivery assets. The unchanged hanger's
SAT count must match `tmp/age/tunic6/unaged-sat.json` exactly; no changed or new
part is exempt from the zero-intersection rule.

## Local controls and shared code

The Blender `test_*.py` controls cover source preservation, collar stations,
continuous fitting clearance, structural sleeve pressing, actual rest-angle
transfer, sub-contact rest faces, physical fringe coverage, winding-independent
root UVs, persisted stitch opacity and repeatable PBR export.
`test_hem_metrics.py`, `test_diagnostic_labels.py` and `test_tunic_contacts.py`
run with the supplied Python environment. Hem samples follow the actual
boundary graph; G26 measures local autocorrelation peaks after removing
garment-scale slope. Render labels decode
R+G coverage before material IDs, so antialiased wool/fringe/fitting boundaries
do not become synthetic holes. A negative control retains real constant-width
slots and rejects their straight contours at the unchanged 12 px threshold.

The pipeline imports the shared aging modules without editing them. Local
wrappers repair short rest edges, resample fringe at physical arclength and
pack explicit navy/AO/opacity pixels for glTF. The original single-texel strand
atlas vanishes under close-camera minification; bundled wool roots are tested
against that negative control.
