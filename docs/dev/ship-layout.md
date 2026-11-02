# Ship sections, connectors and ladders

## Recommendation and scope

Keep the opening's authored bay in a local frame, give the playable ship one pure layout model, and move all door progress into a shared simulation module. Build D14's three sections and two connectors, then stream connector presentation around the player on D01 through D30. Collision and interaction state must exist independently of rendered nodes.

This is an architecture and implementation contract, not a claim that the feature is built or tested. Implementation starts from `main`. The inspected `art-corridor-hatches` checkout supplies the art references. No game code changes accompany this document.

The 21 decisions in `tmp/connectors/build-brief.md` govern this feature. In particular, all four internal D14 hatches open by cranking, regardless of the older map's rust mark at X=0; other-deck hatches never open. The map's example D13 opening and four side-door stations in neighboring sections are superseded by the brief's closed other-deck hatches and three stations. Do not import additional rooms, radiation, atlas trunks, powered lifts, card readers, or story revelations.

References are `docs/art/corridors/README.md`, `d14-local-plan.png`, `connector-section.png`, their metric source `build-connector-maps.py`, and `docs/art/ship/3d/ship_atlas.json`. The map builder establishes the quarter-turn and aft ladder clearance used below. This design uses the source geometry and accompanying text; it does not claim an independent visual inspection of the PNGs. The atlas supplies axes and deck datums, not a runtime level or confirmed exterior sensor data.

## Implementation status: S01 through S08

`ShipLayout` defines validated records, stable ids, explicit unbuilt endpoints and the approved coordinate frames. `ShipGeometry` and `PodGeometry` own the shared pure solid recipes; `ShipCollision` preserves the opening's original collider insertion order and provides lazy, deck-local layout fixtures. `ShipScene` supplies structural construction to both entrypoints. The harness retains its existing omission of production wires, smoke symptoms and voice.

Production and the harness now place all bay furnishings under one `BayRoot` and use world-space capsules from the transformed exit path. Smoke samples in the inverse bay frame; a finite accepted-motion portal crossing latches the voice event. The hall switch uses the layout anchor, the power room remains fixed, and section 41 now meets wheel hatches at X=6 and X=30. The shared power-room wall has one owner through X=33.2.

`HarnessRoute` replays the five opening schedules through Player. The three bay-only schedules retain their relative input deltas; hallway and power-room tails are regenerated through layout anchors. Built documentation coordinates are exported by `tools/export_ship_layout.gd`.

`GameStep` now owns logical advancement in production, the harness and route replay. Capture pauses stop movement, doors, attention and fixture fades together. Wake completion belongs to the logical tick at 282; WakePresent retains the presented-frame readiness barrier and camera/pass projection. `Interactions` registers the opening's five proximity targets and layout door faces, selects once after accepted movement, and dispatches at most one actionable edge.

`Doors.Store` owns all door progress and exposes copied snapshots and independent read-only event batches. Both existing doors use its original 48-tick recipes. Crank fixtures use versioned UTF-8 FNV-1a, xorshift32 with zero seed replacement `0x6d2b79f5`, integer-weight schedules, six-tick wheel interpolation and a 48-tick smoothstep swing. The optional second stalled slot uses one modulo draw over N-2 slots, skipping the first stalled index. Refusals retain zero work; plain existing hallway leaves shudder through DoorView adapters. Door face normals point into their source spaces. Swing and parked-leaf collision now run in production's D14 collider set. D14 sections 40 and 42, both connectors and short well landings now use the shared geometry recipes. The four internal hatches crank open; side doors, lifts and far boundary hatches refuse. Closed section-facing hatch views exist at startup. Entering the last four meters of section 41 prepares the adjacent connector and outer section before exposure. New rooms hold steady red with separate light masks, and WALK stops at the supported landing edge without a shaft collider. Navigation factories now generate boxed octal deck/section identifiers and quantity-preserving Spanish. D14 hatch faces and lift fronts use shared immutable raster pairs, independent blend materials and spatially indexed attention with shared first-resolution memory. The console consumes the same cache while retaining its existing text, timing and physical-only behavior. Full-deck streaming, ladders and hatch audio remain in later slices.

## 1. Existing contracts to preserve

`Game` is a RefCounted composition object. `PlayerMotion` wires `Exit.GetUpController` and `Walk.WalkState`; `Resolve` sweeps conservative capsule bounds through `ColliderSet`. `Player` projects the result onto a camera rig. The project runs physics at 60 Hz. Preserve typed simulation Results, rejection without mutation, the first-error latch, and deterministic collider insertion order. A malformed authored layout or an obstructed authored ladder transfer is an error, not an invitation to teleport or ignore collisions.

The current coupling matters:

- `Game._init()` constructs the frozen pod registry, the collider set through `ShipCollision.opening_set`, and an exit path through `PlacementTruth`. The pure opening recipe replaces the bay's +X wall with the hallway pierce and extends the set with the power room. `Hallway` and `PowerRoom` retain presentation-facing recipe adapters.
- `PlayerMotion` owns two independent door enums, clocks and offsets, and five separate interaction methods. `Player._physics_process()` calls rod, bay door, switch, power door and console in that order. These methods use planar distance, not facing, and consume an edge only when they act.
- The bay door retracts for 12 ticks and slides for 36; the power door slides for 48. Passage opens at animation completion. Keep these timings and the opening route's action semantics.
- `SmokeSymptoms.exposure_at` assumes the old bay's world axes. `VoicePresentation` detects the old X=6 crossing in render polling. `Lighting.fixture_transforms` infers wall sides from pod-local Z. Merely transforming pod centers would break these consumers.
- `ShipDisplay` owns two 1024 by 640 SubViewports per screen. That is acceptable for the single console today, not for hundreds of signs. `DisplayPerception.Memory` is already shared through `Game.writing_memory`.
- `app/main.gd` and `app/harness_mode.gd` assemble their own scenes. The latter also has its own wake clock. It currently omits production wires, smoke symptoms and voice. Scene geometry and logical tick ownership must converge before connector evidence can be trusted.

The opening still runs pod, deliberate rod pickup, rod-pried bay door, hall switch, ungated power door and two console presses. Wake remains 282 ticks with its readiness barrier. The bay remains red after backup activation; the existing hall and power room still change from steady red to dim white.

## 2. Layout and ownership

### 2.1 One authored layout module

Add `sim/ship_layout.gd`, `class_name ShipLayout`, extending RefCounted. It contains typed nested records and the authored construction recipe. It has no dependency on `app/`, Nodes, textures, fonts, audio or the planning JSON. Existing pure pod dimensions and local pod placements stay in `sim/pods.gd`; ShipLayout references that one bay template rather than copying seven coordinates. Move the rod placement out of `Rod` into this layout's bay-local anchors.

The public shape is:

```gdscript
static func authored() -> ShipLayout.Result
func deck(number: int) -> ShipLayout.DeckSpec
func section(id: StringName) -> ShipLayout.SectionSpec
func connector(id: StringName) -> ShipLayout.ConnectorSpec
func door(id: StringName) -> ShipLayout.DoorSpec
func face(id: StringName) -> ShipLayout.FaceSpec
func well(id: StringName) -> ShipLayout.LadderWellSpec
func anchor(id: StringName) -> Transform3D
func bay_to_world() -> Transform3D
func world_to_bay() -> Transform3D
func floor_y(deck_number: int) -> float
```

