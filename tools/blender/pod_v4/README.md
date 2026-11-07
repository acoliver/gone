# Pod v4 source (#88)

`pod-v4-working.blend` is the editable Y-up source. It retains the fitted
shell, closed glazing solid, couch, pillow, original base gasket and smooth
normals. The glass has explicit `pane_region` face tags: outer 0, inner 1,
cut edge 2 and polished bevel 3. `build.py` derives the single-sheet game
pane from those tags. It never repeats the perimeter trim.

Export with the retained Blender version:

```sh
/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender \
  --background --factory-startup --python-exit-code 1 \
  --python tools/blender/pod_v4/build.py -- \
  --output assets/props/pod/pod-v4.glb
godot --headless --path . --import
```

Re-export is byte-identical with Blender 4.5.11 LTS. The export contains
27,414 triangles in five mesh nodes: PodBase with Couch and Pillow, and
PodLid with WindowPane. Godot retains 19,958 triangles after shell LOD;
the pane keeps its unsimplified 5,280 triangles so the bevel and region
mask survive. The existing 20,000-triangle limit is unchanged.

Coordinates are metres, +Y up, +Z foot and -Z head. Closed bounds remain
2.392917 m long, 0.899940 m wide and 0.895995 m high. The couch plateau is
Y=0.240. PodLid's origin is the head seam at
`(0, 0.437, -1.17250931263)`. Negative local X rotation opens it. The
production open angle is 67.7295 degrees for both empty and player pods;
the rows move 206.999 mm inward to leave 20 mm behind the swept dome while
retaining a 2.5 m aisle and 150 mm exit reserve. `measure_hinge.py` checks
the sweep, contact and camera clearances against the source geometry.

The pane preserves its fitted thickness outside a 2 mm perimeter band.
Its edge has a 1 mm reveal and a three-segment 0.5 mm bevel. A closed
window seat shares PodLid and the existing Gasket material, recessed
1.5 mm below the glass exterior. Its pane-facing facets follow the retained
tapered cut-edge triangles, with 0.05 mm separation and zero measured
pane/seat intersections. Only the hidden frame-facing bottom contour is
reduced, within 0.4 mm of the new seat's original contour. The original
base gasket and white frame are unchanged by the glazing conversion.

`author_glass.py` records the one-time conversion from the original
paired solid. Ordinary editing and export use the saved tagged source.
`verify_glass.py -- --output <directory>` checks source topology, actual
bevel radii and reveal, preserved positions/thickness and aperture rays.
Run it with `--python-exit-code 1`; Blender otherwise reports Python
assertions without a failing process exit code. Smoothing must be established
before setting the derivative's custom normals. Reversing that order changed
the retained normal field by up to 38.5 degrees; the source verifier now
checks that conversion directly.

`tools/pod_geometry_export.gd` exports the actual prepared Godot arrays.
`verify_runtime.py -- --runtime <json> --output <directory>` checks their
source correspondence, welded topology, masks, normals and aperture rays.
It retains individual ray records, including first opaque material/triangle
and the triangulated source witness. The closed case includes a 5 mm grid
with a 10 mm inset. Local-normal rays measure the three-dimensional broad-face
boundary; downward rays use the projected lower skirt loop, which defines
where those rays can exit the clear opening. A surface-distance inset on the
steep flank incorrectly included the seated rim. The verifier also exports
`pane-regions-<state>.json` for rendered source-region masks. The open cases
use both directions at every broad triangle centroid. This local-pod check
does not establish full-room or perimeter-band acceptance.

Materials remain ShellPlastic, WindowTint, CouchFabric, PillowFabric and
Gasket. Blender's closed-solid preview uses Principled transmission 1,
IOR 1.5 and roughness 0.07. The GLB has a neutral transport fallback;
Godot replaces WindowTint with `app/pod_glass.gdshader`. COLOR_0 selects
the seated cut edge without tinting the broad viewing surface. PodMesh
also restores the shell clearcoat that Godot drops during glTF import.

Full glass acceptance is still open. Godot 4.7's ambient-luminance specular
occlusion erased valid probe reflections in this black-ambient room. The
shader disables that heuristic without changing the probe or adding diffuse
fill. The mirror control disables it too. The project now sets the engine
default clear color to black because interior probes omit Environment
backgrounds. Flat optics measure normalized reflection 0.03981 at normal
incidence and 0.39638 at 80 degrees, with zero measured diffuse fill. Windowed
diagnostics request draws explicitly so covered windows do not reuse captures.

The corrected projected aperture has zero near-seat hits. The sealed runtime
mesh still has 84 tub-hit deviations beyond 2 mm, maximum 3.116 mm, from its
first shell LOD. The LOD's submillimetre simplification metric does not bound
ray-witness displacement at oblique incidence. Normal rays and open-pose
centroid rays remain clear; central couch distance remains 655.995 mm.
The 20,000-triangle and 2 mm gates remain unchanged. Asset geometry is not
accepted while that witness failure remains.

