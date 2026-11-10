# Stasis wiring and coordinated frame damage

**Settled direction:** use a hybrid of an authored, constrained route graph with bend-, slack-, and contact-aware offline geometry baked as static meshes, plus modeled hardware fitted to measured references. No random tube or vine-like routing. Cables run beneath supported panels with clips and protection, transition to rigid wall conduit behind the pods, descend to the floor, then rise unseen into each pod base. This gives each run purposeful source-to-pod connectivity without visible wall-to-pod plugs or ends at bare walls.

Small pod translations are permitted where needed for clearance. During implementation, measure the actual lid and occupant get-up motion, aisle sweep, exit, and collisions; update purposeful route pins as needed. The current 20 mm rear gap and 303 mm panel-to-lid gap describe the present layout, not fixed design rules. Preserve pickup and prying gameplay unless a necessary change supports the wiring goal; record the reason.

The fictional ship's engineered insulation remains largely intact after 1,000 years in sealed sterile air. Use light abrasion, dust, faded markings, and localized mechanical or thermal damage at hanging spans and sparking power ends. Protect exposed runs with jackets or armour, conduit, grommets or glands, strain relief, and clamps; distinguish power and data runs. Do not make all cables rusty, cracked, frayed, or crumbling, or claim present-day PVC lasts this long. Ferrous conduit and frame may oxidize. Treat durable fictional insulation as a design choice.

The broken overhead frame and matching rusty floor member remain for a future stage. Finish the panel pull request and merge first. This note records the chosen method and next-stage workflow; it does not authorize new assets, code, concept generation, or implementation. After the panel merge, prepare a concept proof workflow and then check fit before full routing. No additional approval gate is implied.

The source reports document measured constraints and retrieved references; no game or asset changes, concept sheets, Blender work, or implementation were performed.

## What the installation should look like

A credible installation reads as equipment with origins, destinations, support points, and terminations. The power harness has a supported trunk under the panel field, restrained branches, visible glands or strain reliefs, and connectors at service points. The network loom follows a related but distinct route, with smaller separate jackets, regular ties, and different termination hardware. Both enter rigid conduit at deliberate junctions and elbows. Wall conduit descends through gaps between pods and reaches proposed service terminals behind their stationary bases.

Treat the route as a graph: source → supported trunk → clamped branch → wall conduit → pod terminal. Its branches describe connectivity. They are not a visual recipe to grow a tree of tapered tubes. Random branching, gravity-driven paths, and overlapping cylinders do not explain what each cable serves. Keep member identities through branchouts; individual insulated wires remain separate objects within a restrained bundle.

At the damaged station, release only selected power leads from specific broken supports. Their free ends hang from surviving anchors, retain plausible slack, and terminate at visibly exposed power cores where sparks occur. Network lines may be damaged too, but should not glow without an electrical fault. The remaining room wiring stays supported and orderly. The ceiling stays mostly filled: current placement is 119 of 120 cells occupied, with one planned damage area.

## Why the previous wires looked wrong

The removed implementation produced thick, uniform loops with arbitrary deep parabolas and S-bends. It had no meaningful endpoints, support/clamp system, stiffness contract, or per-cable identity. A span only 0.52 m long sagged 0.68 m while using a 40 mm radius. Smoothing or changing the curve primitive would leave the central problem intact: the paths did not describe an installed system. More tube-like geometry would make that failure more visible.

Stable sweep frames solve a different issue. Parallel-transport frames can prevent a profile or bundle from twisting unpredictably along a curve, but they do not choose a route, add endpoints, establish supports, set bend limits, or prevent collisions. A stable frame cannot make an unsupported loop look clamped. Geometry sampling and clearance checks remain necessary after smoothing.

## Route constraints and damage alignment

Measured bay-local coordinates use +Y up. The lowest panel underside is Y=2.934; the maximum pod-lid sweep reaches Y=2.631425. Their vertical gap is about 303 mm. A proposed cable/tray surface band at Y=2.74–2.88 may fit between them, but it is a planning allowance, not validated clearance. Check actual cable envelopes, brackets, fixtures, and full lid motion before implementation.

The present rear gap is about 20 mm, so the current layout does not support routing wall pipes behind the lids. Pod translations are allowed if needed; measure lid and occupant clearance, aisle sweep, exit, and collisions before fixing routes. Route through inter-pod gaps and behind the pods, then down to the floor and up unseen into pod bases. Keep supports on retained frame rails or brackets rather than unsupported panel faces.

The current opening is centered at (-1.8, 2.99, 1.5). The three existing sparks are elsewhere and do not align with it. The floor pickup is a 1 m plain round steel rod, 44 mm in diameter, centered at (-0.6, 0, -1.4); its plan distance from the opening is 3.138 m. It also does not match the 55 mm square carrier profile overhead. These facts support one coordinated damage record: a missing carrier interval, a matching rusty fallen frame piece near the current pickup anchor, and sparks attached to exposed power terminations at the damaged station. A candidate break near the current floor rod avoids a gameplay relocation, but the precise overhead alignment remains a design proposal requiring service and clearance checks.