`Result` carries either a layout or a `LayoutError` with kind and offending id. Construction checks finite dimensions, valid decks, unique ids, reciprocal portal faces, existing references, nonoverlapping apertures, exactly one bay and power room, and the specified openability set. Accessors assert on unknown ids. Return copies of mutable collections; callers never mutate layout records. GDScript does not enforce immutable objects, so keep stored fields private and expose read-only access methods.

Records and responsibilities:

| Record | Required data |
| --- | --- |
| `DeckSpec` | Integer 1..30, derived floor Y, connector ids and built section ids. |
| `SectionSpec` | Stable id, deck, section number, derived bounds, ordered wall openings and side-door ids, lighting circuit. |
| `ConnectorSpec` | Stable id, deck, pitch index n, derived bounds, fore/aft hatch ids, well id, lift id, port opening and shared-wall ownership. |
| `DoorSpec` | Id, deck, kind, policy, portal frame, aperture dimensions, two endpoint spaces, face ids, animation recipe, wheel presence, closed blocker specification. |
| `FaceSpec` | Id, door id, source space, destination section number, local surface frame and interaction frame relative to its door. |
| `LiftSpec` | Id, connector id, door id, starboard footprint and landing label anchor. No operational car or lift controller. |
| `LadderWellSpec` | Id independent of deck, bounds, climb line, D01/D30 limits, per-deck landing and transfer paths, continuous shaft clearance. |
| `BaySpec` | Id, D14 and section 41, one rigid transform, reference to the frozen bay template, local rod/hatch/smoke anchors. |
| `PowerRoomSpec` | Id, D14 and section 41, unchanged footprint, door, six console station transforms and generator anchor. |

All placement choices belong to ShipLayout or a referenced local template. Mesh detail dimensions remain with their mesh builders. A knob used by collision and rendering, such as aperture width or wall thickness, belongs to pure placement data, not a second render constant.

### 2.2 Exact playable geometry

Use meters, +Y up, bow -X, stern +X, port -Z and starboard +Z. `floor_y(d) = (14 - d) * 5.5`; D01 is 71.5, D14 is 0 and D30 is -88.0. Clear height is 3.2. The distance between endpoint floors is 159.5 m.

A section for pitch index n spans `[30n+6, 30n+30]` along X, with number `n+41`. A connector spans `[30n, 30n+6]`, between sections `n+40` and `n+41`. Both have corridor interior Z=-1.5..1.5.

| Built space | X interval | Notes |
| --- | --- | --- |
| D14 section 40 | -24..0 | Three side-door stations at offsets 3, 9, 15 on each wall; all shut. |
| Fore connector, n=0 | 0..6 | Present on every deck. |
| D14 section 41 | 6..30 | Existing hall; bay replaces X=15 starboard leaf; power door stays at X=27 port. |
| Aft connector, n=1 | 30..36 | Present on every deck. |
| D14 section 42 | 36..60 | Same six shut side doors as section 40. |

Keep five never-opening side leaves in section 41, six each in sections 40 and 42, plus the bay and power doors. There are 17 never-opening side doors, 60 lift doors, 120 connector hatches and two D14 boundary hatches. The bay hatch is an additional existing door with its rod policy. Every door has one simulation record, even if both faces are rendered.

Stable ids use structural indices, not rounded coordinates or scene paths:

- `D14-S-041`, `D14-C-000`, `D14-C-001`.
- `D14-C-000-H-FORE` at X=0 and `D14-C-000-H-AFT` at X=6; the analogous n=1 ids at X=30 and 36.
- `D14-C-M001-H-AFT` at X=-24 and `D14-C-002-H-FORE` at X=60. Their connector endpoints are explicitly unbuilt boundary records, not missing lookup references.
- `D14-S-041-SIDE-009-PORT`, with 009 denoting the station offset within the section, not world X. A side id retains its identity if a section moves.
- `D14-BAY-DOOR`, `D14-POWER-DOOR`, `D14-BAY`, `D14-POWER`, `D14-HALL-SWITCH`, `D14-BAY-ROD`, `D14-POWER-CONSOLE`.
- `C-000-LADDER`, `C-001-LADDER`; `D14-C-001-LIFT`; face suffixes `/FORE`, `/AFT` or `/BAY`, `/HALL` as appropriate.

At each deck, fore well interior is X=2.15..3.85, Z=-5.8..-1.5. Aft well is X=33.65..35.35, same Z. Port openings are 1.3 m wide, centered at X=3 and 34.5, and 2.4 m high. The aft well clears the unchanged power room ending at X=33, including its 0.2 m wall. Lift faces center at X=3 and 33, Z=1.5, width 1.8; the planning footprint extends 3 m starboard. Only the shut lift front and enclosing shell need rendering. No hidden playable lift room is promised.

Use the existing 1.2 by 2.4 m hatch aperture and 0.2 m wall thickness for connector hatches. Generate wall intervals around apertures, then frame, leaf and blocker from the same portal record. Walls shared by a room and connector have one owner and one set of solids. In particular, remove the old X=6 bay wall assembly and X=30 endcap; do not leave overlapping slabs behind new hatches. PowerRoom's south-wall tiling currently depends on `Hallway.HALL_END_X`; replace that dependency with the shared boundary intervals through X=33, so extending the hall does not duplicate this wall.

### 2.3 Geometry, collision and consumers

Add `sim/ship_geometry.gd`, `class_name ShipGeometry`, for pure `SolidSpec` generation and portal splitting. Extract the reusable box placement and rotated-eight-corner AABB conversion from `app/placement.gd` into this module. `SolidSpec` carries id, transform, full size, material role and collision role. Add `sim/pod_geometry.gd`, `class_name PodGeometry`, for the existing pod collision solids and tray-floor dimensions currently owned by PodBody; PodBody and ShipCollision both consume it. Mesh-only dressing stays outside collision. Keep `Placement` as the bay-local furnishing recipe, consuming the pure solid type; do not make the simulation import `Placement`, `PodBody`, Hallway or PowerRoom.

Add `sim/ship_collision.gd`, `class_name ShipCollision`, which owns cached per-deck static sets and per-door blockers. It consumes layout, pure solid recipes and door snapshots, never scene visibility. Static solids are ordered by owner id and local piece index. Door-open completion increments a deck revision and rebuilds that deck's assembled set once. Never rebuild all decks on a wheel press. Preserve ColliderSet's inclusive queries and Resolve's tie-breaking order. Keep the linear query until measurements justify another broad phase.

`app/ship_scene.gd` (`ShipScene`) is the common scene composition root used by main and the harness. It creates a `BayRoot`, Hallway/PowerRoom adapters and a `ShipStream` presenter. `app/section.gd` (`ShipSection`) and `app/connector.gd` (`ShipConnector`) build repeated geometry from specs. Hallway retains section 41's switch, lighting and ceiling dressing, not a parallel corridor topology. PowerRoom retains console and generator presentation, not global collider assembly. `app/hatch.gd` retains the bay's mesh style; `app/door_view.gd` (`DoorView`) projects all registered door snapshots.

`Game` owns `layout`, `doors`, `collision` and the run seed. Construct it as `Game.new(seed)` with an explicit integer: the production root chooses and logs one seed at startup; the harness passes scenario.seed; tests supply a constant. Neither Store nor a scene builder calls randomize or reads a clock. `PlacementTruth.player_exit_path(layout)` and new `PlacementTruth.anchor(layout, id)` derive gameplay and harness expectations from these records. Harness scripts refer to ids and local route offsets. No scenario generator may embed its own doorway X/Z. Independent numeric tests still pin the required layout coordinates so a wrong producer and consumer cannot agree undetected.

