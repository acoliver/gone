# Taller quarters console and native keys (#129)

The fitted console now has a 16:10 display and 24 Naleya key legends.
The saved source is `tools/blender/quarters/console/console-working.blend`.
This changes the console only. Room furniture, cameras, lighting, clothes,
interaction dispatch, the idle underscore, message wording and the
60/180/60-tick corruption/message/fault sequence are unchanged.

## Shape and placement

| Measurement | Accepted baseline | #129 source/export |
| --- | ---: | ---: |
| Active display width | 0.874 m | 0.874 m |
| Active display height | 0.238 m | 0.54625 m |
| Active aspect | 3.672:1 | 1.600:1 |
| Console height | 0.690 m | 0.9388873 m |
| Width | 1.100 m | 1.100 m |
| Exported depth including front rivets | 0.55310 m | 0.55310 m |
| Screen backward tilt from vertical | 30.9638 degrees | 30.9638 degrees |
| Triangles | 5,088 | 5,112 (limit 15,000) |
| State atlas size | 3072 square | 4096 square |

`refit.py` deforms the saved head cages rather than generating a replacement.
The glass lower edge remains at exported glTF `(0, 0.454878712, 0.062092286)`.
The bezel sides, upper trim, gasket, glass and upper rivets extend together.
The cap transitions inward by 25.6 mm above source height 0.925 m to keep a
closed upper cap within the existing rear depth at the retained tilt.
The initial taller version clipped the unchanged close camera. Trimming
18 mm of upper metal border along the screen plane reduces the top bar from
30 to 12 mm and the cap height by 15.4349 mm. Its 30 mm depth, 1 mm gap above
the glass and contacts with both side rails remain intact. The glass, gasket,
upper rivets and lower border do not change. No display height is sacrificed.
The final cap transition occupies 13.8873 mm of vertical height.
An independent comparison with the baseline GLB found identical world-space
vertices for all 35 lower parts: lower housing, support, shoe, control panel,
24 keys, three toggles, three sockets and lower housing rivets. Relative to
`0f26ad0`, only the housing, left/right rails and top bar change; the other
39 mesh parts have identical world-space point sets.

The layout's nominal console top changes from 1.45 to 1.6988873 m. This is
its existing 0.76 m datum plus the new source height. It prevents the runtime
fitter from compressing the new screen back to the old height. It does not
move the desk or console base. The existing fitter still seats the console
on the actual worktop below the rear upstand. Collision uses the same X/Z
footprint and the taller head envelope. Existing desk-contact, desk-item,
walkway, reach and shared-collider tests remain in force.

## Native key layout

`export_legends.gd` calls the production `Naleya.layout()` and
`Naleya.expand_strokes()` APIs used by `ShipTextCanvas._append_native()`.
It saves the returned filled quads in `legends.json`. No font or independent
copy of the glyph paths is involved. The regression test compares every
exported quad with production stroke expansion.

Rows run from the front edge toward the display; columns run left to right
when facing the keys. The tokens below describe the inputs to the exporter,
not Latin lettering on the asset.

| Blender row / keys | Input tokens | Native signs |
| --- | --- | --- |
| 0 / `Key_0_0` through `Key_0_5` | 0 1 2 3 4 5 | mo na mu shi le chi |
| 1 / `Key_1_0` through `Key_1_5` | 6 7 a e i o | wi shu a e i o |
| 2 / `Key_2_0` through `Key_2_5` | u pa pe pi po pu | u pa pe pi po pu |
| 3 / `Key_3_0` through `Key_3_5` | ta te ti to tu ka | ta te ti to tu ka |

The first eight keys use Naleya's octal digit mapping. The remaining keys
use valid V/CV signs. Each sign is 24 mm high, with the native stroke width
and aspect preserved. Positive glyph Y points toward the display on the
key deck. `bake_legends.py` maps the quads through the actual key-top UVs
and inlays pale dielectric ink into both state albedo/normal/ORM atlases.
The aged ink is duller but remains light against the dark keycap. This is
asset lettering only; there is no keyboard input feature.

The atlas grows to 4096 because the least-inked vowel forms had fewer than
100 half-coverage texels at 3072 after the taller head's UV repack. Increasing
resolution retains the maintained stroke geometry instead of thickening or
inventing signs. Every delivered key passes the 100-texel and light-ink
checks in both states. Runtime visibility still requires image review.

## Runtime text

`QuartersRoom` fits a 1024 by 640 text space inside the imported Display AABB,
using the smaller width/height pixel scale. Type grows from 32 to 48 pixels.
Width wrapping retains the 92% margin, and a new test checks physical width
and total font line height for all three playback phases in both states.
The message/fault source and simulation timing are not edited.

## Black terminal diagnosis

Baseline `56a656b` already renders the powered terminal as an unshaded dark
panel. Its exported Display material matches the taller asset:

| Property | Baseline and current |
| --- | --- |
| Base color, linear RGBA | (0.002, 0.018, 0.019, 1) |
| Roughness / metallic | 0.65 / 0 |
| Exported specular factor | 0 |
| Emissive factor | (0.0003, 0.0027, 0.00285) |
| Glass depth | 0.004 m |

Both versions then replace this material in `QuartersRoom._screen()` with
the same opaque, unshaded terminal material: albedo `(0.004, 0.012, 0.018)`,
emission `(0.008, 0.035, 0.05)` at energy `0.4`, metallic `0.02` and specular
`0.5`. Remembered roughness is `0.45`; Present roughness is `0.9`. These
roughness/specular values do not create reflections under unshaded rendering.
There is no separate reflective glass overlay. The unchanged scanline quad
sits 0.3 mm in front of the 4 mm panel, with black lines at alpha 0.14; text
sits 1.7 mm forward. The room's interior box-projected ReflectionProbes are
unchanged, as are the black background, disabled ambient source, exposure and
lights in `Lighting`. They cannot add reflections to this unshaded surface.

No glass brightness, finish, probe, light or global optics change was made.
The larger dark area can make the existing treatment more conspicuous, but
whether that treatment looks appropriate is for parent image review. Numeric
material equality does not establish visible reflection quality.

## Reproduction

Use the installed Blender and Hunyuan virtualenv Python. No guide GLB is
needed to export the tracked saved source. `refit.py` is the recorded
adjustment from the old fitted source and is a no-op on the already adjusted
saved source. `build.py --assemble` retains the original guide-fit envelope
before applying the same deformation, if that old guide is supplied.

```sh
BLENDER=/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender
PYTHON=/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python
mkdir -p tmp/issue129 tmp/verify-stasis-wiring/seat-production tmp/mat/locker/pass5
$BLENDER --background --factory-startup --python-exit-code 1 \
  --python tools/blender/quarters/console/build.py -- \
  --output assets/props/quarters/console.glb
$BLENDER --background --factory-startup --python-exit-code 1 \
  --python tools/blender/quarters/console/build.py -- \
  --output tmp/issue129/console-repeat.glb
$PYTHON tools/blender/quarters/console/verify.py \
  --input assets/props/quarters/console.glb --reexport tmp/issue129/console-repeat.glb
godot --headless --path . -s tools/blender/quarters/console/export_legends.gd
$PYTHON tools/quarters_aging/map_library.py \
  --blend tools/blender/quarters/console/console-working.blend \
  --prop console --resolution 4096
$PYTHON tools/blender/quarters/console/bake_legends.py
$PYTHON tools/blender/quarters/console/test_console.py
godot --headless --editor --path . --import
godot --headless --path . -s tests/run_tests.gd
godot --headless --path . -s harness/run.gd -- scenarios/quarters-demo.json --out tmp/issue129/harness
```

Always run the atlas mapper before the legend bake. The mapper writes both
base finish sets; the legend baker composites antialiased ink over them.
There is one shared rigid `console.glb`, not separate aged geometry. Both
Remembered and Present texture sets are delivered under
`assets/props/quarters/steel/console/`.

The two extra scratch parents above are required by unrelated guarded
helpers described in #133. No helper or test enforcement was changed.
Before any capture, compare the native imported `.md5` file's `source_md5`
with the current GLB MD5; the source `.import` sidecar alone is insufficient.
Verification results and measured room clearances are recorded below after
running the import and room checks. Image judgment belongs to the parent
session; no visual approval is claimed here. Review skipped per Andrew
2026-10-09 (OCR disabled).

## Measured room fit

The imported Remembered and Present states produce the same measurements:

| Actual room measurement | Metres |
| --- | ---: |
| Worktop top / console bottom above floor | 0.700000763 |
| Console top above floor | 1.638887405 |
| Cabinet bank bottom above floor | 1.899999619 |
| Vertical gap from console top to cabinet-bottom datum | 0.261112213 |
| Console-to-worktop contact gap | 0.000000000 |
| Rendered display width along its tilted plane | 0.873999894 |
| Rendered display height along its tilted plane | 0.545440674 |

The existing room fitter retains its depth factor of 0.994394 to include
the front rivet projection inside the 0.55 m desk footprint. Height and
width factors remain 1.0. That retained depth fit accounts for the small
difference between the 0.54625 m source glass height and its physical
length in the room. No furniture or camera moved. The actual worktop is
0.70 m, not the layout's 0.76 m upstand-inclusive desk envelope.

## Capture framing and review status

The unchanged `console` camera projects the active Display vertices to pixels
`(399.83, 15.10)` through `(1025.95, 390.69)` in the 1536 by 864 raw frame.
Those coordinates are identical before and after the upper-border trim.
Fresh imported baseline `56a656b` puts the housing at 157.9838 pixels and
the glass at 191.8835 pixels below the top boundary in this same camera.
The taller geometry introduced the clipping. At `0f26ad0`, the housing,
left rail and top bar reached respectively -8.3947, -6.3190 and -6.0202
pixels. After trimming their surplus upper metal, they start at 3.3367,
5.0741 and 5.2475 pixels. Every console mesh vertex now
has at least a two-pixel margin in both states. This check uses actual vertices,
not projected AABB corners. The complete 0.874 by 0.54625 m display remains.

