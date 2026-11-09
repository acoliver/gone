# GONE ceiling light, round 4

This pass starts from `../round3/fixture.blend`. The round-3 receiving channel, opaque channel baffles, recessed glass, thick fourteen-slot grille, chamfered rails and rounded generated lower lip are retained. All writes are confined to `tmp/lights-redo/round4/`. The ship has been adrift for about 1000 years.

## Geometry

`build.py` opens the round-3 Blender file. It displaces the transverse louvre centred at X=-0.14 m by up to 13 mm along the beam, with the displacement falling toward its attached ends. This changes the adjacent aperture widths and skew instead of relying on a small vertical dent. Rounded aperture terminal corners stay attached to the frame. The existing upward dents and 0.65 mm louvre chamfers remain.

Both source terminals are cut at X=±0.510 m and closed. Replacement end caps are 40 × 218 × 96 mm, with a 1.5 mm physical bevel. Each cap meets a 42 × 220 × 4 mm ceiling flange within the body's envelope. Four inset hexagonal end fasteners replace the old terminal fasteners. Each fastener has a 9 mm-diameter, 3 mm-deep recess cut into the end plate, exposing the head without extending it beyond the end plane. Four independent end-on rays verify that the first hit is the recessed head about 0.8 mm behind that plane. Existing rail bolt geometry is simplified to recover triangles. Neither cap nor bolt extends beyond the 1.10 × 0.10 × 0.22 m envelope.

Blender authoring uses +Z up and front -Y. Export explicitly sets `export_yup=True`, producing glTF +Y up, front +Z, with top Y=0. Cameras, ceiling and room lights are added only after the asset export.

## Glass output

A non-repeating 2048 × 256 emission texture assigns individual gains to all fourteen slot regions. Slots 4, 5 and 6 form a failed 210 mm tube section, 21.65% of the 970 mm glass length. The first seven regions use warm tint RGB (1.00, 0.77, 0.39), and the last seven use cool tint RGB (0.51, 0.77, 1.00). Individual irregular dirt shadows and narrow grime silhouettes reduce output behind each louvre. The diffuse glass base is darkened so that reflected base light does not erase emission differences. The slab remains opaque, rough and recessed, with the same side and end light baffles.

The emission texture's linear-luminance reduction and the tone-mapped 2.5 m capture's slot samples are reported separately. The first source texture had a 71.4% linear reduction, but the lit capture measured only 31.8% lower output. The failed-region texture gains were therefore reduced to 0.12, 0.10 and 0.14, with all other slot gains retained. The report requires a 60–80% screen-luminance reduction in the 2.5 m capture. Tone mapping compresses output differences. Those measurements are not visual verdicts.

## Weathering

Blender bakes position and normal atlases for the modified body, grille and hardware. Deterministic world-coordinate feature masks generate edge paint losses, dark exposed steel, oxide, rivet tails, channel seam streaks, grille soot and light dust on upper/edge surfaces. The broad base paint is olive. There is no broad brown recolour or rust displacement. Three non-aligned continuous spatial fields break up chip edges; no image tiles repeat.

Rust is concentrated near the lower body edge, end-cap edges, rail edges, fasteners and channel seams. Side streaks descend in Blender -Z, equivalent to glTF -Y. Gaussian streak half-widths are 4.2 to 5.8 mm, giving 7.0 to 9.7 mm full width at half maximum before length tapering. Side rivet tails reach 52 mm; channel-shoulder tails reach 65 mm, retaining their opacity until the final 12 mm taper. The first lit-mask measurement found only two streak pixels because the earlier linear taper erased the tails at the underside. The shoulder masks were corrected at their source. Soot follows the grille and receiving channel. Dust lightens upper and edge regions, including the rail shoulders.