The planning atlas is not read by the game. During the bay-move slice, add `tools/export_ship_layout.gd` to export the built subset as JSON. Update the atlas's built records and the map builder to consume that export, retaining proposed facilities and provenance separately. Change `docs/art/ship/3d/validate_atlas.gd` to compare built records against the exported layout. The export is derived documentation data, not another editable source of runtime coordinates. Do not promote the atlas's hypothetical spines or remote pods into this feature.

## 3. Move the bay once

### 3.1 Frame contract

Choose a bay-local frame over rewriting every pod, wire, light and get-up coordinate. The exact transform is:

```text
T(x, y, z) = (15 + z, y, 7.7 - x)
T.basis = Basis(Vector3(0,0,-1), Vector3.UP, Vector3(1,0,0))
T.origin = Vector3(15,0,7.7)
```

The columns are exact cardinal vectors, avoiding tiny cosine residue in rotated AABBs. It is a positive quarter-turn about +Y. Bay footprint becomes X=11..19, Z=1.7..13.7. Player pod 6 becomes (17.9, 0, 12.5); rod floor center becomes (13.45, 0, 8.3). Relative distances, pod mouths, aisle clearance, camera orientation, eye height and smoke density stay unchanged.

The old local hatch's inner threshold `(6,0,0)` maps to `(15,0,1.7)`. The required hallway door station is `(15,0,1.5)`, on the opposite face of the same 0.2 m wall band. These are two faces of one portal, not inconsistent transforms. Store the portal at the hall face and derive the bay face by wall thickness. Preserve the bay's recessed ajar mesh and its local frame behind that face; do not move the entire bay another 0.2 m to align its interior threshold with the hall face. Pierced slabs, sill and passage floor must bridge the entire band.

The switch is a hall-owned anchor at `(16.2,1.25,1.45)`, with its plate rotated onto the starboard wall and outward normal -Z. It is right of the opening when looking back at the bay door from the hall, matching the spoken doorway reference. The power room remains X=21..33, Z=-9.7..-1.7, door `(27,0,-1.5)`, console act center `(22.05,0,-7.5)`.

### 3.2 Where conversion occurs

Keep `Pods.PodRegistry.frozen()` explicitly bay-local. Rename its hatch accessor to make local semantics explicit, or remove runtime hatch lookup in favor of the layout portal; no API should silently return local coordinates as world coordinates. `Game.registry` remains the local pod registry used by bay builders. `BayRoot.transform = T`; room shell, pods, hatch, fixtures, rod, hazards, pod strips and wires remain children with their old local placements. Keep the single WorldEnvironment at the scene root.

Simulation uses world-space capsules everywhere. Construct the get-up path in bay-local space using the original pod/tray recipe, then transform every pose's endpoints and pivot data once into world space. Add an explicit rigid transformation method to `Exit.ExitPath`; do not reconstruct a five-pose path from world endpoints and lose its segment/pivot information. Move the shared tray-floor height out of presentation ownership into the pure pod geometry specification, with PodBody consuming it. The `Wake` timeline and its sway/blur/exposure samples do not change. `Player` adds T's yaw to its local spawn yaw; it remains outside BayRoot because it must leave the bay.

ShipCollision transforms each local bay solid before generating its world AABB. Do not transform an already expanded AABB and expand it again. Door offsets are expressed in their animation frame: the bay's old `(retract,0,-slide)` vector passes through T.basis exactly once. A child of BayRoot uses the local offset directly; DoorView never applies both conversions.

`SmokeSymptoms` receives the bay volume specification and T inverse at construction, and converts the world eye before evaluating the current local taper. Keep full dose inside through local X=5.5, taper to zero at X=6, Y=0..3.2 and |Z|<=4. Add the missing lower-X extent at -6 from the bay bounds: it was unreachable before, but an unbounded half-space must not become ship-wide smoke now. Dose rise/recovery, event timing, audio queue and shader equations stay unchanged. Test the old interior profile unchanged and add outside-volume/other-deck zeros.

Replace render-polled X crossing with `sim/portal_crossing.gd` (`PortalCrossing`). Given previous and accepted current foot positions and a portal, it tests oriented signed-plane crossing, intersection within the aperture, correct source side, deck, locomotion permission and open passage. Bay exit is crossing the hall face toward -Z. `Game` latches this event once; `VoicePresentation` reads it and retains its noninterrupting playback and one-second switch delay. Returning to the bay never retriggers line 2. Crossing the infinite plane elsewhere does nothing. No new audio recording is needed for the existing lines.

### 3.3 Bay migration impact inventory

| Area | Files and checks |
| --- | --- |
| Composition and coordinate boundaries | `app/main.gd`, `game.gd`, `player.gd`, `motion.gd`, `harness_mode.gd`, new ShipScene; all entrypoints pass the layout. |
| Pure placements and motion | `sim/pods.gd`, `sim/exit.gd`, `app/placement.gd`, `placement_truth.gd`; keep local pod data and transform exit/collision once. `sim/walk.gd` and `resolve.gd` need translated/quarter-turn tests, not rewritten movement axes. |
| Bay rendering | `room_geometry.gd`, `pods.gd`, `pod_mesh.gd`, `pod_body.gd`, `pod_strips.gd`, `hatch.gd`, `rod.gd`, `hazards.gd`, `lighting.gd`, `wires.gd`; most receive the new parent, while world-query helpers take T explicitly. Verify particle bounds/local emission and strip look directions. |
| Hall and power boundaries | `hallway.gd`, `power_room.gd`, shared geometry/collision; replace east-wall shortcut, pierce X=15 starboard, rotate switch, preserve power geometry. Fix the stale right-hand comments in `game.gd` and `power_room.gd` using port/-Z wording. |
| Exposure, wake and voice | `sim/smoke_symptoms.gd`, `voice_presentation.gd`, `wake_present.gd`; keep `sim/wake.gd`, wake effects and smoke audio timings unchanged. |
| Captures and verification | `app/capture_gameplay.gd`, `capture_lit.gd`, `capture_smoke.gd`, `capture_wake.gd`, `harness/run.gd`, scenario route authoring and atlas export. Convert authored camera shots with the same frame. |
| Coordinate tests | `placement_test`, `pods_test`, `pod_mesh_test`, `pod_strips_test`, `wires_test`, `surfaces_test`, `hazards_test`, `lighting_test`, `exit_test`, `player_test`, `input_fixes_test`, `hallway_test`, `rod_test`, `power_room_test`, `smoke_symptoms_test`, `smoke_vision_test`, `wake_present_test`, `voice_presentation_test`, `harness_test`. Keep local assertions and add world assertions where appropriate. |
| Unchanged mathematical contracts | `walk_test`, `resolve_test`, `colliders_test`, `wake_test`, `phase_test`, `controller_test`, `intensity_test`, `power_test`; retain every existing case and add transformed/deck fixtures rather than replacing their original mathematical cases. |
| Windowed integrations | `tests/main_audio_integration.gd`, `tests/voice_audio_integration.gd`, display scene checks; update setup positions, preserve SHA checks, completion latches, 282-tick gate and exact delay boundary. |

## 4. Door and interaction simulation

### 4.1 State, policy and effects

