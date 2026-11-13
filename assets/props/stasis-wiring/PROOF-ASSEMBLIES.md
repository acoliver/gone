# Stasis wiring physical proofs

These are two isolated proof sections for issue 110. Neither is installed in the game scene.

`supported-transition.glb` contains two continuous 24 mm power jackets, six separate 6 mm data jackets on a 6.4 mm hex radius, compact ties, rail-mounted saddles, separate 60/25 mm conduit, floor collars and hidden underfloor continuations. The source positions come from `sockets.json`. Cables start inside the gland padding and initially travel along +Z. Power and data have different controlled slack. Drops occupy the panel seams; cantilever arms sit below the panel undersides.

`fault-frame-pair.glb` contains the retained hollow carrier ends, the matching fallen 1 m fragment, two short supported power leads and three 4 mm copper ends. Six healthy data jackets remain tied to retained structure. The 55 mm square carrier has 3 mm walls. One shared fracture record creates both retained cuts and fragment ends. The fallen mesh uses the recorded 82-degree transform, not another fracture generator. The lower ledge ends bend away from the opening.

Each GLB has a corresponding editable `.blend`. Material-group meshes and hidden editable route centerlines use Blender's native Z-up frame. GLB import and `export_yup=True` perform the frame conversion exactly once. The enclosure remains a separate production reference so replacing its hardware does not require rebuilding the wiring.

## Build and inspect

From the repository root, using the existing local geometry environment:

```sh
/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python tools/build_stasis_wiring.py
/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python -m unittest discover -s tools -p 'test_stasis_wiring_*.py' -v
godot --headless --editor --path . --import
godot --headless --path . -s tools/run_stasis_wiring_tests.gd
godot --path . -s tools/capture_stasis_wiring.gd -- /Volumes/XS1000/acoliver/projects/gone/branch-4/tmp/verify-stasis-wiring/assemblies
```

The focused Godot runner inherits the existing child-process script-error guard. It does not run the complete suite. Capture requires a real rendering window and writes six 1280×960 PNGs plus `capture-manifest.json`, with source/GLB hashes, cameras, renderer, exit code and readback statistics. Material bindings use the existing weathered-steel shader and ceiling-panel materials. The enclosure retains its imported PBR materials; jackets are non-emissive dark rubber at roughness 0.7.

## Interfaces and measurements

`StasisWiring.build(&"supported-transition")` and `StasisWiring.build(&"fault-frame-pair")` instantiate cached static resources in bay-local metres, +Y up. `include_context=false` omits the proof panels, wall and floor. No per-frame generation runs. `isolate_fragment()` selects the fallen piece for inspection.

`proof-assemblies.json` records constructed centerlines, jacket-surface bend measurements, packing, individual clamp contacts, panel-seam clearances, conduit-floor contact, exported bounds and matching fracture hashes/triangle planes. Its physical graph refers to exact sample ranges of the constructed routes and rejects disconnected feeds. The three future spark anchors are `assemblies.fault-frame-pair.metrics.power_core_tips_m`.

The physical graph ends at declared underfloor proof boundaries. Seven-pod installation, full moving-lid/get-up clearances, pickup wiring and production regression tests remain outside this proof stage. Visual acceptance belongs to the parent image-comparer review.
