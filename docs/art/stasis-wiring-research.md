# Stasis wiring construction method

The installed bay wiring uses an authored route graph, constrained offline sweeps and separately fitted hardware. Static meshes carry the result into Godot. The [layout](stasis-wiring-layout.md) describes the network and fault; the [production guide](stasis-wiring-production-installation.md) lists its sources, outputs, build commands and tests.

## Routing and supports

Each route has a source, destination, supported spans and physical terminations. Power and data use distinct jacket sizes and separate paths. Clamps, glands, wall conduit and buried distribution explain how the network reaches each stationary pod base. No exposed hose crosses a walking gap.

Free power leads belong only at the coordinated fault, suspended from surviving anchors and ending at the copper tips that emit sparks. The rest of the network remains supported. The shared [ceiling seat](seat-production-integration.md) provides the matching overhead gap and floor pickup.

Routes must clear full lid sweeps, the get-up path, the standing capsule, fixtures and service reservations. Check the exported mesh envelopes as well as centerlines. Parallel-transport frames control sweep twist; routing, support and collision checks still determine where a cable may go.

The fictional insulation remains largely intact after prolonged sealed storage. Light abrasion, faded markings and localized electrical damage distinguish it from corroded ferrous supports. This is an authored material choice, not a claim about the lifetime of present-day cable insulation.

## Geometry choices

Choose bend radius by cable construction and jacket diameter. Product datasheets can inform a class, but their limits do not transfer automatically to every cable. Keep individual strands separated through bends and branchouts. Rigid conduit uses straight runs, controlled elbows, couplings and mounted brackets.

The offline route tools under `tools/stasis_wiring_*.py` generate static indexed meshes. Hunyuan is useful for isolated substantial fittings, where apertures and thickness can be inspected and fitted. Room-wide connectivity comes from the authored graph. Thin hidden strands are poor candidates for inferring exact connections from one image.

Run the production guide's rebuild and verification commands after changing routes. `tools/test_stasis_wiring_geometry.py`, `test_stasis_wiring_production.py` and `test_stasis_wiring_fault.py` cover the geometric and endpoint contracts.

## References

- [Harness routing research](https://cjme.springeropen.com/articles/10.1186/s10033-021-00544-9): topology and constrained routing.
- [Rotation-minimizing frames](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/12/Computation-of-rotation-minimizing-frames.pdf): sweep orientation.
- [Godot procedural geometry](https://docs.godotengine.org/en/stable/tutorials/3d/procedural_geometry/index.html): static mesh construction options.
- [Hunyuan3D 2.0 paper](https://arxiv.org/html/2501.12202v4): image-conditioned shape and texture generation.

## Known limitations

The network has no runtime cable mechanics. External routing and reconstruction references describe other systems and do not validate this implementation. Current collision and continuity claims come from the project's exported-mesh and native-scene checks.