Add `sim/doors.gd`, `class_name Doors`, with a `Store` keyed by layout door id. Door records own all progress and survive scene eviction. Use orthogonal policy and state rather than a special controller per doorway:

```gdscript
enum Policy { CRANK, NEVER_OPENS, ROD_PRY, PRESS_SLIDE }
enum State { CLOSED, CRANKING, OPENING, OPEN }
func press(id: StringName, context: Doors.Context) -> Doors.PressResult
func tick() -> Array[Doors.Event]
func snapshot(id: StringName) -> Doors.Snapshot
```

`Context` contains carried-rod capability, not Nodes. Reach and facing are selected before this call. `PressResult` distinguishes `NOT_APPLICABLE`, `MOVED`, `STALLED`, `RELEASED` and `REFUSED`; accepted outcomes consume exactly one edge. Unknown ids or illegal authored policy/animation combinations are errors. `NEVER_OPENS` remains CLOSED, has zero persistent wheel progress and no collider transition. `OPENING` is required to distinguish a released mechanism from a traversable passage.

Unify now: store, clocks, blocker transitions, interaction registration, events and DoorView projection for connector hatches, side leaves, lift doors, bay hatch and power door. Keep the bay's rod gate, ajar starting mesh and retract/slide recipe; keep the power door's ungated one-press slide. The console's STANDBY/INACTIVE/ACTIVE and lighting circuits remain Game behavior. Rod inventory and switch state remain simple interaction handlers, not door policies. Do not add powered/card-reader mechanics or a general quest framework.

Remove `DoorState`, `PowerDoorState`, elapsed counters and `_tick_door/_tick_power_door` from PlayerMotion after migration. Replace writable `Game.door_open` and `power_door_open` with derived queries of the two ids. Existing named harness events can remain report adapters over those queries; no duplicate gameplay booleans remain. Door counts come from the Store. Game commits collider revisions when Store emits `OPENED`, before the next movement sweep.

### 4.2 Deterministic crank resistance

Add `sim/hatch_resistance.gd`, `class_name HatchResistance`. Use a specified byte-based 32-bit hash and PRNG, not String.hash, randomized engine seeds or a shared RNG consumed by rendering. Hash UTF-8 `hatch-v1|<signed decimal run seed>|<door id>` with FNV-1a, masking to 32 bits per byte. A local xorshift32 stream advances with shifts 13, 17, 5 and masks each step; replace the forbidden zero PRNG state with the fixed nonzero seed constant during construction. This is part of the algorithm, not recovery from invalid input. Pin seed/hash/output vectors in tests.

Build one finite resistance schedule per CRANK door. Draw an integer category in 0..99: 0..84 selects total attempts N uniformly from 5..10, 85..99 selects N from 11..16. Use modulo draws with their documented tiny bias rather than engine RNG behavior. Choose one stalled slot uniformly among attempts 1..N-1; choose one additional distinct stalled slot when the next draw modulo 4 is zero. The last attempt always moves. Give every moving slot an integer weight 1..5.

Persistent wheel progress is integer work units. Target angle is 270 degrees. At attempt k the target angle is `270 * accumulated_weight / total_weight`; a stalled press adds zero. Therefore every schedule opens exactly on N, includes at least one zero-progress press and varies movement amount. Attempts count only when a selected in-reach face receives a fresh press. Both faces share the same counter and schedule; leaving and returning, streaming, another hatch's use and frame rate do not change it. Test category/attempt bounds on a fixed large seed corpus and exact short fixtures; do not introduce probabilistic flaky tests.

Keep the physical wheel's displayed angle in the simulation snapshot. A moving press sets a new target; interpolate from the current displayed angle to that target over six logical ticks. A new edge during that interpolation retargets from the current displayed angle, without discarding progress. Final release starts OPENING only once the final wheel interpolation reaches 270 degrees. No hand animation. Emit the heavy release event at that boundary, once.

### 4.3 Opening and refusal presentation

New hatches rotate about a vertical jamb hinge for 48 ticks from closed to 90 degrees, with a deterministic smoothstep fraction. The layout fixes hinge side and swing direction into the connector, independent of the face used. Closed and opening collision includes the conservative swept envelope of the leaf, derived from its hinge and dimensions, in addition to the aperture blocker. This reserves clearance before the first press, so starting the animation cannot create a blocker around the player. It deliberately makes collision near a closed leaf conservative, consistent with the existing AABB resolver; test that both wheel faces remain reachable within 2.2 m. Do not fill this temporary swing envelope with permanent wall geometry. Once OPEN, remove the passage and swept-envelope blockers and retain only the leaf's final parked collider and fixed frame. Test that the aperture admits the capsule from both directions, the parked leaf cannot be walked through, and the swing envelope does not intersect the ladder transfer path.

A refusal animates a wheel jerk to 4 degrees relative to its resting angle in three ticks and back in six. A repeated press restarts from the current visual offset toward that same bounded peak; it never accumulates work. Plain side/lift doors have no wheel movement and play a thud. A stalled but openable crank uses the short jerk and strained clunk too; its previous persistent progress is retained.

Events have monotonic sequence, logical tick, door id, face id, attempt index, outcome, angle delta and audio variant index. Render and audio use their own cursors over the current tick's immutable event batch. A renderer must not drain events before the audio observer or harness sees them. Game retains snapshots and counters, not an unbounded event history.

### 4.4 One selection path, with existing behavior preserved

Add `app/interactions.gd`, `class_name Interactions`, a pure coordinator with typed `Target` data and one dispatcher by target kind: pickup, door, switch, console, ladder. Register all targets from layout ids. Adding a new hatch is a new record, not a new branch in Player or PlayerMotion.

For new door faces and ladders: require same deck/landing, WALK mode, within 2.2 m planar reach, eye within the target's vertical interaction band, camera forward hitting the face rectangle with a 0.20 m margin, and no static-solid occlusion before the hit. Use pure segment/AABB intersection with stable hit ordering; no physics-engine raycast. The face owns its normal and frame. Rank eligible targets by ray-hit distance, then id. Being close on D13 must never select a D14 door.

Preserve the old opening targets' planar eligibility and relative priority as a declared `LEGACY_PROXIMITY` selection policy: rod, bay door, switch, power door, console. A facing-selected door face takes precedence over proximity-only targets. The power door's reach overlaps the X=30 hatch approach, so proximity must not redirect a press away from that hatch. A rodless bay-door press remains not applicable and can reach the switch, as `hallway_test` requires. New `NEVER_OPENS` targets consume a press for refusal. The existing opening targets retain their proximity eligibility; migrating them to require facing would be a separate behavior change.

Player calls `interactions.process(plane, context)` once. The interaction coordinator filters and selects before consuming INTERACT, then calls the appropriate state owner. Take at most one actionable INTERACT per logical tick. Old unhandled input still expires at `end_frame`; a press cannot pick up a rod and crank a door in the same tick.

## 5. Deck-aware walking and ladders

### 5.1 Position and mode

Keep `Resolve.Capsule` endpoints in world meters. Add `sim/locomotion.gd`, `class_name Locomotion`, owning a tagged state: `WALK` has a deck id and WalkState; `MOUNTING`, `CLIMBING`, `DISMOUNTING` have a `Ladder.State` and well id. `PlayerMotion` retains LYING/GET_UP and delegates its standing locomotion to this object. Phase remains STANDING while climbing; a second global phase machine is unnecessary.

