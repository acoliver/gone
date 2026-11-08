# GONE ceiling light, round 2

All authored files are in `tmp/lights-redo/round2/`. The Hunyuan sources, concept images, round-1 outputs, hatch textures and shader are read-only inputs. No branch, index, tracked file or Git configuration was changed. No foreign process was signalled. All baking and rendering uses CPU Cycles, not the shared GPU.

## Reproduce the asset and measurements

Run from `/Volumes/XS1000/acoliver/projects/gone/branch-1`. These variables abbreviate the full paths used by the commands in this session.

```sh
R=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/lights-redo/round2
B=/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender
P=/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python
sleep 1
"$B" --background --factory-startup --threads 4 --python-exit-code 1 --python "$R/inspect_source.py" > "$R/inspect.log" 2>&1
"$B" --background --factory-startup --threads 4 --python-exit-code 1 --python "$R/build.py" > "$R/build.log" 2>&1
PYTHONDONTWRITEBYTECODE=1 "$P" "$R/weather.py" > "$R/weather.log" 2>&1
"$B" --background --factory-startup --threads 4 --python-exit-code 1 --python "$R/finish.py" -- --export-only > "$R/export.log" 2>&1
PYTHONDONTWRITEBYTECODE=1 "$P" "$R/verify.py" > "$R/verify.log" 2>&1
"$B" --background --factory-startup --threads 4 --python-exit-code 1 --python "$R/finish.py" > "$R/renders.log" 2>&1
PYTHONDONTWRITEBYTECODE=1 "$P" "$R/report.py" > "$R/report.log" 2>&1
touch "$R/READY"
```

The longer commands were run under managed background supervision with `nohup`, rather than left in a foreground shell subject to the workstation watchdog. The final combined invocation was:

```sh
sleep 1
nohup bash -c '/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 4 --python-exit-code 1 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/lights-redo/round2/build.py && PYTHONDONTWRITEBYTECODE=1 /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/lights-redo/round2/weather.py && /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 4 --python-exit-code 1 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/lights-redo/round2/finish.py -- --export-only && PYTHONDONTWRITEBYTECODE=1 /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/lights-redo/round2/verify.py && /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 4 --python-exit-code 1 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/lights-redo/round2/finish.py' > /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/lights-redo/round2/final-run.log 2>&1
```

## Geometry operations

`build.py` imports `../hunyuan/720/painted.glb`, which contains the 315,154-triangle seed-720 generated surface and its painted albedo. It applies the same 90-degree native-X orientation as round 1, then fits the specified metric envelope. Blender authoring remains Z-up, with front along -Y. Export uses `export_yup=True`, so the external result has +Y up, front +Z, mounting height Y=0, and body below that plane.

The original body is voxel remeshed at 2 mm and faired for 28 smoothing iterations. Both generated ends are clipped at source-fit X +/-0.533 m and closed from their own boundary. A sampled underside field moves the lower skin toward a flat datum without replacing the roof and side contours. A second 1.7 mm voxel weld removes folds in the original lip. The bottom is bisected and closed rather than collapsed onto a coincident surface. The generated shell is reduced before machining.

A centred, 94 mm-wide strip is clipped from that generated lower skin. Its top and bottom are made planar with 4 mm thickness. A local 60 x 47 mm repair closes the generated left corner that otherwise exposed glass outside the first slot. Fourteen bevel-ended transverse slots are boolean-cut through this retained skin. Their pitch is 70 mm, their length along the beam is 36 mm, and their cross-beam span is 66 mm. A corresponding 20 mm-deep recess is cut into the body behind it. Edge rails and sixteen small fasteners are separate metal parts. The four end fasteners remain inside the overall envelope.

The 3 mm frosted diffuser has its downward surface 13 mm behind the underside plane. It is opaque and emissive, with no transmission dependency. It is a separate part, not an emissive assignment to irregular generated triangles. The rest of the underside is olive steel. Disconnected scan debris is removed; the generated beam is not replaced by a box.

## Paint and normal bake

`build.py` smart-unwraps the cleaned generated shell and CPU-bakes the painter's diffuse colour and the dense source's tangent-space normals onto 1024-square maps. It also bakes position and geometric normal fields for physically scaled material masks. The normal texture is used at strength 0.14, limiting scan relief while retaining generated detail.

`weather.py` uses the existing hatch steel and oxide image scans at 0.20 m pitch, following the scan-sampling and geometry-mask approach in `app/shaders/weathered_steel.gdshader`. The rebaked painter contributes 8% broad tonal variation after clamping and filtering; its red and dark islands do not survive as rust patches. A 1.5 mm edge mask selects photographed oxide and exposed metal. Four end fasteners supply 1.2 mm half-width gravity streaks with 29 mm lengths; three selected rail positions supply shorter underside stains. Rust changes albedo and roughness only, with no raised geometry or rust bump.

`olive_unweathered_control.png` disables the weather contribution while keeping the same underlying olive paint. A matching lit capture measures whether the weather has visible image contrast. `weather-stats.json` records edge-versus-broad-face oxide measurements.

## Verification and renders

