# Dense aging for the pilot tunic

The dense-aging pipeline is experimental. No candidate has replaced the game
asset. Acceptance requires every measured gate and a visual concept comparison;
passing local controls does not certify a trial's geometry or appearance.

The tunic represents 1000 years of dry aging. Its cut, collar, shoulder boards,
buttons and medal must remain recognizable. The source is `tunic-working.blend`,
with `body-p` as the wool reference. `ShoulderChestForm` remains an invisible,
unexported collider.

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
under `tmp/age/tunic5/`.

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
SAT count must match `tmp/age/tunic5/unaged-sat.json` exactly; no changed or new
part is exempt from the zero-intersection rule.

## Local controls and shared code

The Blender `test_*.py` controls cover source preservation, collar stations,
continuous fitting clearance, structural sleeve pressing, actual rest-angle
transfer, sub-contact rest faces, physical fringe coverage, winding-independent
root UVs, persisted stitch opacity and repeatable PBR export.
`test_hem_metrics.py` and `test_diagnostic_labels.py` run with the supplied Python
environment. Hem samples follow the actual boundary graph; G26 measures local
autocorrelation peaks after removing garment-scale slope. Render labels decode
R+G coverage before material IDs, so antialiased wool/fringe/fitting boundaries
do not become synthetic holes. A negative control retains real constant-width
slots and rejects their straight contours at the unchanged 12 px threshold.

The pipeline imports the shared aging modules without editing them. Local
wrappers repair short rest edges, resample fringe at physical arclength and
pack explicit navy/AO/opacity pixels for glTF. The original single-texel strand
atlas vanishes under close-camera minification; bundled wool roots are tested
against that negative control.