There is no continuously guessed deck during a climb. WALK's deck changes only after a successful landing transfer. Climb reports well id, continuous height and nearest landing for presentation; the nearest landing is not permission to walk. Collision selection uses the swept capsule's vertical interval, not a rounded deck number.

`Walk.WalkState` already preserves arbitrary foot.y. Keep its resolver, ramp and input validation. Add a validated resume/transfer method so returning from the ladder installs the swept landing capsule without restarting the opening's steadying ramp. Preserve the elapsed ramp value while climbing; never mutate its private capsule from an app script.

### 5.2 Well geometry and safe landing path

Add `sim/ladder.gd`, `class_name Ladder`. Each well has a front landing floor at each deck, Z=-1.5..-3.3, with the continuous shaft behind it, Z=-3.3..-5.8. The climb capsule axis is at the well center X and Z=-4.3; visible ladder rails/rungs sit behind that axis, outside the capsule. Landing floor and ceiling pieces end before the climb lane, so neither deck floors nor the 3.2 m connector ceiling span the shaft. Shaft wall sections cover the full 5.5 m pitch, not just the room clear height. Top and bottom have visible end closures outside the capsule endpoint envelope.

The approach anchor is on the landing at Z=-2.9, with a 0.305 m minimum capsule-center margin from its exposed edge. Mounting transfers along a straight swept line to Z=-4.3 at the same floor-relative height. The shaft opening is an intentional absence of support during this constrained transfer. No invisible floor may span it.

Walking has no falling model today. Add an explicit supported-walk-region constraint for these landing edges: only WALK displacement is clipped at the landing's capsule-inset boundary, keeping the capsule supported. This is a gameplay limit at a visible drop, not a fake collision solid also presented to Ladder. The landing/connector union has no seam barrier at the doorway. Mount/dismount sweeps use real solids and bypass only this mode-specific support boundary, never a real wall. Unit tests must prove walking cannot float over the shaft and a legal mount still crosses it. A gravity/fall system is out of scope.

### 5.3 Fixed-tick transitions

`Ladder.try_mount(layout, well_id, deck, capsule, facing)` validates the landing, reach and facing and yields a MOUNTING state. Mount uses a 24-tick swept interpolation to the climb axis from the accepted start pose; preserve head-to-foot offset. An obstruction of this authored path returns a typed error and leaves that tick's state unchanged. Do not snap to the destination or retry elsewhere.

In CLIMBING, forward/back intent becomes signed ascent/descent at 1.5 m/s, independent of camera yaw/pitch. Full input moves 0.025 m per tick. Store scalar climb height in GDScript's 64-bit float and construct the Vector3 capsule from it each tick, avoiding accumulated float32 vector error across 159.5 m. Resolve every vertical displacement against the shaft and overlapping landing slabs. The layout must provide clearance; unexpected contact shortfall beyond Resolve's existing tolerance is a `PATH_BLOCKED` error with collider id. Resolve currently ignores a displacement no larger than penetration tolerance: retain such pending scalar travel across ticks until a sweep can consume it, rather than losing low analog input or advancing the capsule without a sweep. Direction reversal updates that signed remainder. Bound the unswept remainder by the unchanged tolerance and cover it in tests. Clamp intended height to D01/D30 endpoints as the explicit movement rule, not as an error fallback. Holding outward at an endpoint moves zero and remains mounted.

Choose Space to dismount at a landing. It is valid within 0.15 m of a floor's standing foot height. Retain the last crossed landing id for one tick so a crossing cannot be missed by f32 conversion. Dismount sweeps a short vertical correction to exact landing height and then the reverse horizontal mount path over 24 ticks. Invalid midshaft presses do nothing and are dropped, not queued for the next landing. Strafe has no movement effect while mounted. A fresh Space is required after mounting to dismount; the mount edge cannot do both.

The dismount commits WALK and the new deck only after the final sweep. Each physics tick calls exactly one mode's step. At a landing the eye is `capsule.foot.y - radius + 1.6`, matching existing standing height including penetration tolerance; during climb it follows that same continuous expression. Mouse look remains available; no teleporting camera or forced head tilt. Door interaction is disabled while mounted, although nearby label attention remains possible.

### 5.4 Input compatibility

Today W/S are `look_up/look_down`, while arrows are movement. Keep that mapping on foot so keyboard-turn and pitch tests retain their behavior. Add dedicated `climb_up/climb_down` actions on W/S. In mounted modes, `Player._collect_device_input` routes W/S and up/down movement keys to a new single-consumption climb channel on InputPlane and suppresses W/S pitch; mouse pitch still works. Do not offer both W and Up as a speed multiplier. Values are combined and capped at one.

Scripted input gets `offer_climb`, `take_climb` and `ScriptedAdapter.climb`; add a `climb` action to HarnessScenario. For mounted movement-key compatibility, legacy negative simulation forward means physical forward/up; convert it once at the Locomotion boundary when no dedicated climb intent exists. Validate both sources and reject contradictory dual-channel scripted input rather than silently picking one. Tests pin the sign: device W and Up, scripted climb +1, and mounted simulation forward -1 all ascend. Existing on-foot simulation +Z forward semantics remain unchanged.

### 5.5 Collision partitions

ShipCollision lazily builds complete pure sets per deck, independently of ShipStream. WALK queries its deck; climb queries all deck slices intersecting the swept capsule bounds plus the well's continuous walls. This includes the adjacent floor before crossing it and catches ceilings with the head, not only the foot. Stable ids deduplicate shared slabs. No collision data is removed when a scene is freed. The endpoint closures and supported landing regions prevent escapes beyond D01/D30 without changing Resolve's general-purpose error rules.

## 6. Labels and perception

### 6.1 Meaning and face direction

Add catalog entries in `app/ship_text.gd` for `navigation.deck` = lometa / CUBIERTA, `navigation.section` = shelani paki / SECCIÓN, `navigation.lift` = kotewa / ASCENSOR and `navigation.hatch` = pana / ESCOTILLA. Keep console messages unchanged. Record `shelani paki` as a project compound, corridor 106 plus part 235, modifier before head, in `docs/design/language/nalesha-reference.md`'s addendum and `docs/design/decisions.md`. It adds no dictionary root. Also update the old geography decision with the new doorway orientation.

`ShipText.hatch_label(deck: int, section: int)` and `deck_label(deck: int)` return a typed `LabelText` containing native text and Spanish text. Values are positive integer identifiers, not strings supplied by callers. Convert to octal once with Naleya.octal; never pass decimal 14 to the octal-text renderer as the digits `14`. The D14/41 pair is native `lometa [16]\nshelani paki [51]`, perceived `CUBIERTA 14\nSECCIÓN 41`. Native [16] is read na wi, [51] chi na. Lift doors show only the deck line above the doors; they do not acquire an extra lift line or a ladder-doorway label.

A face names the section reached in its travel direction. Crossing into a connector names the section at its other end. This makes signs useful on both faces without inventing a section number for a connector:

| Hatch X | Looking/traveling +X | Looking/traveling -X |
| --- | --- | --- |
| -24 | 40 | 39 |
| 0 and 6 | 41 | 40 |
| 30 and 36 | 42 | 41 |
| 60 | 43 | 42 |

