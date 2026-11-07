# Protagonist's quarters: plan (#95)

Status: proposal, 2026-11-07. Nothing here is built yet.

## What Andrew decided

- **Style:** concept B, the industrial version: grey-green riveted steel bulkheads, exposed ribs, pipe runs and conduits, softened by the couple's belongings ([`concept-pair.png`](concept-pair.png); remembered on the left, present on the right).
- **Size and contents:** officers' quarters for a couple, about twice the size of the first single-cabin concept. The room has:
  - a double bed;
  - a sofa facing a wall view screen;
  - a small table with two chairs;
  - a desk with a hardened military console that still works;
  - a wardrobe holding his uniform;
  - built-in storage on every wall except the entrance;
  - belongings for both of them.

  There are no windows and no books or paper.
- **Two states:** he enters, sees the room as he remembers it, and looks up from the console into the present.
- **Age:** about a thousand years in sealed, sterile, oxygenated air (ruling 25 in [`decisions.md`](../../design/decisions.md), #93/#94).
- **Location:** not fixed. Andrew is thinking about two decks below the opening, which would make it D16. That deck band (D13–16) already lists proposed awake-crew quarters in the [ship atlas notes](../ship/README.md). Both ladder wells reach every deck, so D16 is reachable without new geometry rules. The room design below does not depend on the deck.
- **Method:**
  - No prop is modelled by hand or built from primitives in Blender or Godot.
  - Every prop starts as a contact sheet of generated images. The local Hunyuan3D install turns it into a mesh, and the mesh is then fitted and adjusted, following the `concept-to-3d-asset` skill.
  - Build the unaged props first, then build tools that derive the aged versions from them.

## Methods this reuses

These have already been proven in this project, and the plan builds on them rather than inventing new ones.

- **The round hatch** (branch-1, `issue-sliding-doors`, not yet on `main`):
  - **Geometry:** generated images of the frame and leaf (`art-source/hatch/`) went through Hunyuan into parts, which were fitted and repaired (`tools/blender/hatch_fit.py`, `hatch_generated_*.py`).
  - **Paint colour:** generated, shadowless images of the concept paint, packed into an atlas (`tools/prepare_hatch_paint.py`).
  - **Masks:** baked per model in Blender: ambient occlusion, curvature, coverage and weather (`tools/blender/hatch_bake.py`).
  - **Material:** the shared, approved `app/shaders/weathered_steel.gdshader` layers paint, bare steel and oxide over the CC0 Poly Haven steel scans already in `art-source/steel` and `assets/surfaces/steel`. The ship's shells and doors use the same shader.
- **The stasis pods** (#88, on `main`):
  - **Geometry:** clean-cage fitting.
  - **Glass:** the thin-glass shader `app/pod_glass.gdshader`. It needs a real opening, a reflection probe and `specular_occlusion_disabled`.
  - **Plastic:** glossy plastic with its clearcoat restored in code.
  - **Verification:** the glass gates and the capture and raycast diagnostics.

The quarters props use the hatch's texture and weathering method for everything metal, and the pod glass for every pane: the view screen, the console screen cover and the photo-frame glass. Quarters implementation depends on the branch-1 steel and hatch work reaching `main`, so stage 2 starts after it merges.

## Decisions I made, and why

1. **Room shell versus props.**
   - **Decision:** the walls, floor, ceiling, ribs, pipe runs and door frame stay on the shared room-geometry system (`app/room_geometry.gd` and the wall/floor/ceiling surface sets), like every other compartment. Everything that sits in or on the room is a generated prop.
   - **Why:** the rest of the ship already builds rooms this way, and its colliders, streaming and lighting depend on it.
   - **What's new:** a clean "as built" surface set for the remembered state. The existing worn surfaces in `assets/surfaces/` are already aged.
2. **One base asset per prop; the aged state is derived from it.**
   - **Decision:** each prop has one unaged model. Its aged state comes from that model, never from a second, independent generation. Both states keep the same origin, pivots, part names and footprint.
   - **Why:** the memory transition swaps states in place, so the two must line up exactly.
3. **How each prop gets its aged state depends on whether its shape changes.**
   - **Hard props whose shape stays put** (lockers, desk, console, wardrobe, table, chairs, bed frame, screen housing, frame):
     - one mesh, with the weathered-steel masks baked once;
     - two material settings: "as built" (paint intact, no oxide, no dust) and "after a thousand years" (paint flaked, oxide, streaks, dust).
     - The transition swaps the material settings. This is the hatch method plus a clean end of its range.
   - **Props whose shape changes** (mattress, quilt, pillows, cushions, throw, garments, jacket, boots, and the dust and debris heaps):
     - a second mesh produced by the aging toolkit's geometry transforms, baked as its own asset.
     - A shader can blend colour but cannot collapse foam or tear cloth.
4. **The photo ages like everything else.** Andrew: the photo doesn't change except for what a thousand years would do.
   - **Decision:** a printed photo on a durable polymer plate, behind pod-style glass, in a metal frame.
   - **After a thousand years:**
     - the dyes have faded and shifted in colour;
     - the glass is hazed with dust;
     - the frame has corroded;
     - the couple are still faintly recognisable.
   - **Why a print:** a digital frame would simply go dark, which isn't what he described. A single keepsake print fits his "no paper books" rule better than a screen does.
5. **Pilot before mass production.**
   - **Decision:** take three props through every stage first:
     - a wall locker module (painted steel);
     - the sofa (foam and fabric);
     - his uniform on its hanger (a hanging garment).
   - **Why:** between them they cover the hard, soft and cloth classes. The rest of the inventory only starts once all three pass.

## Inventory

Every prop's parts are split along the lines the aging toolkit needs (stage 3). Sizes are starting targets; Andrew can change any of them.

| Prop | Parts kept separate | Target size (m) | Notes |
| --- | --- | --- | --- |
| Double bed | frame, headboard pad, mattress, quilt, 2 pillows | 2.20 × 1.60 bed | Sized for the 2.03 m occupant used for the pods |
| Bedside unit × 2 | carcass, drawers, lamp | 0.45 wide | Lamps work in the memory only |
| Overhead lockers above bed | carcass, doors | per wall bay | Modular |
| Wall storage modules | locker, drawer bank, open shelf, cabinet | modular 0.6 grid | Snap to one grid so they tile every wall |
| Sofa | frame, seat cushions, back cushions, throw blanket | 2.0 × 0.9 | Pilot prop |
| View screen | housing, glass, display surface | 1.6 diagonal-class | Display surface separate, so it can be dead or cracked |
| Round table | top, base | 0.9 diameter | |
| Dining chairs × 2 | frame, seat pad | | Must match each other |
| Her jacket over a chair | jacket | | Generated in its draped pose |
| Desk | desk body, drawers | built in | |
| Military console | armoured housing, bezel, display surface, keys and toggle panel | | Display stays emissive and clean in both states (gameplay screen) |
| Desk chair | frame, seat pad | | |
| Wardrobe | carcass, door (pivot), rail | 0.9 wide | Door open in both states |
| His dress uniform on hanger | hanger, jacket, insignia | | Pilot prop; insignia separate (metal) |
| Her dresses × 2 on hangers | hanger, garment | | |
| His boots | pair | | |
| Photo frame | frame, glass, photo plate | | Ages physically: faded dyes, hazed glass, corroded frame |
| Mugs × 2, plates × 2 | each | | Ceramic |
| Hairbrush, jewellery box, medal case, data tablets × 2 | each | | Small; one contact sheet can hold several |

That is about 25 distinct props, a few of them repeated.

## Stage 0: room layout

**Plan view.** Draw a top-down plan from concept B and place each prop with its footprint and its clearance to walk past.
- Room: 8.0 m along the hall by 6.0 m deep, with the ship's 3.2 m clear height. Andrew found 5.6 × 5.0 m too small. The quarters are on a deck that isn't built yet, so the 6 m spacing between D14's side doors doesn't constrain them.
- Entrance in the near wall. Bed centred on the far wall. Living area and screen on the left. Desk, console and wardrobe on the right. Table in the middle-left.
- Andrew approves the plan view before any prop is generated.

**Camera.** Record the doorway camera that matches the concept, for later comparison captures.

**Output.** `docs/art/quarters/layout.json` holds the room size and every prop's position, footprint and facing. `tools/art/quarters_plan.py` renders `plan.png` from it and checks the layout, writing the results to `plan-checks.json`:
- footprints inside the room, with no overlaps;
- every use point reachable by the 0.6 m player capsule;
- walkways at least 0.9 m wide on the widest route;
- no storage on the entrance wall;
- the doorway clear.

One change from the concept: the dining table sits right of the door path. On the left it blocked the aisle beside the bed.

## Stage 1: contact sheets (unaged)

A contact sheet is a set of images of one prop that the image-to-mesh model can use. Each prop's sheet must show:
- one object, in its final state (wardrobe door open, jacket draped);
- on a plain light grey background, in soft even light;
- with little perspective: a three-quarter hero view, plus front, left, back and right views of the same object.

**Generating it**, with local tools only (`references/local-tools.md` in the skill):
1. **Hero view:** generate it with Z-Image-Turbo, using a style prefix taken from concept B: brand-new grey-green painted steel, rivets, military-ship hardware. Make several seeds per prop.
2. **Other views:** produce them with FLUX.2-klein edit, using the hero and a crop of concept B as references ("the same object seen from its left side"). This gives better odds that the views match than separate prompts would.
3. **Review:** the image reviewer checks each sheet:
   - every view shows the same object;
   - the object matches concept B;
   - nothing extra is in the frame;
   - its state is right.

   Sheets that fail are regenerated. The reviewer has no round limit for art (Andrew, 2026-11-07).
4. **Group small items.** Small objects can share a sheet with one item per cell. Each cell is cut out before generation.

**Prompting lessons from the concepts:**
- Name what the object is and isn't.
- Describe the wanted object directly. Naming an unwanted thing (for example "no keyboard") tended to add it.
- Expect glass slits that read as windows, and reject them.

**Tooling** in `tools/art/`:
- `contact_sheet.py`, which runs generation, crops and the sheet layout;
- a prompt file per prop;
- provenance recorded in `docs/art/quarters/README.md`.

## Stage 2: meshes (unaged)

This stage follows the skill's stages 3 to 8 for each prop:
1. **Generate.** Run Hunyuan3D-2mv (full model, octree 320) on the hero view alone and on the four views together. Keep whichever the reviewer and the mesh checks rate better.
2. **Split and pick.** Split the result into connected components and choose the parts.
3. **Fit clean surfaces.** Fit clean surfaces over the generated shape: sparse cages, then fair, then subdivide. Make real separate parts along the inventory's split lines. Doors and drawers get their own pivots.
   - **Soft goods** (mattress, cushions, pillows, quilt, garments) are fitted as their own closed volumes, not fused to their frames, because stage 3 deforms them separately.
4. **Scale.** Scale to the inventory targets and to `layout.json`. Check that each prop sits on the floor or its wall with no gaps or overlaps.
5. **UV-unwrap and set materials.**
   - Every surface gets a UV layout at a consistent texel density, because the aging masks live in UV space.
   - Every surface gets a named material class from this list: PaintedSteel, BareSteel, Aluminium, Brass, HardPlastic, Ceramic, Glass, Display, Foam, NaturalFabric, SyntheticFabric, Leather, Rubber.
6. **Textures.** Use the hatch method.
   - **Metal:** bake ambient occlusion, curvature, coverage and weather masks into a per-prop atlas, then shade with `weathered_steel.gdshader` over the existing steel scans.
   - **Concept colour:** where a prop needs concept colour (painted panels, the console face), generate shadowless paint images and pack them the way `prepare_hatch_paint.py` does.
   - **Non-metal classes:** fabric, leather, ceramic, plastic and the photo get the same mask atlas and their own small shaders or materials.
   - **Glass:** every pane uses the pod glass shader.
   - **Hunyuan's texture painter** (`paint.py`) is a fallback only, if a prop's colour can't be covered this way.
7. **Export.** Export with a build script and the editable `.blend` in `tools/blender/quarters/<prop>/`. The export must be byte-reproducible.
8. **Check.** Run the skill's geometry checks: winding, manifoldness, self-intersection, triangle count. Render from fixed cameras, and have the reviewer compare against the contact sheet and concept B.

**Budget.** Set a runtime triangle budget for the room against the perf policy before stage 2 starts. The pod room's 20,000-triangle cap per asset type is a starting point. Small items get small budgets, and engine LODs are used where measured error stays under 1 mm.

## Stage 3: aging toolkit

These are reusable tools, not one-off edits. They run headless (Blender `bpy` plus NumPy/PIL), are seeded and versioned, and take a per-prop parameter file. They read an unaged GLB plus its `.blend` and write the aged GLB with the same origin, pivots and part names.

**Masks, baked per mesh in UV space:**

| Mask | What it marks | What uses it |
| --- | --- | --- |
| Edge curvature | Outer edges | Paint chips and rust |
| Cavity / ambient occlusion | Recesses | Where rust and grime collect |
| Up-facing exposure | Upward faces | Dust settles there |
| Gravity streak fields | Below fasteners, edges and holes | Rust runs down from them |
| Contact | Where parts touch | Staining and corrosion at joints |

**Material transforms**, one per material class, driven by the masks and the age (ruling 25). For metal this is not new work: `weathered_steel.gdshader` already does the flaking, oxide and streaks. The toolkit adds the "as built" end of its range, and the remembered state uses it.

| Material class | Change after 1000 years |
| --- | --- |
| PaintedSteel | Paint flakes off (noise × edge × age), revealing rust underneath, with streaks and blistering |
| BareSteel | Rust |
| Aluminium | Dull white pitting |
| Brass | Brown-green patina |
| HardPlastic | Yellowing and crazing |
| Ceramic | Stain rings |
| Glass | Dust haze |
| Display, dead | Black, with a crack overlay |
| Display, console | Unchanged |
| NaturalFabric | Fade, yellow-brown shift, then brittle tears and holes |
| SyntheticFabric | Fade and stiffening |
| Leather | Cracks and curl |
| Rubber | Hardened and cracked |
| Foam | Gone to crust (see geometry) |

All of these also get matching roughness and normal changes.

**Geometry transforms:**
- **Foam collapse.** Mattress and cushions sink onto their supports to about a quarter to a third of their volume. The surface breaks into cracked plates and crumbs, and the cover drapes over the crust.
- **Cloth decay.**
  - Shift the drape under gravity with Blender cloth simulation, on the generated garment mesh.
  - Cut holes and tears from the fabric mask and fray their edges.
  - Split hanging garments at the shoulders and slump them off the hanger. The cut, collar and insignia must still be recognisable.
- **Leather curl.** Boots curl and crack with bend deformers.
- **Debris.** Fibre and dust heaps go under garments and paint flakes under rusted surfaces. They are scattered as instances of a few generated debris pieces.
- **Dust.** Dust is mostly texture, plus a thin shell only where heaps need volume.

**The room shell** uses the same shader as every other ship shell. For the remembered state, its "as built" setting is the shader with paint intact and no oxide. That gives one shared look with the corridors and needs no separate clean wall set.

**Checks for each aged prop:**
- Measured numbers:
  - foam volume ratio within its band;
  - share of each surface flaked or rusted;
  - pixel-hue gate: no green or mould-coloured regions, since nothing biological grows;
  - pivots and footprints identical to the unaged prop.
- Image reviewer: renders from the same cameras, unaged beside aged, against the concept's present-day image and the ruling 25 aging rules.

## Stage 4: room assembly and the two states

1. **Build the room shell.** Build it at the agreed location from `layout.json`, with the clean and aged surface sets.
2. **Place the props.** Place every prop twice under two roots, Remembered and Present, sharing one set of transforms. The transition hides one root and shows the other in the same frame.
3. **Light both states.**
   - **Remembered:** warm and bright, with the bedside lamps on.
   - **Present:** secondary-power white from the regular ceiling fixtures, with the bedside lamps dead.
   - **Console:** lit in both. The quarters get their own reflection probe and render-layer setup, so their lighting stays off the rest of the ship.
4. **Add colliders and interactions.**
   - Colliders cover the furniture.
   - The console is the video-message trigger.
   - The badge sits somewhere in the room.
   - Entry follows puzzle-progression P03: a manual release or the local circuit, never the badge inside.

   These are gameplay slices (puzzle progression "Slice B") with their own issues.
5. **Verify.**
   - Doorway captures in both states, matched to the concept camera, reviewed against `concept-pair.png`.
   - Perf runs under the unchanged policy.
   - The unit suite and harness scenarios.

## Order and issues

Each step gets its own issue under #95 and goes to PRs on issue branches.

1. Stage 0 layout and plan view. Andrew approves.
2. Contact-sheet tool, plus pilot sheets for the locker module, sofa and uniform.
3. Pilot meshes through stage 2, with hatch-method masks and the "as built" end of the weathered-steel range. This step waits for the branch-1 steel and hatch work to merge.
4. Aging toolkit v1 on the three pilot props.
5. Pilot review with Andrew: unaged and aged, side by side in the doorway capture.
6. Remaining inventory in batches, by material class: hard steel, then soft goods, then garments and small items.
7. Room shell, clean and aged surface sets, and assembly in both states.
8. Gameplay slice (entry, console video, badge) with the puzzle-progression work.
9. Update the `concept-to-3d-asset` skill with the hatch texture method, contact sheets and aging lessons.

## Risks

- **Views that disagree.** Multi-view sheets that disagree can damage meshes; the Battlestar ships melted this way. The single hero view is the fallback, and the reviewer checks agreement before Hunyuan runs.
- **Thin and soft shapes.** Hunyuan does worst on thin and soft things: garments, quilts, plates. Generating each in its final pose and fitting it as its own closed volume keeps it usable, and cloth simulation does the rest.
- **"As built" steel.** The weathered-steel shader was tuned for old, worn surfaces. Its clean end is new territory, and the pilot checks it against the remembered concept.
- **GPU contention.** Other sessions share the GPU, so long jobs queue one at a time, and performance runs wait for an idle machine.

## Open questions for Andrew

1. **Location:** D16, or another deck once the deck plan is set?
