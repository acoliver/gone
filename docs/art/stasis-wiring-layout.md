# Issue 110: installed wiring and coordinated fault

The production bay now installs the source-to-seven-pod network and its localized power fault through `StasisWiring.installation()`. [Production installation notes](stasis-wiring-production-installation.md) give the coordinates, build commands, physical checks and native capture limits. Earlier five-riser, Z=-1.2 fault and upper-carrier fracture proposals are superseded.

The source is mounted at `(-5.935,2.75,-3.1)`, yaw +90 degrees. Two 24 mm power jackets and six 6 mm data strands use measured clamps, source compression fittings, and one wall-drop pair. Power crosses the floor at `(-4.02,0,-3.93)` in 60 mm conduit; data at `(-4.18,0,-3.955)` in 25 mm conduit. Hidden distribution reaches seven stationary plinths without exposed hoses across walking gaps.

## One coordinated failure

The only missing panel remains cell `(4,4)`, center `(-0.6,2.99,-0.9)`. Only the lower formed seat fails, at `(-0.6,2.988,-0.6)`. Upper carriers remain continuous. The accepted seat profile/material, matching floor fragment, 115-degree roll, pickup anchor/proxy/collider/reach, and hatch-pry behavior are unchanged.

Three released 8 mm insulated power cores emerge through tapered boots from clamped 24 mm jacket ends. The fourth jacket is closed with an opaque insulating cap. No cable ends are left floating without a termination. Each released core turns through a measured 160 mm radius and exposes only its last 4 mm of copper, with 1.6 mm copper radius.

| Physical jacket end | Jacket endpoint, bay-local metres | Treatment | Copper tip endpoint |
| --- | --- | --- | --- |
| Left power 1 | `(-1.15,2.82,-0.587)` | Released core, approaches +X then turns down | `(-0.77,2.486,-0.587)` |
| Left power 2 | `(-1.15,2.82,-0.613)` | Released core, approaches +X then turns down | `(-0.83,2.556,-0.613)` |
| Right power 1 | `(-0.05,2.82,-0.613)` | Released core, approaches -X then turns down | `(-0.35,2.526,-0.613)` |
| Right power 2 | `(-0.05,2.82,-0.587)` | Closed insulating cap, nose at `(-0.068,2.82,-0.587)` | None |

`tools/stasis_wiring_fault.py` authors these physical cores and copper solids. Their generated records in `production-routes.json` supply `StasisWiringRoutes`, `Placement.spark_spots()` and the three named `Hazards` emitters. The semantic graph connects each tip and the sealed fourth end to the source as well as retaining all seven power/data feed pairs. Data is supported and has no sparks. Spark timing, smoke, wake/eyes, power behavior and gameplay are unchanged.

The retired twelve-run `Wires.build()` presenter had no production call site. It and its loose-wire recipes have been removed. The tests now pin the three specific physical tips, 4 mm exposure, retained supports and closed fourth jacket instead of the old loops/strands/frays inventory. No second dressing is installed.

## Physical verification and captures

The builder separately audits the new fault against complete native lid arcs, fixture/service reservations and continuous standing/get-up camera/capsule height envelopes. The supported-network clearance result is not used as proof for released leads. Exported GLB copper components are checked outside Blender for exactly three exposed closed solids at the expected positions and lengths.

Native `main.tscn` captures include the natural wake blinks, open-eye frame and Standing reached by ordinary Space input. Separate diagnostic cameras record the installed source, routing, floor entry, fault, copper tips, matching fragment and non-bay hallway. White diagnostic views use the existing secondary circuit with no added lamps or material overrides. Inspection views are not evidence of the ordinary opening.

Current corrected logs, exported junction/overhead checks, fingerprinted snapshots, PNGs and capture readbacks are under `tmp/verify-stasis-wiring/production-corrected/`. The earlier `production-final/` directory is historical and contains the pipe-wall and takeoff overlaps identified by the review. See the installation notes for current results and commands. Appearance assessment remains with the separate visual worker.