Use the same mapping on other decks although those destinations remain inaccessible. Both bay-hatch faces use section 41, which contains the bay and hall. The power room has a plain crew door, not a new hatch face label requirement. Face records exist even for the inaccessible reverse face of a boundary hatch; presentation only creates reachable surfaces, with tests for both data records. Author hatch sign quads as 0.92 by 0.46 m, centered 2.85 m above the deck, on each fixed frame face with 0.01 m outward surface offset. This clears the 2.4 m aperture and frame below the 3.2 m ceiling. Lift signs are 0.92 by 0.23 m, centered 2.55 m above the deck. These anchors and sizes live in FaceSpec/style data and supply both mesh placement and attention rectangles.

### 6.2 Boxed identifier geometry

Extend `Naleya.chunk_units/layout` to recognize `[0-7]+` as one boxed identifier token. Brackets are renderer markup and never font punctuation. Emit the existing digit glyph strokes plus one closed rectangular polyline around their ink bounds, padded 1 native unit beyond the ink edge, stroke width 0.72. Include the box's half-stroke extent in layout width and advance. Keep the whole box unbreakable and maintain the single +Y-up to canvas-down inversion. Reject unmatched/nested brackets, empty runs, words inside boxes and digits 8/9. Existing unboxed numbers, clock separators and word layouts retain their meaning. Box geometry and padding are renderer choices, not additional language rules.

### 6.3 Cached texture pairs and attention

Add `app/ship_text_cache.gd`, `class_name ShipTextCache`. It owns at most two reusable 2D raster SubViewports for all navigation text, each using ShipTextCanvas. A request key includes complete native/Spanish text, style id, texture size, layout version and font identity. A pair of completed `ImageTexture`s is immutable and shared by every face using that text. Never retain a ViewportTexture whose pixels will change when the next label is drawn.

Use a 1024 by 512 navigation style with equal-sized two-line text and a fixed sign quad; keep the existing 1024 by 640 console style and heading/state sizes. Generalize `ShipTextCanvas` to explicit lines/style rather than treating line two as an operating state. Capture textures after `frame_post_draw`, one unique pair per render frame, only on cache miss. Cache hits do no viewport work. Maintain reference counts and at most 32 unreferenced pairs in LRU order; evict only unreferenced pairs. Present scenes attach a label only after its pair is ready. They are prefetched before becoming visible, so no blank or Latin placeholder is accepted.

Add `app/ship_label.gd` (`ShipLabel`) for a quad, unique blend material, face id and DisplayPerception reference, without per-label viewports. Modify ShipDisplay to request its finite console text pairs from the same cache, preserving message reset, blank STANDBY and physical_only behavior. Prefetch both inactive and active console pairs on approaching the power doorway, before either console press can occur; a press changes the state and cached view in the same logical tick. Keep test-observable semantic text even though the canvas is no longer a child of each display. Sharing textures must never share the blend amount.

`app/label_attention.gd` (`LabelAttention`) owns per-face perception state and Game's shared first-resolution memory. Index faces by deck/space. Each logical tick considers only candidates within the existing 4 m range, front-facing and within the existing rectangle/margin test. Require unobstructed sight to the face using the same pure segment test as interaction; a label cannot resolve through a closed hatch. Keep a small decay set for labels just left behind and tick them false until perceive=0 after at most 21 ticks, then remove them. Eviction keeps that lightweight decay state; reloading the scene cannot skip decay or restore a stale Spanish blend. Sort candidates by face id so simultaneous first-resolution handling is repeatable.

The first hold/ramp remains 72/96 ticks, later 21/36, decay 21. Native physical textures never change as attention changes. The cache does not contain perception state. A completed reading of a hatch can establish shared memory before the console; this is the required shared-memory behavior, not a per-screen reset.

## 7. Rendering and frame-time control

Add `app/ship_stream.gd`, `class_name ShipStream`, a presentation-only residency manager. Do not instantiate 60 room trees and then hide them. Pure definitions and door states for all decks are cheap and always available; mesh trees, label textures and lights are demand-built.

Start with the same opening presentation: BayRoot, section 41 and PowerRoom. No other-deck rooms, sign rasterization jobs or connector lights run during the wake/opening capture window. The closed connector hatches can be represented by their section-facing boundary views until their interiors are needed. Begin preparing the adjacent connector and neighboring D14 section when the player enters the last 4 m of section 41 toward that end. The required meshes and initial sign pair must exist before a door's first opening animation can expose them. This is a measurable prefetch contract, not a gameplay lock tied to render speed.

Near a ladder or while mounted, keep the occupied connector's rooms for the nearest deck and two decks above/below, clipped to 1..30. Prewarm the next deck when entering the outer half-pitch of the resident band. The other well is not instantiated on remote decks. D14 opening can remain allocated but hidden and processing-disabled when remote; door and power state remain in Game. Re-entering D14 restores views from snapshots, not default states. At most five remote connector rooms are active for the occupied well, plus the small D14 scene set.

The continuous shaft must not expose holes when looking down 159.5 m. Use shared low-detail shell segments and one MultiMesh for rails/rungs spanning the full well, created when that well first becomes visible. Landing lips and door recess masks outside the room band remain cheap shell geometry. They are real geometry, not black fog caps that move with the player. Detailed connector rooms and labels are still limited to the resident band. No smoke is replicated outside the bay.

Use shared meshes/materials for repeated walls, frames and wheels; use MultiMesh only for static repeated rails/rungs and shell details. Doors and labels remain individual instances because they have independent transforms and blend state. No new renderer/framework is needed. Split construction into bounded queues with one room's geometry or one texture pair per frame; prewarm and assert residency in capture tests. Measure actual construction spikes instead of hiding them with a loading pause.

New sections, connector rooms and well landings use steady emergency red on their own emergency circuit, independent of `power_active`, as the bay does. Section 41 and PowerRoom retain their existing switch/red/white rules. Reuse Lighting's red energy, color, material and no-fog/black-ambient environment; there is only one WorldEnvironment. Give new fixtures room/deck-specific light masks and matching mesh layers so shadowless omnis cannot illuminate through a closed bay wall or into a neighboring deck. Bound new fixture ranges to their rooms and enable only the occupied/visible landing band. Do not create a blinking circuit by copying hazards.

Before implementation, retain a baseline from `main` for `scenarios/perf-smoke.json` using the existing policy: 1152 by 648, 60 warmup frames, 300 samples, mean <=25 ms and p95 <=50 ms. Do not change those limits, sample counts, resolution or assertions. Compare repeated baseline/feature runs on the same machine and build configuration, with raw samples retained under unique `tmp/connectors/verify-*` directories. Passing those coarse caps alone does not prove unchanged opening frame time: require no measurable regression beyond baseline run-to-run spread and inspect the construction/label counters during the opening. Record the measurements, including adverse results. No frame-time result has been measured for this design.

## 8. Audio

Add `app/door_audio.gd`, `class_name DoorAudio`, subscribed to accepted door events after the logical step. Emit creak/grind for MOVED, strained clunk for STALLED and wheel REFUSED, thud for plain-door REFUSED, and heavier release once on entering OPENING after final crank. A generic event's selected face frame supplies the AudioStreamPlayer3D position. Do not trigger sound by observing a rendered angle delta: zero-progress presses need sound and scene eviction must not duplicate events.

Use a small scene-level voice pool, not an audio player on every door. On pool exhaustion replace the oldest non-release effect, with release taking priority; this only limits presentation, never consumes another random resistance value or changes attempt timing. Variant index comes from a separate stable hash of door id and attempt index. Keep wake, smoke and Spanish voice playback paths and completion timing untouched.