The existing presentation helper crops 40 pixels from the top to remove the
harness chip, which also removes about 25 pixels from the glass in this close
view. Framing review must use full frames including the chip band. Comparisons
retain that band and put baseline `56a656b` on the left and current on the
right. Remembered and Present are finish states, not before/after versions.
The earlier review images used the same refitted source for both states and
therefore could not establish whether clipping was inherited from `56a656b`.
No camera, room light, environment, simulation sequence or other furniture
has changed.

The supplementary keyboard camera is recorded in
`tools/blender/quarters/console/capture_keys.gd`. Its earlier detail images
passed the parent keyboard review in `tmp/issue129/keys-visual-review.md`.
That review predates the upper-border trim and associated UV repack. The
current build still requires parent image judgment.

## Verification results

The initial independent Python regression failed on the old 0.238 m display
height and absent native-legend metadata. The final asset passes all three
Python checks, including the new top-bar thickness, glass-gap, rail-contact
and cap-closure test. The framing check failed on the clipped geometry before
the trim and now passes for every mesh vertex in both finish states. The
guarded focused lane passes 108 tests; the unchanged full runner passes
1014 tests with zero failures. This adds one framing regression to the
previous 1013/0 result, which included three new console tests. The existing
aging suite passes 89 tests and the fixture-weather suite passes 11 tests.
No existing assertions or guards were weakened. The full Godot run exits
successfully while reporting resource cleanup diagnostics at shutdown.

The independent trimesh verifier passes bounds, +Y-up/+Z-front orientation,
closed geometry, consistent winding, positive volume, zero degenerate faces,
5,112 triangles against 15,000, zero UV overlaps/out-of-range coordinates,
and UV density p95/p05 1.097039 against 1.25. Saved-source GLB repeat exports
are byte-identical. Independent repeats of all seven state atlas images and
mapping metadata are also byte-identical. The final key-top raster uses the
largest planar cap face, not a bevel; all 24 signs have 120 to 223 ink texels.

Both projects completed fresh editor imports. Immediately before each
capture run, all 38 quarters GLBs and the seven console PNGs passed native
`.md5` source-hash checks. The current console source and native record both
have MD5 `00717379118e28c5c940fd1381367746`; the isolated baseline project
has `d0f2e4aee8627f4d5a8b59ad7773cd83`. No source assets were swapped in the
working project to capture the baseline.

New verification logs are under `tmp/issue129-visualfix/`:
`test-console.log`, `test-frame-before.log`, `test-frame-after.log`,
`test-focused.log`, `test-full.log`, `test-aging.log`,
`test-fixtureweather.log`, `verify-export.log`, `atlas-repeat-check.log`,
`room-measurements.json`, `source-measurements.json`, `current-before.json`,
`current-after.json`, `baseline-projection-and-materials.json`,
`baseline-import.log`, `current-import.log`,
`baseline-native-before-capture.log` and `current-native-before-capture.log`.

## Actual before/after capture set

The serialized actual-windowed capture runs both pass the unchanged machine
checks on all 24 beats:

- Before, source `56a656b`: `tmp/issue129-visualfix/captures-baseline/run-1794352179/`.
- After, taller console with trimmed cap: `tmp/issue129-visualfix/captures-current/run-1794352211/`.

An inventory-only subclass of the production harness records each console
mesh's resource, vertex-position hash, bounds, transform and material override
before calling the unchanged parent capture method. It also records the other
instanced room assets and their source hashes. These inventories prove which
native mesh resources were loaded. For all six comparison beats, before/after
camera eyes and ticks match, Display material overrides match in both finish
states, and all other instanced room asset sources/hashes match. No rendering
or simulation behavior was added by the inventory hook.

`tmp/issue129-visualfix/capture-manifest.json` records raw PNG paths/hashes,
reports, inventories, source provenance and JPEG paths. All comparisons retain
the complete raw 1536 by 864 frame, including the 40-pixel protocol band.
They are uniformly scaled for delivery, without cropping or masking. Baseline
is on the left and current is on the right. Under
`tmp/issue129-visualfix/review/`, the individual 1400 by 426 JPEGs are:

- `remembered-console-before-after.jpg`
- `present-console-before-after.jpg`
- `remembered-wide-before-after.jpg`
- `present-wide-before-after.jpg`
- `console-message-before-after.jpg`
- `console-fault-before-after.jpg`

The single 1400 by 639 contact sheet is `all-six-before-after.jpg`.
The `singles/` subdirectory contains full-frame baseline/current JPEGs at
1400 by 788. The capture lanes report particle-shader/texture RID cleanup
diagnostics at shutdown, after successful capture and machine verification.
These scratch outputs are not committed. Parent visual judgment remains pending.