`verify.py` loads the exported GLB with trimesh, applies the glTF node transforms, and measures bounds, axes, triangle count, welded topology and downward glass normals outside Blender. It casts 112,500 vertical rays across the footprint and 67,500 across the grille. A 5,201-sample centreline counts visible slot runs. Six further 35,000-ray tests use +/-15, +/-35 and +/-55 degree views across the strip. Glass first hits must pass through a slot at the actual grille plane, and visible glass normals must point down. UV and normal seams are welded only for topology checks.

`finish.py` exports the fixture alone, saves `fixture.blend`, then constructs a preview-only dark grey ceiling and two soft room fills matching round 1. It renders 1200 x 900, 48-sample CPU Cycles images from below at 2.5 m, below close, three-quarter, both ends, emissive off, and weather disabled. The ceiling and lights are not exported. `report.py` creates the labelled 2160-pixel-wide comparison sheet with concepts 202/210 and round-1/round-2 views, computes lit-control differences, and writes `results.json`. No visual quality judgment is made.

## Commands used during diagnosis and iteration

Before authoring, the following read-only checks distinguished pre-existing work and graphics jobs:

```sh
git status --short
ps -axo pid,etime,%cpu,command | grep -Ei 'blender|mflux|hunyuan|mlx|comfy' | grep -v grep
cat "$R/source-inspection.json"
```

These are the issued build and verification variants, in order, with the same variable substitutions as above:

```sh
# Initial launch with both a trailing ampersand and managed background mode exited without starting Blender.
sleep 1; nohup "$B" --background --factory-startup --threads 4 --python-exit-code 1 --python "$R/build.py" > "$R/build.log" 2>&1 &
# Corrected managed-background launch, no trailing ampersand:
nohup "$B" --background --factory-startup --threads 4 --python-exit-code 1 --python "$R/build.py" > "$R/build.log" 2>&1
sleep 1; PYTHONDONTWRITEBYTECODE=1 "$P" "$R/weather.py"
sleep 1; "$B" --background --factory-startup --threads 4 --python-exit-code 1 --python "$R/finish.py" -- --export-only > "$R/export.log" 2>&1
sleep 1; PYTHONDONTWRITEBYTECODE=1 "$P" "$R/verify.py" > "$R/verify.log" 2>&1
sleep 1; nohup "$B" --background --factory-startup --threads 4 --python-exit-code 1 --python "$R/build.py" > "$R/build-debug.log" 2>&1
sleep 1; nohup "$B" --background --factory-startup --threads 4 --python-exit-code 1 --python "$R/build.py" > "$R/build-fixed.log" 2>&1
PYTHONDONTWRITEBYTECODE=1 "$P" "$R/weather.py" > "$R/weather.log" 2>&1
"$B" --background --factory-startup --threads 4 --python-exit-code 1 --python "$R/finish.py" -- --export-only > "$R/export.log" 2>&1
PYTHONDONTWRITEBYTECODE=1 "$P" "$R/verify.py" > "$R/verify.log" 2>&1
```

The same `build.py && weather.py && finish.py -- --export-only && verify.py` sequence was then launched under `nohup bash -c`, with each command using the full paths above, into `pipeline.log`, `pipeline-closed.log` and `pipeline-final.log`. A separate `verify.py && finish.py` sequence was launched into `renders.log`; the oblique test stopped that sequence before rendering. The final combined invocation is printed in full above and supersedes those attempts.

The initial flattened-triangle method created coincident faces and failed the first boolean. Replacing it with a bisected closed lower surface retained the beam. A later whole-depth threshold collapsed the thin extracted grille; assigning top and bottom from its own clipping plane fixed the thickness. The ray grids located the missing left corner. Trimesh split analysis then identified the remaining apparent body boundary as a disconnected one-triangle artefact, rather than a hole in the main closed shell. Removing its three vertices fixed closure. Oblique ray tests identified the residual slope in the grille skin; assigning its top and bottom to separate parallel planes fixed that aperture error. Failed attempts are retained in their logs.

Additional numerical diagnostics were run with:

```sh
sleep 1; PYTHONDONTWRITEBYTECODE=1 "$P" "$R/diagnose_export.py" > "$R/diagnose-export.log" 2>&1
PYTHONDONTWRITEBYTECODE=1 "$P" -c 'import trimesh; s=trimesh.load("/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/lights-redo/round2/fixture.glb"); m=next(g.copy() for n,g in s.geometry.items() if g.visual.material.name.startswith("OliveSteel")); m.merge_vertices(merge_tex=True,merge_norm=True); print([(len(p.faces),p.is_watertight,p.area) for p in m.split(only_watertight=False,repair=False)])'
```

Progress-only shell checks used `tail -n 4`, `tail -n 5`, `tail -n 8`, `tail -n 9`, `tail -n 10`, `tail -n 12`, `tail -n 15`, `tail -n 16`, `tail -n 20` and `tail -n 25` against the corresponding logs above; `grep '^STEP'`, `grep 'GRILLE_RAW_DEPTH\|Weighted face normals faces'`, `grep -Ei 'WARN|ERROR|invalid|degenerate'` and `grep -E 'VALIDATE|WARNING|Error'` against the build/pipeline logs; and `ps -axo pid,etime,%cpu,command | grep 'round2/build.py' | grep -v grep`. These commands only read state. No install, download, Godot import, Git write or process-signal command was used.
