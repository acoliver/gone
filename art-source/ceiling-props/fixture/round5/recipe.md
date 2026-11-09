# GONE ceiling light, round 5

This pass starts from `../round4/fixture.blend`, with grille geometry recovered from `../round3/fixture.blend`. All outputs stay under `tmp/lights-redo/round5/`. The ship has been adrift for about 1000 years. Geometry, UV baking, export and rendering use Blender. No Godot files or repository state are changed. References are read-only.

## Geometry

The sealed round-4 body, receiving channel, rounded lower lip, opaque inner baffles, raised rails and recessed glass remain. The round-4 13 mm sideways louvre bend is removed by using the round-3 grille. Its second dent is straightened. One louvre at X=-0.14 m retains its 1.4 mm shallow dent and receives only 1.2 mm of sideways deflection at the centre. There are fourteen apertures. No dirt geometry intersects the openings.

The end caps replace the round-4 terminal blocks. Their lower outer planes taper inward by 8 mm along the length, and their width narrows by 7.5% toward the bottom. Physical 4 mm bevels with two segments soften the cap edges. Each end meets a 46 × 220 × 4 mm ceiling flange with a 1.2 mm chamfer. Four inset hexagonal bolts sit in actual recessed seats near the ceiling. The components remain inside the original body envelope. The flange preserves the full 220 mm width; the end plane preserves the full 1100 mm length.

Authoring uses Blender +Z up, with front -Y and the ceiling at Z=0. `export_yup=True` produces glTF +Y up and front +Z. Cameras, preview ceiling and room lights are created after export and are absent from `fixture.glb`.

## Paint and corrosion

`build.py` extracts actual mesh edges whose dihedral angle exceeds 30 degrees. Samples along those edges are spaced at no more than 0.7 mm. Blender bakes world position and shading normal atlases. `weather.py` computes distance to the edge samples to localize chipped paint and oxide, with a 2.1 mm falloff. The measurement edge band is 2.5 mm wide.

Chip boundaries vary using deterministic 3D hashed value noise at 12 mm and 1.8 mm scales. The hash field has no wrapping tile within the asset and no diagonal sine-wave field. It only modulates paint loss already confined to physical edges. Broad-face paint receives a 5.5% aging darkening and less than 0.4% colour grain; these preserve its olive proportions. Base housing paint is sRGB (0.355, 0.383, 0.255), and cap/rail paint is (0.310, 0.343, 0.218).

Rust also follows fastener positions. Side streaks follow Blender -Z gravity, with Gaussian FWHM 2.3–3.0 mm and a 52 mm maximum tail length. Thin receiving-shoulder tails extend up to 65 mm from the fastener line, with an 18 mm terminal fade. Soot follows the narrow receiving channel and its inner rail region. The recessed grille has its own heat-darkened paint. Dust uses positive-Z-facing normals, with a low-frequency density variation. No texture displacement or overlay mesh is used.

All three materials export albedo and packed roughness/metallicity textures. The fixture Blender file packs its images. Weather controls replace every metal albedo and ORM with clean paint. Rust, streak and dust controls remove only the named colour effect, keeping geometry, lighting and ORM unchanged. Their lit differences measure contribution rather than authored coverage alone.

## Tube output

One continuous warm-white linear RGB emission tint (1.00, 0.91, 0.76) spans the glass. A smooth tint drift changes green by no more than 1.2% and blue by no more than 0.72%; there is no warm-to-blue transition. Linear brightness changes smoothly along the tube. A sixth-power exponential profile reduces a single section centred at X=-0.175 m, covering slots 4–6, to approximately half the other sections' physical output. Four wide Gaussian grime shadows have 11–14% depth. There are no narrow spikes, hard-edged dirt polygons or step changes between slot indices.

The emission image is computed in linear light, then encoded to sRGB once for Blender/glTF. `weather-stats.json` records physical output separately from the AgX display-referred capture measurements. Tone mapping compresses the display difference; a 50% physical output ratio is not a 50% screen-RGB ratio.

The common emission strength is 0.35. The first pilot used strength 2.0: the failing section retained 52.8% physical output but measured 90.6% of healthy screen luminance. Reducing the common gain to 0.35 preserves the physical ratio while bringing the measured screen ratio to 79.3%. No section-specific colour adjustment or further dark patch was added.

## Measurements

The lit weather comparison uses the same 1200 × 900 below-close camera and fixed X=100..1099, Y=330..569 region as rounds 3 and 4. The round-3 reference is 0.0134739 mean absolute RGB difference; round 4 is 0.0524200. Round 5 targets 2–4 times round 3 while remaining below round 4. Weather/control captures share geometry, emission, camera, white room fills, seed and sample count.