`tools/glass_curved_validation.gd` checks both sides of the prepared pane
with seven pods present, including all three production states and diagnostic
70/78-degree poses. Its ten cases measure median transfer 0.94994 against
0.88–1.03, tenth percentile 0.91926 against 0.82, and correlation above 0.99999
against 0.98. `tools/pod_captures.gd -- --out <directory>` captures red, fade
and white production views. Their checker modulation transfers are
0.93650/0.94898/0.94901 against 0.80. The calculation separates the reference's
two measured cell levels: a fixed 0.15 split could leave the bright class
empty. Synthetic 0.90 transmission and opaque-black controls measure 0.90485
and 0 respectively; the transmission gate is unchanged.

The isolated `tools/glass_smoke_validation.gd` checks analytic compositing and
reversed-order controls on both sides at 0, 67.7295, 70 and 78 degrees.
`tools/glass_smoke_sweep.gd -- --regions <pane-regions-2.json> --out <directory>`
uses the production 144-particle field and broad-face source masks. It subtracts
same-view smoke-free pairs and gates the worst individual two-degree step,
not the aggregate percentage. Peak fractions above 0.08 linear RGB are
0.00373 SEALED, 0.02284 EMPTY_OPEN and 0.01869 PLAYER against the 0.01 limit.
The two open arcs fail. This diagnostic does not establish that its residual
fully separates legitimate front-smoke attenuation of reflections from a
sorting defect, or that its camera arc reproduces the actual player path.

`tools/glass_edge_validation.gd` also requires `--regions`. Its card footprint
uses the source normals and the selected 0.3 m boundary patch. The probe origin
is the selected patch: the earlier displaced origin introduced 14/27-degree
parallax errors, larger than the narrow card's four-degree half-angle. The
latest flank signal is 0.06480 against 0.005 with projected contiguous span
1.0 against 0.75, but its flattened control loses -0.00133 against the required
0.50. The rounded-end footprint has only 31.58 pixel area against 100, so that
view is invalid despite measurable response. These results do not certify
polished-edge response under production fixtures, all poses or both sides.

Clean alternating performance trials have not run: the bounded idle check
found other Godot, Blender and MLX workloads. Diagnostic GPU timestamps are
zero on this renderer, so they cannot establish GPU cost. Full smoke, edge,
performance and final visual acceptance remain open. Numerical tools exit
nonzero when their implemented gates fail; a passing diagnostic does not
certify the unimplemented parts of the advice plan.

## Production visibility checks (#88)

Padding uses light neutral medical cloth: linear reflectance
`(0.35, 0.36, 0.37)` for the couch and `(0.70, 0.71, 0.72)` for the pillow,
both at roughness 0.9. The saved source, GLB and runtime material pins agree.
The cloth remains non-emissive. The production environment retains its original
linear tonemap, exposure 2.0 and existing light intensities. Fabric visibility
must not change the look of the rest of the game.
`pod_captures.gd` saves a linear half-float `sealed-close-red.exr` and measures
red saturation separately for couch and pillow through the pane using geometry
ID masks. The couch-shape gate permits at most 20% clipped couch pixels;
fixture highlights elsewhere in the frame do not enter that gate. PNG saturation
is reported separately because eight-bit rounding can also produce 255.
At the permitted couch reflectance floor, the fix8 sealed-red capture still
clips 60.44% of couch pixels and 91.17% of pillow pixels. The couch-shape gate
therefore fails; meeting 20% would require a change beyond the allowed fabric
adjustment. The near-white pillow is unchanged. The flat and curved optical
fixtures and their thresholds remain unchanged.
`Lighting` adds short-range red belt-spill and head-wall-bounce proxies because
emissive belts alone do not light nearby geometry without GI. Room ambient
and collision remain unchanged.
The head pivot still has 0.322 mm source contact clearance; its dark wedge
was the unlit head-facing shell, not a wall intersection or a hole at the axis.

`pod_captures.gd` retains the production cameras and adds white-fabric/lid-hidden
controls plus an isolated same-pod mirrored pair with symmetric white lights.
`tools/pod_diagnostic_export.gd` writes their prepared world-space surfaces;
`diagnose_views.py -- --captures <directory>` raycasts those surfaces with
render-face culling. `tools/pod_pixel_measurements.py --captures <directory>`
uses NumPy/Pillow to report linear Rec.709 luminance, paired edge contrast,
first-hit dark-region counts and mirrored strip rows. It makes no visual
acceptance claim. The curved, smoke, sweep and edge tools above are retained
as reusable diagnostics, including their documented failing cases.

The source originated in the local reconstruction and clean-cage fitting
pipeline. Scratch fitting scripts and external weights are not export
dependencies. `build_pod_probe.py` belongs to the earlier #45 probe.