Add tracked `tools/generate_hatch_audio.py`, using Python's standard library (`wave`, `struct`, `math`, a specified integer PRNG). It generates original mono 48 kHz PCM16 WAVs under `assets/audio/hatch/`: four creak/grind variants, one stalled clunk, one refusal wheel clunk, one plain-door thud and one release. Use seeded filtered noise, inharmonic decaying resonances and brief impact excitation, with fade-in/out and DC removal. Normalize each completed waveform to a -3 dBFS peak; prohibit clipping, nonfinite values, empty audio and silent output. No third-party recordings or model services.

Track a manifest containing synthesis version, per-file seed, sample count, sample rate and SHA256. `--check` synthesizes in memory and compares exact PCM/headers with tracked assets without overwriting; explicit generation writes only the declared output files. Python tests cover reproducibility, WAV format, expected duration, headroom and rejection paths. Import with loop, trim and normalization disabled. A windowed audio test verifies event-to-stream selection and no duplicate release. Andrew's listening judgment remains separate from these signal checks.

## 9. One logical tick and harness evidence

### 9.1 Tick ownership

Extract `app/game_step.gd`, `class_name GameStep`, from the current root/player/harness ordering. It is a pure coordinator, not a new engine loop. Each logical tick does the following once:

1. Advance wake and already-running door animations; publish completed collider changes.
2. Integrate input look, advance exactly one get-up/walk/ladder mode using fixed `Sim.LOGICAL_TICK_SECS`.
3. Detect accepted portal crossings; select and apply one interaction edge.
4. Update text state and nearby attention, then expire unused input.
5. Publish the immutable tick snapshot/events for Player, scene, voice, audio and harness observers.

Keep smoke's present sampling convention explicit during migration: sample the previous accepted eye at the root step, preserving the existing one-tick relationship and audio tests. WakePresent still controls the presented-closed-frame readiness handshake. Move its current `_complete_if_due` phase transition into GameStep at wake tick 282; WakePresent observes completion and only settles the camera/pass. Otherwise a batch of headless logical steps would depend on whether `_process` ran between them. Preserve the exact readiness/start-once and completion tests with this new owner. Likewise, Lighting/Hallway/PowerRoom fades advance through the logical step, and their render callbacks only project levels. GameStep is invoked by the production root or harness driver, never by both. Player exposes `step` and `present` instead of independently advancing another physics clock.

During a harness capture pause, freeze logical steps including door wheel, ladder, attention and lighting fade ticks. Rendering/chip capture can continue. The current `busy_capturing` guard stops only `drive_tick`; a separately ticking Player would otherwise climb or finish opening against a frozen report tick. Tests must pin state before/after a delayed capture. Keep the existing beat correlation tolerance; do not enlarge it to hide this discrepancy.

ShipScene provides shared geometry in both entrypoints. Existing harness lanes may retain their documented audio-free presentation, but their motion, doors, collision, labels and layout use the production classes. Test headless paths without awaiting `frame_post_draw`; windowed raster/capture tests exercise that separate boundary.

### 9.2 Existing scenarios

Regenerate the routes for `gameplay-full.json`, `gameplay-keyboard-turn.json`, `rod-pickup.json`, `hallway.json` and `power-room.json`. All pre-exit bay waypoints are bay-local and become world positions through T. Relative look deltas for a wholly rotated shot do not receive a second quarter-turn; absolute headings and the spawn frame do. Re-author the corridor segment after the bay exit, including the nearby switch, approach to the power doorway and console. Preserve each named beat, purposeful rod detour, keyboard-only turn lane and all evidence checks. Retiming beats to the actual route is permitted; widening tolerances or dropping beats is not.

Add `harness/route.gd`, `class_name HarnessRoute`, as a route author/compiler using layout ids and local offsets, shared by integration input scripts and a tracked `tools/build_connector_scenarios.gd`. It emits ordinary look/move/press/climb actions. Its controller may steer through waypoints using accepted poses but cannot write player coordinates or call Game's door methods. Pin the compiled schedules for fixed seeds and fail on timeout/stuck state rather than dynamically adding attempts. Each retained scenario gets a replay test against actual Player input.

`calibration-step.json` and `calibration-move.json` remain unchanged; their content is not ship geometry. `perf-smoke.json` retains its workload and policy, with only the world spawn frame changing. Keep negative never-beat and no-autoexposure scenarios failing. Expand `harness_test.gd` for new action/event shapes without weakening malformed input tests.

### 9.3 New unit and integration coverage

Write failing tests before implementing each contract. The existing runner auto-discovers sorted `*_test.gd` files; preserve its SCRIPT ERROR guard and all existing assertions.

| Test file | Required cases |
| --- | --- |
| `ship_layout_test.gd` | Exact coordinate anchors independently pinned, 30 floors, three D14 sections, two wells, 60 connectors/lifts, unique ids, references, four CRANK ids only, all face destination numbers, aft-well clearance, malformed records. |
| `ship_geometry_test.gd` | Render/collider solid identity, no double shared walls, both portal faces, exact apertures, open/closed blocker membership, landing floor holes, immutable ordering, all required wall pieces. |
| `bay_frame_test.gd` | T/inverse and quarter-turn basis, all seven pods and five exit poses, rod/hatch/switch pins, local route covariance, camera and light orientations, smoke inside/outside, one-time bay crossing. |
| `portal_crossing_test.gd` | Correct/incorrect direction, wall-band faces, out-of-aperture plane crossing, closed door, wrong deck, repeated crossing and first-event latch. |
| `hatch_resistance_test.gd` | Hash/PRNG fixtures, exact attempt schedule, zero/small/large deltas, 5..10 majority and 11..16 tail, seed/id separation, no dependence on render order. |
| `doors_test.gd` | Each policy, two-face shared progress, edge consumption, 6-tick wheel interpolation, final release, 48-tick swing, old 12+36/48 timings, parked collision, repeated refusal and no progress, snapshot persistence. |
| `interactions_test.gd` | Facing/reach/front/back/occlusion/deck, deterministic tie order, legacy switch fallthrough, no pickup+door double act, no interaction while mounted. |
| `ladder_test.gd` | Mount/dismount sweeps, support boundary, all landings on both wells, partial input, reversed direction, endpoint clamps, midshaft refusal, head collision, typed errors/no mutation, tick guard, 159.5 m round trip without height drift. |
| `ship_collision_test.gd` | Translated Resolve cases at D01/D30, vertical slice inclusion for head/foot, streamed/unstreamed parity, stable blocker revisions, all-deck locked-door containment. |
| `locomotion_test.gd` | Mode exclusivity, preserved walk ramp, transfer commit tick, no on-foot floor reset, climb input/device sign parity and camera eye continuity. |
| `ship_text_test.gd`, `naleya_test.gd` | Authored terms, generated identifiers, D14=16 and section41=51, D30=36, box extents/0.72 stroke/1 padding, wrapping, malformed markup, unchanged console and glyph fixtures. |
| `ship_text_cache_test.gd`, `label_attention_test.gd` | Same text/style shares immutable pair, different style misses, <=2 raster viewports, bounded eviction, per-face perception isolation, existing timings, decay across unload, no through-wall attention. Raster completion is separately windowed. |
| `ship_stream_test.gd` | Exact residency sets at D01/D14/D30, prefetch deadlines, bounded room/light count, no remote work during opening, persistent door states on reload, continuous shaft shell. |
| `game_step_test.gd` | Exactly one tick per caller, no state progression during capture pause, event observer fan-out, collider-open before sweep, no stale target after movement. |
| `door_audio_test.gd`, `tests/test_hatch_audio.py` | Correct outcomes/variants including zero-progress, final release once, bounded voices, exact deterministic generated assets and format. |
| `connector_route_test.gd` | Full real-Player route described below, plus deterministic replay digest. |

