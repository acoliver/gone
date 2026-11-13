# c01 generated-surface medal fit, gone #130

This directory freezes `c01-hyseed0.glb`, its input image and its measured raw height/contour samples. The editable result is `medal-fitted.blend`. Fitting outputs stay under `tmp/issue130-v3/fit1/`. Production assets, tunic code, shaders, budgets and tests are outside this pipeline.

## Shape source and cage

`prepare.py` converts the unchanged generated mesh to Blender Z-up, front -Y, and applies one uniform scale for a 32 mm body width. It samples each angular section independently. The side bands preserve the generated silhouette, front shoulder, rear shoulder and their depth variation; they do not revolve a common profile.

The raw front-height contour supplies the five-point outline. Five ridge traces and five valley traces follow signed angular-curvature extrema on the generated surface. Smoothed three-dimensional splines share one measured central convergence. Their cage controls use even arclength spacing. `cage.py` embeds this graph and the measured rim curves with constrained triangulation. The body has sparse front/rear triangles and side quad bands. Only the suspension uses sparse QuadriFlow topology, followed by fitting at its control vertices and bounded fairing. Dense subdivision vertices never query the raw surface.

The generated star meets the rim in several sectors. Independent rim searches initially crossed the star outline there. The rim search domain moves outward around the measured preceding curve at those contacts, then samples heights from the unchanged generated surface. `features.json` records this contact correction. No donor sectors, symmetry constraint or replacement star template are used.

Body and suspension separate at the measured source-height contact plane 0.455. The fused loop/bar junctions separate at source X = +/-0.13 above source height 0.80, with internal cut caps. Hardware cross-sections retain their generated bulk. No suspension thinning or replacement swept tubes are applied.

## Fairing, normals and reduction

`fair.py` solves the enamel as one connected annulus between its embedded star and inner-rim boundaries. Its harmonic depth objective has zero raw-guide fidelity. All interior crease flags are cleared. Relief depth fairs between pinned feature curves; the rear retains its broad generated curvature. Full relief creases start outside the central convergence, allowing a rounded apex. High and low use continuous split-normal fans on the whole full-crease graph, with no sharp or split edges inside the field.

`reduce_low.py` performs visibility-weighted quadric reduction on the clean level-two subdivision. Star curves, rim steps, silhouette and rear transition remain fixed. Hidden rear faces receive lower error weight. Three-dimensional orientation and manifold-link checks apply to every collapse. Field collapses also preserve front projected orientation, preventing folded triangles in narrow sloping enamel strips.

Hardware reduction protects the projected contours at both required cameras. The loop also retains their support neighbourhood: contour edges alone allowed adjacent unpinned faces to create a different apparent outline. The allocation is 7,300 body, 2,300 loop and 900 bar triangles, totaling 10,500. Body faces adjacent to either projected contour receive 300x geometric-error weight. Source support bands can reduce; measured feature curves cannot.

`bake3.py` retains the front-safe 2048 tangent bake with a 0.1 mm body cage and 0.25 mm rays. `bake12.py` adds the established 0.6 mm / 1.2 mm rear-only pass. Its UV mask excludes front and hardware core texels. `bakecheck.py` measures reach and reconstructed tangent-normal errors numerically.

## Run and inspect measurements

Use the existing Hunyuan Python environment and Blender 4.5.11. Check running processes first. Launch long stages with `nohup`, put logs in the output directory, and poll their process IDs. Do not terminate other jobs.
## Fitting pass 2

Pass 2 starts from `tmp/issue130-v3/fit1/medal-fitted.blend` and writes its editable blend and outputs to `tmp/issue130-v3/fit2/`. It does not replace the fit1 blend or the frozen source. The original pipeline description refers to fit1.

`fair2.py` couples front depth slopes, tapers relief-crease ends and strongly fairs the generated rear from its rim boundary. `edit_fit2.py` thins the existing loop and consolidates generated bar rails. `run_fit2.py` applies pass-specific reduction and output settings to the established utilities. `unwrap2.py` keeps a continuous front chart and assigns intrinsic UV area to steep walls. Run `build2.sh`, `bake2.sh`, then `finish2.sh`, using the same nohup/process-polling rules above. `build2.sh --uv` changes UVs only; `--export` re-evaluates existing fit2 cages without rebuilding their controls.

`inspect_fit2.py`, `bake_audit2.py`, `joins2.py`, `maps2.py` and `extra2.py` measure camera-ray projections, bake correspondence, terminal slopes, depth/normal rasters, rear fairness and hardware contacts. `comparisons2.py` makes identical fit1/fit2 finding crops. No script makes image judgments. Causes, dimensional changes and checks are summarized in fit2's `fit-notes.md` and `result.json`.


Run `prepare.py`, then `build.sh`, `measure.sh` and `finish.sh`. `surface_gate.py` checks the original geometry and conservative sub-0.5-pixel silhouette requirements before baking. `final.py` checks exported geometry/UV parity and writes `fit-notes.md` and `result.json`.

The standard capture set has unchanged neutral-clay lights and six cameras. The input camera is numerically matched from the input blue-field ellipse. Five-rotation controls use one fixed camera and fixed lights, rotating the mesh by offset + k*72 degrees. They extract identical pixel crops without rotating images. Generated notch angles remain asymmetric.

These scripts assemble and decode images but make no visual judgments. The game-camera measurements use the frozen prior registration; they are standalone projections, not mounted runtime captures.