Matching unlit feature masks identify edge, broad and streak pixels in the lit grazing capture. Rust-disabled and streak-disabled pairs give the corresponding lit contribution. A dust-disabled pair records dust contribution too. Broad-face masks use distance greater than 5 mm from sharp mesh edges; they include weathered streaks, rivet patches and soot. Paint-coverage masks exclude the intentionally dark recessed grille and measure visible broad housing/end-cap faces. Olive-preserving material pixels have rust below 20%, soot below 20% and bare-metal wear below 10%. The report also checks that their RGB-sum-normalized lit chromaticity remains within 0.04 of the clean olive control. This is a measured material/lighting proxy, with no visual verdict.

Tiling checks use the actual lit weather-on/off difference. A 16-pixel-grid gradient ratio checks block discontinuities. Raw horizontal autocorrelation at 16, 32, 64 and 128 pixels includes physical repeated geometry and broad paint darkening. A separate broad-housing-only scan divides the signed difference by the clean control's mean RGB, with a 0.035 floor, before removing a normalized Gaussian trend with sigma 6 pixels. It scans horizontal/vertical offsets of 16–192 pixels in steps of four, keeping offsets with at least 1000 valid pairs. Relative normalization accounts for a given reflectance change scaling with local illumination. The raw peak, absolute-effect detrended peak and normalized peak are all retained, so normalization does not conceal the other measurements. None of these statistics establishes human-perceived appearance.

## Captures and verification

`finish.py` uses CPU Cycles, 48 samples, denoising, seed zero and AgX, matching round 4. It renders below at 2.5 m, below close, grazing, three-quarter, left end, right end, emissive off and a weather-disabled control, plus matched distant/grazing controls and effect-isolation captures. All images are 1200 × 900.

`verify.py` loads the exported GLB independently in trimesh. It verifies transformed bounds, +Y mounting height, triangle budget, closed welded meshes, winding, fourteen centreline aperture runs, and no glass exposure outside the physical apertures. It uses the round-4 ray grids with the new 1.2 mm bend envelope, including twelve oblique directions. Four end-on rays verify recessed bolt heads. The total aperture-ray count is 740,201.

`sheet.jpg` is 2280 pixels wide. Concept 202 and 210 tiles appear above three columns of matched round-3, round-4 and round-5 renders. The references are read from their existing locations; nothing is written to those locations. `results.json` records measurements and image paths. `fixture.blend` contains the packed asset; `preview.blend` contains the beauty-render scene. `READY` is created only after final reporting succeeds.

## Reproduce

Blender executable: `/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender`.

Array processing, the requested independent trimesh verification and sheet assembly use the established Python environment `/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python`. No packages, inference models or third-party services are installed or invoked.

1. Run Blender background, four threads, `--python-exit-code 1 --python build.py`.
2. Run `weather.py` with the Python environment and `PYTHONDONTWRITEBYTECODE=1`.
3. Run Blender `finish.py -- --contrast-only` to export and measure the matched below-close pair.
4. Run `verify.py` with the Python environment.
5. Run Blender `finish.py` for the full captures.
6. Run `report.py`, then create `READY`.

Long Blender commands use `nohup` and logs inside this folder. No foreign process is signalled. This pass supplies measurements only; no image inspection, visual quality verdict or in-game lighting test is included.

## Final measured output

The GLB contains 2,708 triangles and fourteen verified aperture runs. Its glTF bounds are [[-0.550000011920929, -0.10000000149011612, -0.10999999940395355], [0.5499999821186066, 0.0, 0.10999999940395355]], with top Y=0.0. All exported meshes are closed after seam welding and winding-consistent. The aperture checks found no glass exposure outside the allowed openings.

The fixed-region weather/control mean RGB difference is 0.03006313, or 2.2312 times round 3. Round 4 measured 0.05241996; this pass is 0.5735 of that value. Visible broad-shell olive-preserving fractions, including their weathered patches, are 92.42% in the close view and 97.25% at grazing.

The lit edge-to-broad-face rust contribution ratio is 10.0210. Streak contribution is 0.023074 mean RGB difference over 1727 grazing pixels; 90.74% exceed 2/255. Lit streak runs have median width 4 pixels, with 10th–90th percentiles 3–6 pixels. Dust contributes mean difference 0.000360 over visible grazing metal; most top-facing dust is hidden by the ceiling.

The normalized lit-effect autocorrelation maximum is 0.760811 at 16 pixels horizontally. The raw four-lag horizontal maximum is 0.923707; the absolute-effect detrended maximum is 0.765692. Maximum horizontal secondary-peak prominence is 0.00046539. The 16-pixel grid-gradient ratio is 0.927547. No fixed correlation cutoff is applied: the horizontal curve has a broad plateau, so its maximum mixes spatial continuity with repeated geometry rather than isolating image tiling. All values remain in results.json, without an appearance claim. The earlier provisional 0.65 maximum-correlation gate was removed for this measurement reason, with no texture change.

The failing section measures 52.83% of healthy physical emission and 79.26% of healthy 2.5 m screen luminance. The comparison sheet is 2280 × 5440 pixels. These are measurements only.