Pinned old collider totals (Hallway 72/70; full scene 86/84/83) cannot describe a larger topology. Keep their old fixture tests where that geometry still exists, and replace production totals with exact new solid-id manifests and explicit expected counts derived during implementation and reviewed against layout topology. Never change equality to a lower bound, remove a collision case, or calculate every expected value by calling the production function under test. Preserve pod-only placement tests, numeric tolerances and all resolver error/tunneling cases. Strengthen production checks with a closed/open differential for each door id.

`tests/connector_route_test.gd` builds Game, production Player and ScriptedAdapter headlessly, with presentation rendering disabled only at the outer scene boundary. It opens readiness through the existing test seam, runs wake/get-up, fetches the rod, pries the bay, crosses into the hall, flips the switch, opens the power door and activates the console. Then it walks back to section 41 and opens/traverses all four D14 hatches, entering sections 40 and 42 and trying the two far boundaries and a side/lift door. Every press is an input edge while facing the actual target. No state setter, teleport, direct door open or capsule edit is permitted.

Next it mounts the aft well, visits D13 and D15 landings, climbs to D01, dismounts, tries both hatches and lift, remounts and climbs to D30, dismounts and repeats refusal checks, then returns to D14. A second route exercises the fore well end to end; parameterize the same driver rather than copy it. Assert crossings and capsule position at every floor, no above/below overshoot under held input, unchanged opening state on return, and only the four allowed connector hatches ever open. Pin the logical event digest for fixed seed/input and compare a second execution. Pure per-landing tests cover both wells on all 30 decks even where the windowed route takes no screenshot.

### 9.4 Connector harness scenario

Add `scenarios/connector-route.json`, generated through HarnessRoute. The windowed route keeps the existing opening sequence, captures the four D14 open hatch faces and a refusal, climbs one well to D01 and D30 with dismounts and locked-door attempts, and returns to D14. Capture native/partial/resolved signs on D14 and both endpoints, with explicit attention holds. The second well's exhaustive traversal belongs to the headless integration, avoiding redundant windowed travel.

A D14-to-D01-to-D30-to-D14 trip covers 319 m vertically, or about 213 simulated seconds at 1.5 m/s before walking, cranking and reading. Do not pretend the full windowed route will reliably fit the existing 300-second process watchdog at realtime speed. Add a capture-only `logical_steps_per_present` setting to HarnessScenario, default 1 and explicitly 4 for connector-route. The harness executes up to four ordinary GameStep calls between presented frames, each with dt=1/60, separate input consumption and separate evidence. Break the batch at every due capture, label-raster residency boundary or terminal event; freeze logic until the capture completes. Never skip ticks, multiply dt, increase player speed, skip an assertion or accelerate the perf lane. Reject the setting outside capture mode. The new report echoes the setting and all logical ticks; headless replay must produce the same digest at batch sizes 1 and 4. Existing scenarios keep 1 and their old timing contracts. Measure that the accelerated capture finishes under the unchanged watchdog, including texture prefetch; retain the full 60 Hz logical journey.

Add `harness/connector_assertions.gd` (`ConnectorAssertions`) and typed report validation for `door_attempt`, `door_opened`, `portal_crossed`, `ladder_mount`, `landing`, `ladder_dismount`, `label` and residency evidence. Bump HarnessProtocol to 5 atomically in app, runner and tests because events now carry deck, id and locomotion mode. Retain chip encoding, hashes, readiness, all old named evidence and beat tolerance. Include explicit source/destination deck and world eye/capsule in movement evidence. Existing app hashing already covers new sim/app/harness GDScript modules.

Verify exact allowed-door set, attempt counts for the scenario seed, zero-progress evidence, wheel angle monotonic work, one release/open event, no illegal traversal, endpoint positions, restored D14 state and label numeric equality. Missing or reordered transition evidence fails. Existing dark/red/white capture thresholds stay unchanged. New red connector beats use the same red test; any new section41 white beats declare the existing white classification explicitly rather than inheriting red by default. Native/Spanish evidence supplements PNG checks, never substitutes for captures.

Commands remain:

```sh
godot --headless --path . -s tests/run_tests.gd
godot --headless --path . -s harness/run.gd -- scenarios/connector-route.json
```

Run all existing positive and negative harness lanes, plus the separate windowed main/voice audio integrations and cache raster checks. Machine PASS does not establish visual or listening acceptance. Keep raw artifacts in unique workspace paths. No tests, game run, audio audition or performance benchmark were executed as part of writing this design. Automated OCR review is skipped per Andrew's standing instruction.

## 10. Trade-offs, risks and remaining questions

The local-frame approach adds explicit conversions at a few boundaries but preserves the bay's many authored relationships. Rewriting world coordinates would spread a quarter-turn through pod/camera/lighting/hazard/interaction tests and make a second placement change equally expensive. A whole-game local-coordinate simulation would add repeated frame switching for every doorway; keeping world capsules avoids that cost.

A door policy enum and shared Store cover the four behaviors actually required. A class hierarchy per door or arbitrary behavior graph would add indirection without a present need. Streaming presentation with persistent simulation avoids building 60 room trees and avoids save/restore coupling to visibility. Texture caching costs a small raster queue and residency contract, but bounds both viewports and GPU memory.

Main risks are concrete:

1. The 0.2 m bay/hall wall band can be pierced on only one side, double-rendered, or transformed twice. Pin both faces and sweep across the complete opening in tests.
2. Quarter-turning Exit's poses without its pivots, or feeding world pods to local lighting/strip logic, changes the opening. Keep local fixtures and assert transformed whole-path/fixture parity.
3. The current sweep is conservative and has no gravity. Landing support boundaries, floor cutouts, capsule head clearance and open-leaf pockets must be proven before connecting live ladder input. Do not solve bad geometry by disabling collisions.
4. Input signs and W/S pitch overlap can invert climbing or move the camera instead of the body. Preserve on-foot bindings and pin device/script equivalence in both modes.
5. Separate app/harness clocks and capture pauses can make deterministic crank/climb claims false. Centralize tick ownership before relying on new end-to-end evidence.
6. Shadowless red lights can leak between rooms/decks, and label raster readbacks can stall a frame. Use masks, residency bounds, prefetch tests and measured baseline comparison. Opening performance is a verification obligation, not established by this document.
7. Cached ViewportTextures can alias subsequent draws, or shared materials can couple perception. Copy completed images into immutable textures and give each face its own blend parameter.
8. The moved doorway changes voice triggering and route framing. Keep the approved voice bytes, use the portal crossing, and verify the switch/right-of-door and last-port-door framing in the playable view.
9. Existing art/atlas files describe the previous build and example hatch states. Export built geometry from layout and retain proposed-versus-built markings; do not let them become a second runtime authoring path.

No product-direction question blocks implementation. The brief settles deck availability, hatches, labels, movement limits and audio source. Sound quality remains for Andrew's listening judgment after assets exist. Frame-time parity, raster clarity at capture resolution, and swing/landing clearance require measured runtime evidence. These are acceptance tasks, not reasons to reopen decisions 1 through 21. Crew counts, remote rooms, radiation causes and future lift behavior remain outside this feature.
