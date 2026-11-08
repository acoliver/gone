# Locker generated face images

The current aged finish maps a complete generated image onto each visible face, following `tools/prepare_hatch_paint.py`. `faces/face-layout.json` records physical dimensions, pixel cells, UV rectangles and concept crops. `faces/selection.json` records chosen seeds, source-matched colour calibration and final measurements. Each face has at least four saved FLUX.2-klein candidates. The image owns paint loss, corrosion borders and trails; the hatch's `paint_fields()` rule derives only relief and roughness. The top image already contains settled dust. Hardware uses its own heavily corroded generated image with pitting from luminance, at equal physical pitch on both axes.

`tools/quarters_aging/generate_locker_faces.py`, `select_locker_faces.py` and `finish_locker_faces.py` reproduce generation, selection and atlas packing. Optional attached stains stay at or below 30% opacity and sample receiving-image rust colour. Procedural island and streak fields no longer drive the aged material. The locker section of `docs/art/quarters/README.md` lists dimensions, seeds, measured gates, retired design-specific checks, commands, tests and captures. The ship's age is about 1000 years.

## Historical swatch method

The following describes the superseded fourth-pass composition. Its generated inputs remain available for historical reproduction and regression fixtures. The earlier masks imposed evenly distributed broad-face damage, edge outlines and recognisable shapes even when their colours came from generated images.

## Saved inputs and generation

All source pixels come from our concept images. Crop coordinates are Pillow XYXY with exclusive right and bottom bounds:

| Class | Concept | Generation input crop | Candidate seeds |
| --- | --- | --- | --- |
| Broad panel | `docs/art/quarters/concept-now.png` | 445, 338, 535, 411 | 95030, 95031, 95032 |
| Heavy loss | `docs/art/corridors/hatch-concept-rusted.png` | 784, 132, 872, 241 | 95130, 95131, 95132 |
| Dust | `docs/art/quarters/concept-now.png` | 464, 266, 561, 306 | 95230, 95231, 95232, 95330, 95331, 95332 |

The raw PNGs, input crops, prompt files and per-candidate metadata are saved here. Each metadata file includes the exact prompt and generation command. Seeds 95330 through 95332 use `dust-settled-prompt.txt`, which asks for a continuous deposited layer without vertical staining. Generation ran sequentially under `nohup`, never concurrently on the GPU.

The command uses `HF_HOME=/Volumes/XS1000/hf-cache`, `HF_HUB_OFFLINE=1` and `/Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-flux2-edit --model flux2-klein-4b --quantize 4 --steps 4 --width 768 --height 768`. The source crop, prompt, seed and output paths are in each metadata file. No packages were installed.

## Selection and calibration

Chosen seeds are panel **95031**, heavy loss **95132** and dust **95332**. `selection-scores.json` records every candidate's paint/rust Lab mean and standard-deviation differences, secondary autocorrelation, border luminance difference and planar illumination gradient. `visual-selection.json` records image-comparer's rejection of hardware-like borders, repeated grids, regular spots and pronounced vertical staining. Colour-class differences must each be at most 8 in D65 Lab. Secondary autocorrelation must be at most 0.5 beyond a physical offset of 50 mm.

The panel colour reference is the interior crop 475, 348, 525, 398 of the same concept. This excludes the lamp-facing corner and input edges rather than treating their illumination as paint variance. Its pixels are saved in `panel-reference.png`; the original generation input is unchanged. `reference-crops.json` records that distinction.

`albedo-calibration.json` saves the selected images and their linear RGB factors, mean-preserving linear contrast and paint white balance. The dust image's fitted log-linear illumination plane is divided out before reflectance fitting. The panel's paint receives a bounded white balance to remove the concept lamp's warm cast; the heavy-loss correction retains a mostly rusted surface. All recorded colour scores include these transforms. The sRGB decode, linear reflectance factors and sRGB encode use the hatch's `calibrate_albedo()` implementation. Paint/rust classification uses the hatch's unchanged `paint_fields()` chroma rule.

Run `tools/quarters_aging/select_locker_swatches.py` with the installed Hunyuan Python to reproduce selection, calibration and `tmp/mat/locker/pass3/swatches.png` from these saved inputs. The sheet shows source crops, raw generated images and calibrated albedo, in that order.

## Fourth-pass atlas composition

`tools/quarters_aging/locker_swatches.py` still projects calibrated source colours at 300 pixels per metre. It separates paint and oxide pigments into class-conditioned colour layers, removing the baked paint/rust border from their RGB. The original projection offsets remain panel (280, 0), vertical heavy loss (340, 0) and horizontal heavy loss (280, 80), in addition to the common origin.

The atlas alpha now locates broken edge loss and small blisters. Source pigment controls ordinary reach from 5 to 25 mm; a few high-cavity impact points receive deeper bites. Rotated metre-space noise and phase-warped gaps break the band into separate losses, with intact paint between them. Coarse-to-fine placement lets small and large side blisters coexist. Individually seeded angular profiles add lobes and bites, with an offset solved to preserve each island's area. Their maximum radius is 24.2 mm, leaving room for the fine breakup and the 3 mm shear displacement within the 60 mm diameter limit. The shader reconstructs coverage cubically before derivative-width sharpening, then adds bounded scan-scale breakup. Shared hatch steel, paint and oxide albedo, normal and ORM details repeat at a 0.20 m pitch. Grain uses measured scan luminance without importing green scan pigments into the locker palette.

Exact mesh-part IDs assign hardware. Real geometry-edge distance locates worn grey steel, independently of the fixture distance used to mark neighbouring receiving surfaces. Dark and orange oxide colours still come from the generated loss swatch, with pitting in the baked and detail normals.

Dust colour is smoothed over 80 mm and its linear-light contrast reduced to 5% around the same mean. Its low-frequency density increases against lips and in cavities, while bevels shed powder. This removes the source swatch's branching marks and the earlier speckled appearance. Effect-disabled controls expose the same underlying surface.

Runoff uses float outlets and source-derived pigment. Paired rivets receive narrower separate trails; upper fasteners have longer runs, and low fasteners have faint stains. Width tapers to zero, opacity fades, and millimetre-scale drift changes the path. Partial-opacity pigment mixing retains a rust hue. The shader computes pixel footprint before the per-source drop branches: evaluating derivatives inside those branches produced invalid whole-row stain coverage at outlet starts. The isolated-runoff gate rejects any such coverage outside the physical outlet envelopes.

The visible-streak gate now follows Andrew's pass-four definition: connected narrow rust-coloured runs at least 40 mm long, starting within 10 mm below a fastener or opening and differing from paint on both sides by at least 0.03 linear. At least 50% of door and upper-side fasteners must qualify. This replaces the historical rust-row and fixed-strip predicates; their old rust-row measurements remain diagnostic data. All other prior thresholds remain unchanged. The README and `tmp/mat/locker/pass4/gates.json` record the reason, complete results and full per-fastener distribution.

Baking consumes the saved PNGs and calibration, without running an image model. Both finish sets reproduce byte for byte. The mesh, geometry masks, UVs and as-built atlas bytes remain unchanged. See the locker material section of `docs/art/quarters/README.md` for commands, counts and image paths.