`weather-disabled.png`, `grazing-weather-disabled.png` and `below-2p5m-weather-disabled.png` replace every metal albedo and ORM image with its clean-paint control. Geometry, glass, emission, lighting, camera, seed and sample count remain identical. Additional rust-disabled and streak-disabled images remove only those colour contributions. Unlit zone-mask renders locate edge, broad-face and streak pixels in exactly the same cameras. Their masks are used to measure contributions in the lit images, rather than treating texture coverage as visibility.

The fixed below-close comparison region is X=100..1099, Y=330..569, matching round 3. The target is at least three times round 3's mean RGB difference. The report also checks 2.5 m metal-mask contrast, edge-to-broad-face oxide contrast and streak contrast. A 16-pixel grid-gradient statistic and lag autocorrelations record blockiness/repetition checks on the lit weather difference, together with texture-atlas gradient statistics. These statistics cannot establish visual quality.

## Export checks and captures

`verify.py` independently loads the GLB with trimesh, applies glTF node transforms, and verifies dimensions, mounting height, triangle budget, welded closed topology and consistent winding. It counts fourteen centreline aperture runs. Full-footprint and channel grids check glass exposure against slot envelopes, including the displaced louvre and its anchored rounded corners. Twelve oblique ray grids check the apertures through the physical grille depth. The total is 740,201 rays. The centreline intervals also record the narrowed and enlarged apertures directly.

Beauty renders retain the round-3 camera positions, white secondary area fills, 1200 × 900 resolution, 48 CPU Cycles samples, AgX, seed zero and denoising. Views include below at 2.5 m, below close, grazing, three-quarter, both ends, emission off and matched weather controls. The 2160-pixel-wide labelled comparison sheet pairs round 3 and round 4 for each required view and includes concept 202 and 210 reference tiles. Source concepts are read-only.

## Reproduce

Use the installed Blender executable at `/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender`. The established Python environment at `/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python` supplies NumPy, SciPy, Pillow and trimesh for deterministic texture-array processing, the requested independent export verification and the comparison sheet. Geometry construction, UV/field baking, asset export and rendering use Blender only. No Godot modification, image generation, inference, downloads or installation are involved.

Run `build.py` in background Blender with four threads and `--python-exit-code 1`; run `weather.py` with the Python environment and `PYTHONDONTWRITEBYTECODE=1`; run `finish.py -- --export-only` in Blender; run `verify.py`; run `finish.py` in Blender; run `report.py`. Launch the render through `nohup` with logs under this directory to avoid the foreground watchdog. Create `READY` only after the report and all checks complete.

`fixture.blend` contains the packed export asset. `preview.blend` contains the beauty-render scene. `results.json` records the measurements and image paths. No image reading, appearance judgment or Godot installation is part of this pass. No foreign process was signalled, and no branch, index or repository configuration was changed.

## Final measurements

The exported GLB contains 2,512 triangles, fourteen slot runs, and dimensions [1.0999999642372131, 0.10000000149011612, 0.2199999988079071] m in glTF X/Y/Z, with top Y=0.0 m. Welded topology is closed and winding-consistent. The 740,201 aperture rays found no glass exposure outside the physical slot envelopes. Four end-on seat rays hit the recessed bolt heads rather than the plates.

The below-close fixed-region mean absolute RGB weather difference is 0.052420, or 3.890 times round 3. At 2.5 m, the mean difference over the rendered metal mask is 0.070212; 96.73% of those pixels exceed 2/255. The failed three-slot section is 69.02% darker in measured screen luminance at 2.5 m.

The lit edge-to-broad-face rust contribution ratio is 6.940. Streak colour contributes mean RGB difference 0.014282 over 6,350 grazing-mask pixels. Authored streak FWHM is 7.0–9.7 mm; measured horizontal lit-effect runs have median 8 pixels, with 10th–90th percentile 4–14 pixels. The lit 16-pixel grid-gradient ratio is 0.9739. No image tile repeats are authored; lag correlations are recorded in results.json.

The labelled sheet is 2160 × 6592 pixels. These are measurements, with no visual quality verdict.
