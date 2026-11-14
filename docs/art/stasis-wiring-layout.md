# Stasis wiring layout and fault

The stasis bay has one installed network connecting its source enclosure to all seven pod bases. `StasisWiring.installation()` places it beneath `BayRoot`. The [installation guide](stasis-wiring-production-installation.md) lists source files, outputs, rebuild commands and tests.

All coordinates here are bay-local metres, +Y up. The source enclosure is at `(-5.935, 2.75, -3.1)`, yaw +90 degrees. Two power jackets and six data strands follow supported overhead routes, descend between pods and enter floor conduit. Hidden distribution reaches stationary pod bases without hoses across the walking gaps.

Power crosses the floor at `(-4.02, 0, -3.93)` in 60 mm conduit; data crosses at `(-4.18, 0, -3.955)` in 25 mm conduit. Buried junctions have physical apertures, terminated jackets and separate copper links inside their enclosures. Pod terminals remain hidden inside their stationary bases.

## Coordinated damage

One ceiling panel cell, `(4,4)`, is empty, centered at `(-0.6, 2.99, -0.9)`. The lower formed seat fails at `(-0.6, 2.988, -0.6)`. Upper carriers stay continuous. The matching floor fragment is the pickup used to pry the bay hatch. Its source and placement are described in the [seat guide](seat-production-integration.md).

Three released insulated power cores emerge from clamped jacket ends, turn downward and expose only their final 4 mm of copper. The fourth jacket has a closed insulating cap. Data remains supported and has no sparks.

| Jacket end | Jacket endpoint | Copper tip endpoint |
| --- | --- | --- |
| Left power 1 | `(-1.15, 2.82, -0.587)` | `(-0.77, 2.486, -0.587)` |
| Left power 2 | `(-1.15, 2.82, -0.613)` | `(-0.83, 2.556, -0.613)` |
| Right power 1 | `(-0.05, 2.82, -0.613)` | `(-0.35, 2.526, -0.613)` |
| Right power 2 | `(-0.05, 2.82, -0.587)` | Closed cap; no exposed copper |

`tools/stasis_wiring_fault.py` authors the cores and copper solids. `assets/props/stasis-wiring/production-routes.json` supplies semantic routes to `sim/stasis_wiring_routes.gd`. Spark placement follows those physical tips through `Placement.spark_spots()` and `Hazards`.

## Verification and limitations

Use the build and test commands in the [installation guide](stasis-wiring-production-installation.md#rebuild-and-verify). The checks cover source-to-pod continuity, physical interfaces, exported conductor separation, lid sweeps, support and service clearances. `tools/test_stasis_wiring_fault.py` covers the exposed tips and closed fourth jacket.

The network is static dressing. It has no cable physics or independently repairable cable interactions. Diagnostic white-light captures reveal construction and are separate from the ordinary red-lit opening.
