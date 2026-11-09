# GONE ceiling light, round 6

This pass starts from `../round5/fixture.blend` and copies the round-5 scripts into this directory. Round-5 body, grille, receiving channel, rails, rivets, recessed glass and single shallow bent louvre remain. The ship has been adrift for about 1000 years. All writes stay in `tmp/lights-redo/round6/`. Earlier rounds and concept tiles are read-only. No tracked files, branches or git state are changed.

## Geometry

Blender rebuilds the two end caps with 12 mm single-plane chamfers, within the requested 10–15 mm range. Their bottom edges taper inward by 11 mm along the length and 12% across the width. Each end gains a 2 × 184 × 58 mm end flange with a 0.7 mm bevel. Four recessed hexagonal bolts mount at Blender Z=-28 mm. Existing 46 × 220 × 4 mm ceiling flanges keep their 1.2 mm chamfers. The assembly remains within 1.10 × 0.10 × 0.22 m.

Authoring uses Blender +Z up, front -Y, and ceiling Z=0. Export uses `export_yup=True`, producing glTF +Y up, front +Z, and top Y=0. Export happens before adding preview ceiling, cameras and fill lights. `fixture.blend` contains only the asset scene inherited from round 5, with packed texture images; `preview.blend` contains the render setup.

## Structure-driven weather

The inherited field-baking method is unchanged: sample mesh edges with sharp dihedral angles, bake world positions and normals in Blender, and calculate physical distance to those edges. No wrapping texture field, repeated image tile, displacement or dirt mesh is added.

The chip falloff expands from 2.1 to 3.4 mm. Nonperiodic hashed 3D fields still modulate only edge-constrained chipping. The finer field has more weight in the chip boundary. Bare-metal wear rises from 20% to 24% of the chip mask. Rivet-head weather footprints expand from 4.5 to 6 mm.

Channel soot increases from 50% to 68% and its transverse falloff expands from 6 to 9 mm. Grille edge soot rises from 14% to 22%, with additional Gaussian grime confined to the physical slot corners. Side rust tails extend up to 73 mm, with 22 mm terminal fades and Gaussian FWHM 3.16–4.16 mm. Receiving-shoulder tails extend up to 78 mm, with 20 mm terminal fades. Gravity remains Blender -Z. Broad paint aging is 8.5%, compared with 5.5% in round 5, while its olive colour proportions are preserved. A nonperiodic 7 mm hashed field modulates soot density only inside the structure-defined channel, grille, corner and rail masks. This gives the two channel edges different accumulation patterns. Dust remains normal-driven as in round 5.

The weather-disabled controls use identical geometry, emission, room lights, camera, tone mapping, seed and sample count. They replace all metal albedo and ORM maps with the clean controls. Rust-, streak- and dust-disabled views isolate the named colour contributions while retaining the weathered ORM.

## Emission

The common glass emission strength is 3.0, compared with 0.35 in round 5. Warm-white linear RGB (1.00, 0.91, 0.76), continuous low-amplitude tint drift, broad grime shadows and the single failing section are unchanged. Slots 4–6 retain 52.83% of the other sections' physical light output. Brightness remains a continuous function of position, without per-slot steps or narrow spikes. No compositor glow or extra preview light is used to inflate the emission measurement.

`results.json` reports the 2.5 m display-referred luminance of every slot, healthy and failed groups, and visible olive broad-shell pixels from the matching camera. Their screen-luminance ratios include AgX compression and therefore differ from the physical emission ratio.

## Matched captures and measurement

All beauty views match round 5: CPU Cycles, 48 samples, denoising, seed zero, 1200 × 900 pixels, AgX, a dark ceiling, and white area fills of 18 W and 12 W. Views include below at 2.5 m, below close, grazing, three-quarter, both ends, emissive off and weather disabled, plus matched distant/grazing and effect-isolation controls. Unlit measurement masks use the same camera and geometry.

The fixed below-close comparison region is X=100..1099, Y=330..569, as in rounds 4 and 5. Its target mean absolute RGB difference is the midpoint of round 4 (0.0524199619) and round 5 (0.0300631318), or 0.0412415468, on a 0–1 scale. The report also records the 2.5 m metal-mask difference. Broad-shell olive coverage excludes the intentionally dark recessed grille and uses the round-5 composition and chromaticity criteria without changes. Required visible olive coverage is at least 65%.

The tiling measurement is identical to round 5. The signed lit weather/control difference is divided by clean-control mean RGB with a 0.035 floor, restricted to broad housing faces, and detrended with a normalized Gaussian sigma-6-pixel filter. Both axes are scanned at lags 16–192 pixels in steps of four, requiring at least 1000 valid pixel pairs. Round 5's maximum was 0.7608111974. The raw and absolute-effect peaks, secondary-peak prominence and 16-pixel grid-gradient ratio are also retained. These statistics are measurements, not a visual verdict.

## Verification and sheet

`verify.py` loads the exported GLB independently with trimesh. It checks transformed dimensions, mounting height, triangle budget, welded closure and winding, fourteen centreline aperture runs, no glass outside the slot envelopes, and twelve oblique ray directions. The four bolt-seat probes follow the revised bolt height. `sheet.jpg` is 2280 pixels wide, with read-only concept 202/210 tiles and matched round-4/5/6 views side by side.

Blender executable: `/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender`.

The existing `/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python` performs array processing, requested trimesh verification and sheet assembly. No package installation, inference models, nested agent or Godot process is used. Background jobs are limited to this pass's own commands; no foreign process is signalled.

To reproduce, run `build.py` in Blender background with four threads and `--python-exit-code 1`, run `weather.py` in the established Python environment, run `finish.py` in Blender, then run `verify.py` and `report.py` in that Python environment. Set `PYTHONDONTWRITEBYTECODE=1`. All logs and outputs belong in this directory. `prepare.py` and `prepare_report.py` record the initial derivation from round 5; the final scripts contain any measurement-driven adjustments. Create `READY` only after the checks and report succeed.

No visual inspection or visual verdict is supplied. In-game lighting is not tested.

## Final measurements

The exported GLB contains 2,664 triangles, fourteen verified apertures, and dimensions [1.0999999940395355, 0.10000000149011612, 0.2199999988079071] m, with top Y=0.0. All welded meshes are closed and winding-consistent. The aperture checks found no glass outside the allowed slots.

Weather/control mean RGB differences in the fixed region are round 4 0.05241996, round 5 0.03006313, and round 6 0.04129770. The midpoint target is 0.04124155; the measured deviation is +0.00005615. At 2.5 m the metal-mask differences are round 4 0.07021210, round 5 0.03158197, and round 6 0.04547713.

Visible broad-shell olive-preserving coverage is 80.84% close, 93.05% grazing, and 81.46% at 2.5 m. The normalized autocorrelation peak is 0.60028561, compared with round 5 0.76081120. The raw peak is 0.84631880, compared with 0.92370652; the absolute-effect detrended peak is 0.65774622, compared with 0.76569244.

Blender and exported glTF emission strength are both 3. In the below-2p5m capture, mean display luma is 0.857438 for the slots and 0.233615 for sampled olive broad faces, a ratio of 3.6703. Healthy slots average 0.871928; the failing section averages 0.804311. That section retains 52.83% physical emission and 92.25% display luma after AgX.

The labelled comparison sheet is 2280 × 5440 pixels. All final numerical gates passed. These are measurements, without a visual or in-game verdict.
