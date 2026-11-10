# Taller quarters console and native keys (#129)

The accepted fitted console now has a 16:10 display and 24 Naleya key legends.
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
| Console height | 0.690 m | 0.9543222 m |
| Width | 1.100 m | 1.100 m |
| Exported depth including front rivets | 0.55310 m | 0.55310 m |
| Screen backward tilt from vertical | 30.9638 degrees | 30.9638 degrees |
| Triangles | 5,088 | 5,112 (limit 15,000) |
| State atlas size | 3072 square | 4096 square |

`refit.py` deforms the saved head cages rather than generating a replacement.
The glass lower edge remains at exported glTF `(0, 0.454878712, 0.062092286)`.
The bezel sides, upper trim, gasket, glass and upper rivets extend together.
The last 29 mm of housing height transitions inward by 25.6 mm to keep a
closed upper cap within the existing rear depth at the retained tilt.
An independent comparison with the baseline GLB found identical world-space
vertices for all 35 lower parts: lower housing, support, shoe, control panel,
24 keys, three toggles, three sockets and lower housing rivets.

The layout's nominal console top changes from 1.45 to 1.7143222 m. This is
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
| Console top above floor | 1.654322624 |
| Cabinet bank bottom above floor | 1.899999619 |
| Vertical gap from console top to cabinet-bottom datum | 0.245676994 |
| Console-to-worktop contact gap | 0.000000000 |
| Rendered display width along its tilted plane | 0.873999894 |
| Rendered display height along its tilted plane | 0.545440912 |

The existing room fitter retains its depth factor of 0.994394 to include
the front rivet projection inside the 0.55 m desk footprint. Height and
width factors remain 1.0. That retained depth fit accounts for the small
difference between the 0.54625 m source glass height and its physical
length in the room. No furniture or camera moved. The actual worktop is
0.70 m, not the layout's 0.76 m upstand-inclusive desk envelope.

## Capture framing and review status

The unchanged `console` camera projects the active Display AABB to pixels
`(399.60, 14.70)` through `(1026.46, 390.98)` in the 1536 by 864 raw frame.
The glass is inside that frame. The taller housing reaches about 16 pixels
above the raw frame; the camera has deliberately not been moved. The existing
presentation helper crops 40 pixels from the top to remove the harness chip,
which also removes about 25 pixels from the glass in this close view. Use the
`*-fullframe.jpg` console/playback copies for screen-height review, and the
unchanged wide views for the full housing in room context. This framing limit
is retained for parent art review rather than changing the camera or reducing
the requested 16:10 glass.

The supplementary keyboard camera is recorded in
`tools/blender/quarters/console/capture_keys.gd`. It uses the actual ship scene,
room lights and state materials. Its initial setup omitted the D16 aft hatch;
that setup error is fixed. The final run has no script errors, but Godot still
reports particle-shader/texture RID cleanup warnings on exit after saving the
two detail images. The main 24-beat quarters harness reports machine PASS.
No visual approval is claimed for either capture lane.

## Verification results

The new independent Python regression initially failed on the old 0.238 m
display height and absent native-legend metadata. The delivered asset passes
both tests. The guarded focused lane passes 107 tests; the unchanged full
runner passes 1013 tests with zero failures (baseline 1010, plus three new
console test methods). The existing aging suite passes 89 tests and the
fixture-weather suite passes 11 tests. No existing assertions or guards were
weakened. The full Godot run exits successfully while reporting resource
cleanup diagnostics at shutdown.

The independent trimesh verifier passes bounds, +Y-up/+Z-front orientation,
closed geometry, consistent winding, positive volume, zero degenerate faces,
5,112 triangles against 15,000, zero UV overlaps/out-of-range coordinates,
and UV density p95/p05 1.097056 against 1.25. Saved-source GLB repeat exports
are byte-identical. Independent repeats of all seven state atlas images and
mapping metadata are also byte-identical. The final key-top raster uses the
largest planar cap face, not a bevel; all 24 signs have 135 to 259 ink texels.

The editor import and final hash check pass. The imported console native
`.md5` records source MD5 `913fb86db733e5cbb306c7c275713869`, matching the
changed GLB before captures. All seven changed PNG source hashes also match
their native imported hash records.

Verification logs are under `tmp/issue129/`: `test-before.log`,
`test-console.log`, `verify-export.log`, `repeat-bake-check.log`,
`test-focused.log`, `test-full.log`, `test-aging.log`,
`test-fixtureweather.log`, `room-measurements.json`, `import-final.log`,
`import-hashes-before-captures.log`, `harness.log` and
`capture-keys-final.log`.

Actual windowed raw captures are in
`tmp/issue129/harness/run-1794340030/beats/` (24 beats, machine PASS).
Standard 40-pixel-cropped presentation PNGs are in
`tmp/issue129/presentation/`. The two actual-room key detail PNGs are
`tmp/issue129/details/remembered-keys.png` and `present-keys.png`.
JPEG review copies are in `tmp/issue129/review/`; use
`remembered-console-fullframe.jpg`, `present-console-fullframe.jpg`,
`console-message-fullframe.jpg`, `console-fault-fullframe.jpg`,
`remembered-wide-fullframe.jpg`, `present-wide-fullframe.jpg`,
`remembered-keys.jpg` and `present-keys.jpg` for console review.
These scratch outputs are not committed. Parent visual judgment remains pending.
