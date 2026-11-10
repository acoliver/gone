# Issue 110 concept and measurement handoff

This source-art stage creates concept references and records constraints only. The merged runtime scene, gameplay, assets, and startup path remain unchanged. Coordinates below are bay-local, +Y up, and are transformed once by `ShipLayout.bay_to_world()` at `BayRoot`.

## Measured room and service envelope

- Room: 12.0 m long × 8.0 m wide × 3.2 m high. Ceiling is Y=3.2 m.
- Panel grid: 10 × 12 cells, 1.2 × 0.6 m. Panel seats at Y=2.99 m; each fitted panel footprint 1.18 × 0.58 m. One currently empty cell `(3,8)` is centered at bay-local `(-1.8, 2.99, 1.5)`. The carrier frame top is Y=3.12 m with 55 × 55 mm square rails.
- Present localized frame variants: broken-edge `(3,9)` and sag `(2,8)`, adjacent to the empty cell. Preserve these existing visuals in the concept target except where a future coordinated damage change is explicitly proven.
- Lowest panel detail underside is about Y=2.934 m; current pod-lid sweep top is Y=2.631425 m, leaving about 0.303 m vertical separation before cable/support envelopes.
- Six ceiling fixtures are centered at X `[-4.2,-0.6,4.2]`, Z `[-1.5,1.5]`; each measured fixture body is 1.10 × 0.10 × 0.22 m, top at Y=3.2 and bottom at Y=3.1. Avoid their bodies and reserved sightlines. Existing emergency ceiling service positions are X `[-4,0,4]`, Z `[-1.6,1.6]`; vents at X ±3, Z=0.
- Floor pickup rod: length 1.0 m, diameter 44 mm, center `(-0.6,0,-1.4)`. Keep pickup, inventory and prying behavior.

## One coordinated damage proposal

Candidate center is ceiling cell `(4,4)`, bay-local `(-0.6,2.99,-0.9)`, near the floor rod (0.5 m plan separation) without directly overlapping the regular fixture at `(-0.6,-1.5)`. Align one missing/fractured carrier interval and localized released power supports there; place a matching 1 m, 55 mm square rusty carrier fragment near the existing rod pickup. The visible opening currently sits at `(-1.8,1.5)`, about 3.14 m from the rod, so final alignment requires a later measured change to the damage station, not arbitrary extra holes or sparks. Before production changes, inspect fixture/service bounds and verify actual lid sweep, pod get-up, aisle/exit and collisions. This candidate is not a clearance certification.

## Appearance and next stage

Keep the installed power trunk distinct from smaller tied control/data looms. Planning diameters: 22–28 mm power and 6–8 mm data, not universal specifications. Show repeated clamps, strain relief, protected large-radius elbows and rigid wall conduit descending behind pods into concealed floor-fed pod bases. The 1,000-year-old engineered insulation remains mostly intact; dust, abrasion and faded bands are restrained, with oxidation on ferrous supports. Expose copper and sparks only at a few torn power ends at one fault. Avoid unsupported loops, floating ends, random branches, blanket insulation failure and neon cyberpunk colours. White pods contrast with worn olive/charcoal hardware.

Concept files and exact prompts/seeds are recorded alongside this document in `art-source/stasis-wiring/`. Request for the next stage: parent image-comparer reviews all three concepts; use the isolated transition-housing image as the full-model Hunyuan reference, then fit/adjust discrete entry apertures to verified measurements. Do not condition Hunyuan on a cable-tangle scene. No image is asserted approved here.
