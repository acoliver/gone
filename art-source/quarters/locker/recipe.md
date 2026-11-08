# Locker aged-colour swatches

The aged locker uses generated colour, following `art-source/hatch/gen4-recipe.md` and `tools/prepare_hatch_paint.py`. The earlier noise-based colour and flake masks produced evenly distributed broad-face damage, heavy outlines and blocky boundaries. Noise remains only in surface relief, pitting and roughness. It does not supply the aged paint, rust or dust colours.

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

## Atlas composition

`tools/quarters_aging/locker_swatches.py` projects the images at 300 source pixels per metre using dominant physical face axes. Projection offsets select non-repeating regions without changing scale. Horizontal faces use an offset that keeps the roof inside the source image. Geometry edge distance, fixture distance and cavity exposure control where the heavy-loss image replaces broad-panel colour. The heavy-loss image's own paint islands and colour variation shape the band boundary and its reach. No independent noise field creates corrosion islands.

Saved physical projection offsets, in source pixels, are panel (280, 0), vertical heavy loss (340, 0) and horizontal heavy loss (280, 80), in addition to the common projection origin. Region selection measured panel rust, straight boundaries and autocorrelation, and measured every panel edge's variation and actual hardware rust for the loss image. Edge reach uses the heavy-loss red-pigment contrast between its fifth and ninety-fifth percentiles, spanning 31 to 80 mm. The lower exposure was increased after a smaller panel-image region reduced pooled painted-steel rust below the retained 25% gate; this changes the material, not that gate's threshold. All 57 final gate values and the four unresolved failures are reported in the locker README.

Hardware membership comes from exact baked mesh-part IDs. Fixture bounding boxes locate receiving surfaces but cannot assign their paint to the hardware class. This prevents rectangular heavy-loss patches from leaking off fixtures onto the door. Up-facing steel receives the heavy-loss colour beneath the generated dust layer. Disabling dust in the capture material exposes that same underlying surface for the visibility control.

Runoff samples the stronger oxide pixels of the calibrated heavy-loss image at reduced opacity. Trails retain float source positions, span 4 to 12 mm at their origins, taper towards their tips and fade before ending within 200 mm. Most rivet trails are shorter than the vent and handle trails. Generated dust supplies the up-face colour; there is no procedural speckle overlay.

Baking consumes the saved PNGs and calibration, not a new model run. Repeated geometry and finish bakes must reproduce all exported mask/finish files and the GLB byte for byte. See the locker material section of `docs/art/quarters/README.md` for commands and the measured capture gates.
