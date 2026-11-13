# Taller quarters console and native keys (#129)

The fitted console has the accepted 16:10 display and a separate power-room
keyboard with 29 muted Naleya legends.
The saved source is `tools/blender/quarters/console/console-working.blend`.
This changes the console only. Room furniture, cameras, lighting, clothes,
interaction dispatch, the idle underscore, message wording and the
60/180/60-tick corruption/message/fault sequence are unchanged.

The latest cap/print correction and numeric layout check are recorded in
[Matched cap pigment and print weight](#matched-cap-pigment-and-print-weight-129).
That section supersedes the earlier cap-colour and legend-size notes below.

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
| Console triangles | 5,088 | 1,488 (limit 15,000), plus separate 28,998 keyboard |
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
The head-only adjustment originally retained all 35 lower parts, including
its old controls. The keyboard correction removes those independent controls.
All 13 remaining mesh parts retain their exact world transforms and point
sets relative to `d3b0b24`; the separate keyboard is seated above the unchanged
ControlPanel. The saved deck, lower housing and support have no new geometry.

The layout's nominal console top changes from 1.45 to 1.6988873 m. This is
its existing 0.76 m datum plus the new source height. It prevents the runtime
fitter from compressing the new screen back to the old height. It does not
move the desk or console base. The existing fitter still seats the console
on the actual worktop below the rear upstand. Collision uses the same X/Z
footprint and the taller head envelope. Existing desk-contact, desk-item,
walkway, reach and shared-collider tests remain in force.

## Power-room keyboard layout correction

Andrew accepted the taller display and requested the power-room keyboard
layout on PR #134. The quarters copy reuses
`assets/props/terminal/keyboard.glb`. Its source is
`art-source/terminal/generated/console2/assembly3/console-with-keyboard.blend`;
`kb3/prepare.py`, `atlas.py` and `finish.py` under the same `console2`
directory record its generated-mesh fitting and finish. The power-room
pipeline and measurements are in `art-source/terminal/PIPELINE.md` and
`generated/console2/final/README.md`. Git commit `8e74f7a` introduced the game
asset. Those source files and every power-room file remain unchanged.

`keyboard.py --refit` removes the old 24 independent caps, their grouping
node, all three tall toggles and their sockets from the saved console. The
existing ControlPanel is a closed solid, so there are no holes to patch.
Rebaking its finish removes the obsolete inlaid legends. No replacement deck
geometry is added. The toggles are omitted because their isolated vertical
bank would retain the layout Andrew rejected; this uses the same complete
keyboard case and right-side key groups as the power room instead.

The reused keyboard keeps every indexed triangle position and UV corner
exactly. Blender splits some render vertices at normal seams during
round-trip, but no physical surface or UV triangle changes. It also retains
the power-room placement's uniform scale, 0.6600278615951538. No additional
scaling is needed. Its physical width, depth and thickness before the support
plane correction are 528.0223, 162.0840 and 36.3015 mm. The corrected seating
pose has a 527.8934 by 162.0387 mm deck-plane footprint. The slight difference
comes from leveling the source's tilted underside, as the power room does.

The quarters source is `keyboard-working.blend`; its placement is recorded
in `keyboard-placement.json`. Its separate export is
`assets/props/quarters/console_keyboard.glb`. `QuartersConsoleKeyboard`
instances that model with the same fitted transform and seating lift as the
console. It duplicates the keyboard's imported PBR material and assigns its
quarters state maps without adding this accessory to the fixed Batch 1
material-review inventory. The console remains 1,488
triangles against its unchanged 15,000 limit; the separate keyboard retains
28,998 triangles against a 30,000-triangle regression cap.

| Exported seating measurement | Millimetres |
| --- | ---: |
| Front deck-edge clearance | 10.0000 |
| Rear deck-edge clearance | 51.6586 |
| Side deck-edge clearance, each side | 246.0533 |
| Minimum normal gap above actual panel top | 0.5000 |
| Keyboard-vertex minimum distance to Display surface | 50.4960 |
| Keyboard-vertex minimum distance to lower bezel | 26.2940 |
| Keyboard-vertex minimum distance to housing | 63.1311 |

Deck-local glTF bounds are `(-0.263946674, 0.009499993, -0.060190081)` to
`(0.263946681, 0.043611988, 0.101848650)` metres. The deck-local bounding
centre is `(0, 0.026555991, 0.020829285)` metres. Positive Z faces the
operator. All keyboard triangles are tested against all retained console
parts with triangle/triangle SAT: zero crossings. Nine first-hit underside
rays measure support gaps of 0.5619 to 0.6496 mm. The source pipeline's
25-ray underside plane fit is reused for this correction. The 0.5 mm gap is below
one millimetre, rather than a visibly floating placement. This is measured
geometry; visible seating still needs the parent's image review.

All 13 retained console mesh parts have exactly the same local point sets
and world transforms as `d3b0b24`, including the full taller Display, all
bezel pieces, housing, lower deck, support and closed ControlPanel. No room,
camera, light, desk, runtime text or playback timing changes are included.
The old dimensions and capture notes below describe the earlier taller-head
work; the keyboard correction supersedes their old control counts.

## Native legends and both finish states

`export_legends.gd` calls production `Naleya.layout()` and
`Naleya.expand_strokes()`. `legends.json` records 29 inputs and their returned
filled quads, assigned to the retained keyboard's numbered design caps. The
first eight inputs are octal digits `0` through `7`; the remainder are
`a e i o u pa pe pi po pu ta te ti to tu ka ke ki ko ku ma`.
The regression compares every quad with production expansion.

`bake_legends.py` uses the original keyboard report's measured cap-interior
UV rectangles. It removes the source's earlier marks, preserves glyph
aspect, and centres the production quads at 50% of each cap interior's
height, with a 90% width ceiling for narrow caps. Positive glyph Y points
toward the display. Rasterized print stays below 52% of cap height; the
narrowest cap is width-limited to 44.8%. Ink uses sRGB
`(112,112,102)` at maximum opacity 0.60 in Remembered and 0.48 in Present.
It changes albedo only, with no emission, engraving or raised/inlaid normals.
Four-times supersampling preserves crisp antialiased edges. Every sign still
has at least 100 half-coverage mask texels. These are asset legends, not a
keyboard input feature.

Both 2048-square state sets live in
`assets/props/quarters/steel/console_keyboard/`. `mapping.json` records the
sealed-storage parameters, glyph bounds, ink probes and opacities. Remembered
retains the source keyboard's case/rubber finish and normal/ORM maps apart
from its changed printed legends. Present has bounded pigment fade, a fine
dust veil and higher roughness without changing its mesh. The power-room
asset and textures are read-only.

### Keyboard finish review correction

The `a99c7ea` bake resampled the hairbrush's `Rubber_aged.png` over every
non-case texel and `steel_library/top-00.png` over the case. The hairbrush
baker (`photo_frame/texture_bake.py`) deliberately builds a 38-seed Voronoi
fracture network, selects cracks with a 1.15-pixel distance difference and
multiplies crack colour by 0.18. Reusing that image made cracks cross the
keys and their membrane. Its relief map was not copied; these fractures
were in albedo. The case image spans RGB `(0,8,11)` to `(255,248,221)` and
introduced broad bright mottling and chipped borders onto the small olive
case, including its exposed deck patch. Neither texture suits this copy's
1000 years of dry, sealed, sterile storage.

The power-room source already has restrained baked wear. Its `kb3/atlas.py`
sets olive case `(84,90,58)`, charcoal caps `(42,44,46)` and recessed membrane
`(13,15,15)`, adds curvature/AO-selected case chips and sparse oxide, then
composites worn printed marks. `PowerRoom._build_console()` instances that
GLB with its imported material; it does not apply an additional age shader,
weather texture or room-state finish to the keyboard. The power-room capture
is supplied as a reference, without an implementer visual judgment.

The `d203221` correction changed `console/bake_legends.py` and the quarters
keyboard atlases without changing shared aging defaults or other props.
That version multiplied Present's source-colour variation by 0.25 and clamped
it to ±2.5 sRGB bytes around the source pipeline's three material pigments.
The housing correction below supersedes those case-specific values.
In that version, case fade mixed 4% toward `(100,103,78)`; caps and membrane
mixed 8% toward `(65,65,63)` and
`(25,27,25)`. Dust uses `(110,106,96)` at 8% opacity with ±1% fine object-space
variation. Crack and peeling contributions are zero. The original normal
map is retained, rather than introducing fracture relief. Roughness floors
are 224/255 for the case and 240/255 for polymer; metallic is capped at
24/255. The existing shader additionally floors upper aged surfaces at 0.94
roughness. Slight embrittlement is represented by dulled rough surfaces,
without broken geometry.

The earlier legend fit was 60% in both atlas dimensions with ink
`(150,146,128)` at 0.45/0.30 opacity. Its broad pale marks dominated the caps.
The new height-led fit and darker ink reduce that contrast, with Present's
lower opacity retaining further wear. The existing 100-texel legibility
minimum and all geometry, UV, seating and framing checks remain unchanged.

The previously listed Present full frame exists at
`tmp/wt-129/tmp/issue129-keyboard/review/present-console-fullframe.jpg`, relative
to the parent checkout. The failed review lookup omitted `tmp/wt-129` and
looked under the parent checkout's `tmp/issue129-keyboard/review/` instead.
The new delivery script checks that every reported absolute JPEG path exists.

The keyboard's existing projected cap UVs have 34 small overlapping triangle
pairs, maximum UV area 0.000000680057, and p95/p05 density ratio 2.23749.
These values match the power-room source exactly. They do not pass the
rigid-console uniform-density gate; that gate remains unchanged and passes
for the console, with zero overlaps and ratio 1.09408. No keyboard UVs were
repacked to conceal inherited source defects. The new regression requires
all keyboard UV triangle corners and both source/copy UV reports to agree.

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

## Earlier taller-head reproduction (keyboard additions below)

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

## Earlier taller-head verification results

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

## Keyboard correction reproduction and verification

```sh
mkdir -p tmp/issue129-keyboard tmp/verify-stasis-wiring/seat-production tmp/mat/locker/pass5
$BLENDER --background --factory-startup --python-exit-code 1 \
  --python tools/blender/quarters/console/keyboard.py -- --refit
$BLENDER --background --factory-startup --python-exit-code 1 \
  --python tools/blender/quarters/console/build.py -- --output assets/props/quarters/console.glb
$BLENDER --background --factory-startup --python-exit-code 1 \
  --python tools/blender/quarters/console/keyboard.py -- --output tmp/issue129-keyboard/keyboard-repeat.glb
godot --headless --path . -s tools/blender/quarters/console/export_legends.gd
$PYTHON tools/quarters_aging/map_library.py \
  --blend tools/blender/quarters/console/console-working.blend --prop console --resolution 4096
$PYTHON tools/blender/quarters/console/bake_legends.py
$PYTHON tools/blender/quarters/console/test_console.py
godot --headless --editor --path . --import
godot --headless --path . -s tests/run_tests.gd
```

Normal exports read the two tracked saved sources and are byte-identical on
repeat. `--refit` is the recorded source adjustment, not a required step for
each export. `verify_keyboard.py --baseline <isolated-d3b0b24-project>
--report tmp/issue129-keyboard/measurements.json` checks exact retained
geometry, seating, SAT contacts and source/copy UV equality outside Blender.
The original `verify.py` still checks the console's unchanged 15,000-triangle,
closure, uniform-UV and display contracts.

### Actual room and capture results

Both runtime finish states retain the existing console depth fit of
0.994394, which seats its 0.55310 m rivet-inclusive source inside the 0.55 m
desk footprint. The keyboard inherits that same existing fit so it stays
seated on the tilted panel. This produces an actual room deck-plane keyboard
footprint of 527.893 by 161.190 mm, height above its projected bounding base
34.099 mm, with deck-plane centre `(0, 26.546, 20.627)` mm. No additional
keyboard-only scale is applied. The source-installed dimensions above remain
the comparison with the power-room placement. Runtime measurements are in
`tmp/issue129-keyboard/room-measurements.json`.

The actual windowed production quarters-demo routes pass all 24 beats for
both the isolated `d3b0b24` project and this keyboard correction. The unchanged
power-room route also passes. The comparison script requires matching camera
eyes and ticks, retains the complete 1536 by 864 console frames including the
protocol band, and delivers 1400-pixel JPEGs with before on the left and after
on the right. Supplemental detail frames use the existing `capture_keys.gd`
camera. No image has been judged by the implementer.

Fresh editor imports precede captures. Native `.md5` source hashes match
all 387 checked resources, including quarters GLBs/PNGs and the source keyboard;
the isolated baseline checks its corresponding resources. The baseline's
first scratch captures lacked extracted photo-frame image dependencies, even
though its GLB native source hashes matched. Those runs are retained under
`captures-baseline-missing-images`, excluded from comparisons, and replaced
after restoring identical extracted images and running another editor import.
The final baseline and current capture logs contain no script errors.

JPEGs for parent review are in `tmp/issue129-keyboard/review/`:
`remembered-console-fullframe.jpg`, `present-console-fullframe.jpg`,
`remembered-keyboard-detail.jpg`, `present-keyboard-detail.jpg`,
`power-room-console-inactive.jpg`, `remembered-console-before-after.jpg` and
`present-console-before-after.jpg`. The raw production runs, native-hash logs,
geometry report and test logs remain under `tmp/issue129-keyboard/`.

The console Python tests pass 3/3; the guarded focused quarters/Naleya lane
passes 109/109 and the guarded full Godot runner passes 1015/1015. The
existing aging suite passes 89 tests and fixture-weather passes 11. Exported
console and keyboard repeats are byte-identical to their tracked sources.
The final seating control uses nine first-hit underside rays, all within
0.5619 to 0.6496 mm of the deck, with zero triangle crossings against every
retained console part. Both exports have the required +Y-up/+Z-front axes.
Godot reports resource cleanup diagnostics at shutdown after successful runs.
Visual review remains pending with the parent. Review skipped per Andrew
2026-10-09 (OCR disabled).

## Sealed-storage correction captures and verification

The material correction changes seven tracked files: the local baker, its
Python regressions, this document, the keyboard's Remembered/Present albedo
images, its Present ORM image and its mapping metadata. Geometry, saved
Blender sources, normals, UVs, console deck finish, room lights and cameras
are unchanged. The source power-room files and shared aging library remain
unchanged.

The final glyph raster occupies 43.1–45.1% of cap-interior height and has
102–1764 half-coverage texels per sign. All five console Python tests pass,
including the existing 100-texel minimum, placement and geometry contracts.
The new tests check print bounds, alignment, actual atlas probe contrast,
bounded sealed-storage variation and deterministic output. The focused
guarded quarters/Naleya lane passes 109 tests; the full guarded Godot suite
passes 1015 with zero failures and exit 0. Aging passes 89 and fixture
weather passes 11. No existing checks were weakened. The full result is in
`tmp/issue129-keyboard-fix/test-full-final.log`. An earlier wrapper lost its
log after being edited while Bash was running, so the full suite was run
again from an unchanged standalone command. Shutdown resource-cleanup
diagnostics remain in the successful run.

Console and keyboard exports from their tracked saved Blender sources are
byte-identical to the delivered GLBs. All seven keyboard atlas PNGs and
mapping metadata are byte-identical on repeat. Both isolated baseline and
current projects completed editor imports. Immediately before each capture,
all 387 checked resources matched the native imported `.md5` `source_md5`,
not just the source `.import` sidecar. The baseline's first import exposed
missing scratch-project locker dependencies; copying those unchanged runtime
resources and importing again resolved it before captures.

The actual windowed production quarters-demo passes all 24 beats for both
`a99c7ea` and the corrected finish. The unchanged power-room route also
passes. Detail captures use the same `capture_keys.gd` camera and unchanged
room lighting. `ps` checks serialize the windowed runs with other sessions;
no other session was interrupted. Baseline GLBs and affected textures were
compared byte-for-byte with `a99c7ea` before delivering the comparisons.

Logs and raw runs are under `tmp/issue129-keyboard-fix/`. The delivery script
checks every reported absolute path for existence, JPEG decoding and a
maximum dimension of 1400 pixels. It preserves complete frames, including
the protocol band, with no crop or mask. Comparison sheets put `a99c7ea` on
the left and the corrected finish on the right. The implementer did not
judge these images. Review skipped per Andrew 2026-10-09 (OCR disabled).

All JPEGs below exist under
`/Volumes/XS1000/acoliver/projects/gone/branch-2/tmp/wt-129/tmp/issue129-keyboard-fix/review/`:

- `remembered-console-fullframe.jpg`
- `present-console-fullframe.jpg`
- `remembered-keyboard-detail.jpg`
- `present-keyboard-detail.jpg`
- `power-room-console-inactive.jpg`
- `remembered-console-before-after.jpg`
- `present-console-before-after.jpg`
- `remembered-keyboard-detail-before-after.jpg`
- `present-keyboard-detail-before-after.jpg`
- `baseline-remembered-console-fullframe.jpg`
- `baseline-present-console-fullframe.jpg`
- `baseline-remembered-keyboard-detail.jpg`
- `baseline-present-keyboard-detail.jpg`


## Preserve the power-room housing finish

The remaining review finding identifies a nearly uniform olive Present
housing. The keys, legends, layout and seating passed review. In `d203221`,
`sealed_storage()` replaced the housing albedo with `(84,90,58)` plus source
variation clamped to ±2.5 sRGB bytes. Its 4% fade and 8% dust then covered
the source variation. The bake also floored housing roughness at 224/255,
capped metallic at 24/255, and classified housing by colour. Those operations
removed the source's exposed metal and oxide response as well as its colour
detail. The Remembered shader added another paint-grain treatment through
the region mask.

The power-room `kb3/atlas.py` already describes a worn, as-found keyboard:
AO/curvature-selected chips, sparse oxide, grime and worn cap print. PowerRoom
uses that imported material without an additional aging pass. Present now
copies the source housing albedo, normal and ORM texels exactly, including
chips, oxide, dark edges and UV padding. Source ORM metallic bytes identify
the material: 0 for caps/membrane, 45 for intact housing paint, 198 for chips
and 89 for oxide. This avoids losing dark metal through an RGB threshold.

Remembered derives its cleaner housing from that same authored atlas. At
chip/oxide texels only, albedo, roughness and metallic mix 25% source wear
with 75% nearest intact housing paint from the source atlas. This reduces
both wear masks to one quarter of their original strength while retaining
the local paint variation. Every intact housing texel, all AO and the normal
map remain unchanged. The source has 1,446 chip and 1,532 oxide texels,
including padding; all 2,978 receive this reduction. No new noise or flat
pigment is introduced. Both states leave housing region RGB at zero so the
unchanged library shader cannot apply paint grain or a roughness override.

The `d203221` cap/membrane finish and legends are retained: source variation
gain 0.25, limit ±2.5 sRGB bytes, 8% charcoal/rubber fade, dust `(110,106,96)`
at 8% ±1%, and no cracks or peeling. Its 8,561 olive-tinted polymer texels
retain the prior `(84,90,58)` pigment and 4% fade toward `(100,103,78)`;
their roughness floor remains 224/255, versus 240/255 for other polymer.
These colour-specific rules apply only to polymer; housing bypasses them.
Every cap/membrane albedo, normal, ORM and shader-region pixel was compared
with `d203221` and matches exactly in both states. All legend records match
as well. Ink remains `(112,112,102)` at 0.38/0.30 opacity, height fraction
0.435 and width ceiling 0.90. Geometry, UVs, saved Blender sources, placement,
room lighting, shared aging defaults and every power-room file are unchanged.


### Housing correction verification

The console Python suite passes 8 tests, including exact Present housing
texture equality, the 25% Remembered wear-mask calculation, unchanged AO,
zero housing shader overrides and retention of the earlier olive-polymer
finish. The focused guarded quarters/Naleya suite passes 109 tests; the full
guarded Godot suite passes 1,015 with zero failures and exit 0. Aging passes
89 tests and fixture weather passes 11. Existing geometry, seating, glyph
legibility and runner enforcement remain in place. The full runner reports
resource-cleanup diagnostics after its successful result.

All seven final atlas PNGs and mapping metadata are byte-identical on repeat.
The baseline's 662 copied tracked runtime files match `d203221` Git blobs,
excluding generated UID/import metadata. Its interrupted copy omitted locker
maps, hinge geometry, wardrobe shader/layout and two JSON plans. Those
unchanged dependencies were restored before the final captures. The first
baseline run lacked the room plan and is excluded from the comparisons;
its error log is retained separately.


Both final projects completed fresh editor imports without script errors.
Immediately before every console, detail and reference capture, all 395
checked source resources matched their native imported `.md5` `source_md5`.
The actual windowed quarters-demo passes all 24 beats for both `d203221` and
the correction. The unchanged power-room route passes its 11-beat machine
checks. Detail captures use the same recorded camera in both versions.
Before/after console reports have matching camera eyes and simulation ticks.
All capture jobs were serialized after checking other Blender/Godot jobs;
no other worker was interrupted.

The 13 JPEGs under `tmp/issue129-keyboard-fix2/review/` include both finish
states, full frames, keyboard details, four before/after sheets against
`d203221` and the power-room reference. They retain complete frames without
cropping or masking, with baseline on the left and correction on the right.
Every JPEG decodes and has a maximum dimension of 1400 pixels; the reference
retains its native 480 by 270 frame. Exact absolute paths are recorded in
`tmp/issue129-keyboard-fix2/jpeg-paths.json`. Logs remain in that same scratch
root. Isolated baseline/cache copies, repeat atlases and raw capture PNGs
were removed after delivery. No image judgment or OCR was performed.


## Readable legends and matched keyboard reference

The follow-up to `09a0e47` increases the maximum ink opacity from 0.38 to
0.60 in Remembered and from 0.30 to 0.48 in Present. Ink stays sRGB
`(112,112,102)`. Target glyph height increases from 0.435 to 0.50 of the
cap-interior height, retaining the 0.90 width ceiling, original aspect ratio,
centering and four-times supersampling. Measured half-coverage print height
is 50.0–51.0% on 28 caps. Cap 28 remains width-limited at 44.8%; enlarging it
further would cross the retained width ceiling. No print exceeds 52% height.
The regression checks each sign against its aspect-constrained expected
height and exact composited ink colour, alongside the existing 100-texel
minimum and alignment checks.

### Dark cap marks come from the source atlas

The inspection used texture values and source code, without judging images.
Checking only the legend-interior rectangles missed the reported marks:
those rectangles contain no Present albedo channel below 46. The complete
projected cap-top UV triangles contain 1,248 dark texels with mean Present
albedo below 30. Every one already has mean albedo below 25 in
`assets/props/terminal/keyboard_keyboard_albedo.png`, with zero metallic in
the source ORM. The original `kb3/atlas.py` assigns charcoal cap and darker
membrane pigments using its height/segmentation masks, then applies baked
AO/coarse grime. `prepare.py` reserves upper-atlas UVs above 0.60 for the
projected cap-top triangles, separate from the lower Smart UV islands.
That allocation identifies all 532,611 cap-top texels independently of RGB.
The dark source material patches lie outside the rectangles cleared for
replacement legends. The quarters bake preserves their positions while
applying the existing sealed-storage pigment mapping.

For example, source pixel `(165,287)` is RGB `(13,15,14)` and Present is
`(22,23,22)`; `(1424,456)` changes from `(10,12,10)` to `(20,22,20)`.
The sealed-storage pigment mapping generally brightens those source patches;
a few near its membrane threshold change by less than one mean sRGB byte
in the darker direction. They remain unchanged here, as requested for
marks inherited from the power-room source. The new regression requires
all 1,248 dark cap-top texels to originate in the source's dark, nonmetallic
texels. It also checks unchanged source normal and AO maps. The quarters
library shader does not sample ORM red as AO, so those AO values alone do
not explain its rendered marks.

Only printed albedo inside cap-interior rectangles changes from `09a0e47`:
44,492 Remembered texels and 46,752 Present texels. All housing texels,
cap-aging parameters, normals, ORM, region masks, geometry, UVs, lighting,
production cameras and power-room resources remain unchanged.

### Like-for-like capture method

Scratch scripts under `tmp/issue129-keyboard-fix3/` preserve the production
capture scripts. `capture_keys.gd` uses the existing quarters detail pose,
55-degree horizontal FOV, 1536 by 864 resolution and 4x MSAA. It records
the camera transform relative to the keyboard mesh's rigid, orthonormalized
world frame, so the comparison preserves metric distance and orientation
without carrying the quarters fitter's slight depth scaling into the camera.
The relative eye is approximately `(-0.004743,0.785338,0.620716)` metres.

`capture_power_keys.gd` subclasses the production harness app. At the
existing power-room route's `console-inactive` beat, it pauses simulation
advancement for a supplementary capture of `ConsoleStation1/KeyboardModel`.
It applies the recorded relative camera transform to that keyboard's own
rigid frame, with the same FOV, resolution and MSAA. It then restores the
normal viewport and camera before the unchanged beat capture. No light,
material, room-state or production camera is altered. The route supplies
the normal lighting state rather than a new studio setup.


### Follow-up verification and delivery

Console Python passes 9 tests, focused guarded quarters/Naleya passes 109,
and the full guarded Godot suite passes 1,015 with zero failures and exit 0.
The existing aging suite passes 89 and fixture weather passes 11. The new
legend requirement failed on the old 0.38/0.30 opacity before the bake.
The revised size regression checks the requested 0.50 target while keeping
the narrow-cap width limit; the ink probe now requires the exact requested
blend instead of the earlier contrast ceiling. No runner, geometry,
seating, UV, 100-texel minimum or shared aging check was weakened.
All seven keyboard atlas PNGs and mapping JSON are byte-identical on repeat.

Fresh editor imports preceded baseline and current captures. Immediately
before every route and detail capture, all 395 checked source resources
matched the native imported `.md5` `source_md5`. Baseline assets were still
byte-identical to `09a0e47` when captured, before rebaking in the same
worktree. Both actual windowed quarters-demo runs pass all 24 beats, with
matching console camera eyes/ticks and identical detail-camera records.
The power-room route passes its 11-beat machine checks. Its supplementary
capture is at tick 3055, console inactive, power off, red level 1.0 and white
level 0.0. The matched relative eye error is 0.0000005364 m; the full relative
transform passes the capture assertion. Jobs were serialized using `ps`,
including waiting for the other worker's `issue130-v3/ingame4/route.py`
Blender job without interrupting it. Godot reports resource-cleanup
diagnostics at shutdown after successful checks and captures.

All 15 delivered JPEGs decode, retain the complete frames and have maximum
dimension 1400 pixels. Exact absolute paths are in
`tmp/issue129-keyboard-fix3/jpeg-paths.json`. The review directory is
`/Volumes/XS1000/acoliver/projects/gone/branch-2/tmp/wt-129/tmp/issue129-keyboard-fix3/review/`.
It includes `power-room-keyboard-detail.jpg`, both quarters states as
`present-keyboard-detail.jpg` and `remembered-keyboard-detail.jpg`, and
`power-room-quarters-keyboard-like-for-like.jpg`, ordered power room,
quarters Present, quarters Remembered. Four before/after sheets use
`09a0e47` on the left and this follow-up on the right:
`present-console-before-after.jpg`, `remembered-console-before-after.jpg`,
`present-keyboard-detail-before-after.jpg` and
`remembered-keyboard-detail-before-after.jpg`. The remaining JPEGs are the
individual baseline/current frames and the ordinary power-room route view.
Logs and capture scripts remain under `tmp/issue129-keyboard-fix3/`.
Raw PNGs and duplicate atlas scratch copies were removed after JPEG delivery.
No image judgment or OCR was performed.


## Matched cap pigment and print weight (#129)

### Numeric layout diagnosis against 58a554b

The layout finding is not reproduced by the game-scene geometry. The
measurement builds both real room instances and identifies all 29 cap
interiors using the source report's UV rectangles. It averages unique
key-top vertices in each rectangle in the keyboard mesh's own local frame,
so Blender's additional split render vertices cannot bias the comparison.
The largest centroid difference is 0.0000000679802 m, or 0.000068 mm.
The full indexed triangle positions and UV corners also remain exactly equal
to the power-room source. There is no substituted main block or arrow cluster.

| Scene-instance measurement | Power room | Quarters |
| --- | ---: | ---: |
| World transform determinant | +0.287532419 | +0.285920203 |
| Keyboard yaw relative to console, degrees | +0.00575539 | +0.00000003 |
| Keyboard pitch relative to console, degrees | 26.107958 | 14.369284 |
| Operator eye in mesh-local Z, m | +0.6267681 | +0.9454117 |
| Display centre in mesh-local Z, m | -0.4653358 | -0.4941406 |

The power-room eye is recorded from the real powered-route player camera;
the quarters eye is the existing quarters detail-camera eye.

Neither instance is mirrored or rotated 180 degrees. Both present the
long-row cap 20 on the operator's side: its centroid is approximately
`(-0.1701944, 0.0511639, +0.0728154)` m. The four-key cluster remains at
positive X, with cap centroids spanning X `+0.297529` to `+0.341527` m.
Both consoles' horizontal forward axes point approximately along world +X.
Their different deck slopes explain the pitch difference. The quarters
fitter's existing 0.994394 depth factor explains the small determinant/scale
difference; neither changes key order. With the matched camera applied to
both rigid keyboard frames, the largest projected cap-centroid displacement
is 0.197232 pixels in the 1536-pixel-wide raw frame.

The fix4 power and quarters camera records already use the same rigid
keyboard-relative pose: eye `(-0.004743, 0.785338, +0.620716)` m, horizontal
FOV 55 degrees, 1536 by 864 and 4x MSAA. Both cameras face the operator edge.
The neutral diagnostic removes each keyboard's room transform and reuses
that same pose and one white directional light. Thus a different camera side
does not explain the finding either. The compared printed symbols differ:
the power-room reference has its original script/icons, while the quarters
copy has complete production Naleya signs. The numerical checks establish
identical physical layout without claiming what caused the reviewer's
perception. No geometry, placement, camera or light was changed to address it.
New matched captures accompany the finish correction.

The unchanged placement passes an independent triangle contact check with
zero crossings against all retained console parts. It retains the 10 mm
front margin, equal 246.053 mm side margins, 50.496 mm display clearance and
nine underside support gaps between 0.5619 and 0.6496 mm.

### Atlas measurements and chosen finish

All colours below are 8-bit sRGB, before rendering. Reported cap triples
are medians of the 29 per-cap measurements; print percentiles pool the
selected printed texels. The source pipeline `kb3/atlas.py` authors cap pigment `(42,44,46)`; its recorded final unprinted
key median is `(41,43,45)`. Its own ink is `(150,146,128)` at maximum opacity
0.45. Source printed texels have median `(89,88,81)` and 95th percentile
`(91,90,83)` inside the measured cap interiors.

The earlier quarters bake replaced the whole cap interior with its border
median. That border includes dark bevel/membrane shading, giving Remembered
`(28,30,32)` rather than the unprinted cap median. The old Present cap median
was `(47,48,49)`, with warm dust `(110,106,96)` and fade `(65,65,63)`.
Its old ink `(112,112,102)` produced print p95 `(84,84,78)` in Remembered and
`(79,80,75)` in Present. These are measured atlas differences.

The new bake excludes source print above mean sRGB 65 and uses the median
remaining cap surface separately for every interior. The cap pigment's
source upper bound is below that threshold; printed cores reach about 91.
Remembered now has median `(41,43,45)`, matching the source. Present uses
neutral light-grey dust `(110,110,110)` at the existing 8% mix with ±1% fine
variation and a neutral-preserving fade target `(65,67,69)` at 8%. Its cap
median is `(49,51,53)`. Olive polymer retains its earlier dust treatment;
housing albedo, normals, ORM and shader region masks are unchanged in both
states. No power-room file or shared aging default changes.

Both quarters states now use the source ink `(150,146,128)` at 0.45 opacity.
Their actual print p95 is `(91,90,83)` in Remembered and `(95,94,87)` in
Present, whose cap underneath is lighter from dust. No emission or raised
geometry is added.

### Source PBR material

Matching the atlases exposed a separate material mismatch. The quarters
library shader hard-codes specular 0.32; the imported source keyboard uses
0.5. Its StandardMaterial3D also retains the source normal/AO sampling.
With the corrected cap atlas but the library shader, neutral Remembered cap
means were `(42.32,44.02,45.39)`, against reference `(49.36,50.64,51.88)`.
A controlled diagnostic changing only the duplicate's material to the
imported PBR response brought Remembered to `(49.32,50.78,51.96)`.
The cap pigments and lights were unchanged between these measurements.

`QuartersConsoleKeyboard` now duplicates its imported StandardMaterial3D
and assigns only the quarters albedo, normal and packed ORM state maps.
The regression compares its specular, scalar multipliers, ORM channels,
normal/AO settings and texture filter with the real power-room import.
It failed on the library ShaderMaterial before implementation. Both finish
states still share the same mesh and seated transform and have distinct
2048-square maps. Present's polymer roughness floor is already encoded as
240/255 in its ORM atlas. No shared shader or aging default is edited.

### Print dimensions

The source print recipe uses a 15% inset on each side and a stroke width of
`max(2, round(0.055 * min(cap_width, cap_height)))` atlas pixels. Its actual
main-block cap 1 through 10 print height has median 64.0817% of the interior
height; glyph aspect accounts for the range up to about 70%. Closing the
small worn holes and measuring distance-transform ridges gives median
stroke width 5.42636% of the shorter cap dimension, typically 7 pixels on
these 119 to 130-pixel-high caps. Icons and short vowel marks have different
aspect ratios and are recorded per cap in the scratch measurement JSON.

The old quarters main-block print was about 50% high with 3.87597% stroke
width. The corrected Naleya print targets the source's 70% height envelope
and uses exactly its 5.5% stroke rule, retaining the 90% width ceiling.
It reserves the stroke width before fitting glyph centre lines, then adjusts
only the rasterized segment weight. Production Naleya quads and their
29 input assignments stay unchanged. Four-times supersampling is centred
on texels. Measured main-block print height is 70.0% in Remembered and
69.8837% in Present; both have 5.42636% median measured stroke width.
The narrow cap remains width-limited, and all legends remain inside their
cap-interior rectangles. Per-cap colours, stroke widths and ink bounds are
recorded in the delivered `mapping.json`.

The Python regressions replace the old #129 size/ink pins with these exact
source-based targets and add a per-cap pigment/neutral-dust check. They keep
the 100-texel minimum, centring tolerances, inherited-dark-detail count,
housing-map equality, geometry, support and clearance assertions unchanged.
The two new finish/print expectations failed against 58a554b before rebaking.


### Final neutral raw-pixel measurements and captures

The following are mean 8-bit sRGB values from the raw 1536 by 864 PNGs,
before JPEG conversion. Cap sampling uses a common UV-interior mask across
all three keyboards, excluding both source and replacement legends, then
one-pixel erosion in the rendered frame. All three cap means use the same
19,401 pixels. Legend sampling uses each keyboard's own printed core with
one-texel erosion in the atlas and fully covered rendered mask pixels.
Different signs occupy different pixels; legend sample counts are 4,011,
3,271 and 3,567 respectively.

| Neutral diagnostic | Cap mean RGB | Legend mean RGB |
| --- | --- | --- |
| Power room | (49.36, 50.64, 51.88) | (82.55, 82.23, 77.25) |
| Quarters Present | (54.32, 55.85, 57.16) | (85.96, 85.88, 80.51) |
| Quarters Remembered | (49.32, 50.78, 51.96) | (81.82, 81.65, 76.20) |

Remembered cap means differ from the reference by at most 0.14 sRGB byte.
Present is lighter from its grey dust. The retained housing control uses
65,122 common eroded mask pixels: reference mean `(69.62,75.25,53.53)` and
Present `(69.70,75.39,53.46)`, a maximum channel difference of 0.14.
These are measurements, without image judgments.

The powered reference comes from the actual power-room route at tick 3109,
with console active, white level 1.0 and red level 0.0. The keyboard-relative
camera origin error is 0.0000005364 m. The complete transform passes the
same-pose assertion, with the same FOV, resolution and MSAA as both quarters
detail states. The normal windowed power-room route passes all 11 beats;
the windowed quarters-demo passes all 24 beats.

The 58a554b room-detail PNGs were captured before changes. For the final
neutral comparison, the exact two baseline albedos were extracted from that
commit and imported in an isolated scratch project using their unchanged
BPTC/mipmap settings. The baseline view uses the original quarters shader
and those native textures, without swapping project assets. Both reproduced
room-detail PNGs are pixel-identical to the original live-58a554b captures:
zero changed pixels and zero maximum channel difference in both states.

Fresh editor import preceded captures. Immediately before each capture,
all 395 checked sources matched their native imported `.md5` `source_md5`;
the two isolated baseline textures also passed native hash checks. Windowed
launches were serialized after `ps` checks while the sibling's headless tests
continued. No sibling process was stopped.

Logs, raw-pixel measurements and capture scripts are under
`tmp/issue129-keyboard-fix5/`. The eight JPEGs below decode with maximum
dimension 1400 pixels and retain the complete frames. Their absolute paths
are in `tmp/issue129-keyboard-fix5/jpeg-paths.json`; filenames are relative to
`tmp/issue129-keyboard-fix5/review/`:

- `power-room-powered-quarters-keyboards.jpg`
- `neutral-diagnostic-keyboards.jpg`
- `quarters-present-keyboard-detail.jpg`
- `quarters-remembered-keyboard-detail.jpg`
- `present-keyboard-before-after-58a554b.jpg`
- `remembered-keyboard-before-after-58a554b.jpg`
- `present-neutral-before-after-58a554b.jpg`
- `remembered-neutral-before-after-58a554b.jpg`

### Final verification

Console Python passes 10 tests, focused guarded quarters/Naleya passes 110,
and the full guarded Godot suite passes 1,016 with zero failures and exit 0.
Quarters aging passes 89 and fixture weather passes 11. All seven atlas PNGs
and mapping JSON are byte-identical to an independent repeated bake.
The geometry report retains zero crossings, 9.999995 mm front margin,
246.053310 mm equal side margins, 50.495964 mm display clearance and nine
support gaps of 0.561850–0.649619 mm. No geometry or UV was changed. Its
retained UV density subreport still flags ratio 2.237488; no check was changed
to suppress that flag.

The guarded logs include expected invalid-Naleya input diagnostics and
Godot resource/RID cleanup diagnostics at shutdown; they are not error-free
logs. Neither windowed route nor detail/neutral capture reported a script
error or assertion failure. Their visual verdict remains pending because
this pass deliberately makes no image judgments. OCR was not run.
Own raw PNGs, duplicate bake atlases and isolated baseline import/geometry
scratch were removed after JPEG delivery; scripts, JSON measurements and
logs remain. Existing untracked imports and assets outside this pass's
scratch were preserved.