Preserve the pickup reach, inventory behavior, and prying colliders unless a later gameplay decision changes them. Do not create additional ceiling damage to accommodate the wiring. For the roughly 1000-year-old sealed, oxygenated setting, use dust, faded markings, electrical charring, and localized corrosion on ferrous frame edges. Do not apply biological rot or rust to rubber insulation.

## Methods compared

| Method | Strength | Main limitation | Best use here |
|---|---|---|---|
| Authored route graph + constrained sweeps | Explicit sources, sockets, supports, branches, and repeatable clearance checks | Requires route and cable classes to be specified | Default for continuous room wiring |
| Authored curves + offline cable simulation | Useful sag, contact, and settling for released spans | Solver settings and final clearance need validation | A short damaged hanging section when hand-authored curves are insufficient |
| Modelled conduit and harness fittings kit | Repeatable clamps, glands, elbows, and profiles | Components do not solve routing or fit themselves | Fitting references and reusable hardware |
| Hunyuan fittings + constrained routes | Distinctive junction boxes, clamps, strain reliefs, and broken fittings with editable routes | Generated apertures and wall thickness need inspection and fitting | Hero hardware concepts, not room-wide cable routing |

The recommended hybrid combines the first and fourth methods. Use the offline simulation method selectively for damaged hanging spans. Bake the results as static meshes; no runtime physics is needed unless a later requirement calls for moving wires.

## Geometry and technical guidance

Specify bends by cable construction and overall jacket diameter. Eland's armoured power example gives fixed minimum bend radii of 6D or 8D depending on conductor size; its 7.5 mm data cable lists 4D fixed and 8D flexed. Those are product-specific examples, not universal power-versus-data rules or specifications for this fictional ship. Use them to define distinct classes, then choose and document the radius convention for each proposed cable.

Build a bundle from offset, separated strand centers rather than fused insulation. Check strand intersections through bends and at breakout points. Place ties and clamps by route distance. Use straight sections, controlled-radius elbows, couplings, and wall brackets for rigid conduit; do not give it rope sag. Sample sweeps densely enough for cable-scale bends, then recheck the smoothed paths against the complete lid motion and other obstacles.

Godot's `Path3D` and `Curve3D` store and sample paths; they do not create cable mechanics. CSG path sweeps are useful for a prototype, while Godot documents CSG as a prototyping tool with CPU costs. Generate static indexed meshes for delivery, instance repeated clamps, and retain separate damage pieces and useful culling boundaries.

Hunyuan3D's paper describes image-conditioned shape generation and separately describes texture generation. It discusses self-occlusion and texture inpainting. Thin, occluded harness strands make connectivity and small openings difficult to infer from a concept image, so missing, fused, or filled details are risks to test, not established failure rates for the local MLX port. Research on single-image reconstruction reports spatial inconsistencies in dense occlusion, but studies other objects and implementations. Use Hunyuan for substantial isolated fittings and model those to verified dimensions; do not depend on it for exact room-wide routing.

## Next decision stage

Before building anything, prepare three concept sheets: (1) supported ceiling routes and the wall transition; (2) a damaged power termination beside a distinct network loom; and (3) the paired fallen carrier fragment and matching overhead fracture. If those are later approved, make two limited proof assets: one supported bundle-to-conduit transition and one damaged hanging cable. Check visible construction, bend and clearance measurements, strand separation, support contact, and lid sweep before routing the whole room. These sheets and proof assets are proposed next steps, not completed work.

## Sources

1. [Zhao et al., harness routing](https://cjme.springeropen.com/articles/10.1186/s10033-021-00544-9): topology and route constraints; engineering model, not rendering guidance.
2. [Wang et al., rotation-minimizing frames](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/12/Computation-of-rotation-minimizing-frames.pdf): stable sweep frames; does not determine routing.
3. [SideFX Labs Cable Generator](https://www.sidefx.com/docs/houdini/nodes/sop/labs--cable_generator-2.0.html): documented cable controls, not a visual guarantee.
4. [Godot Curve3D](https://docs.godotengine.org/en/stable/classes/class_curve3d.html): baked distance sampling and orientation.
5. [Godot CSGPolygon3D](https://docs.godotengine.org/en/stable/classes/class_csgpolygon3d.html): path sweep and prototyping limits.
6. [Godot procedural geometry](https://docs.godotengine.org/en/stable/tutorials/3d/procedural_geometry/index.html): `SurfaceTool` and `ArrayMesh` options for generated geometry.
7. [Eland armoured power cable datasheet](https://www.elandcables.com/media/3ljpmrxt/bs-5467-copper-conductor-multi-core-swa-pvc-basec-0-6-1kv-cable-datasheet.pdf): product-specific construction and 6D/8D examples.
8. [Eland data cable datasheet](https://www.elandcables.com/media/efnfosiu/cat-7-s-ftp-4-pair-lszh-cable-datasheet.pdf): 7.5 mm cable and 4D/8D examples.
9. [Hunyuan3D 2.0 paper](https://arxiv.org/html/2501.12202v4): generation approach, occlusion, and texture limitations; local-port parity not assessed here.
10. [Gao et al., single-image reconstruction evaluation](https://link.springer.com/article/10.1186/s13007-025-01482-6): thin and occluded structure findings with domain and platform limits.
