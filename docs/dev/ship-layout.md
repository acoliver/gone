# Ship sections, connectors and ladders

The playable ship uses a pure layout model for placement, geometry, collision and door policy. D14 contains the opening bay, hall, secondary-power room, neighboring sections and two connectors. Ladder wells serve D01 through D30. D16 adds the protagonist's quarters. The whole-ship art atlas remains a separate planning tool.

## Layout and coordinates

`sim/ship_layout.gd` owns stable space/door ids, frames, deck datums, apertures and service reservations. Ship axes are -X bow, +X stern, -Z port, +Z starboard and +Y up. Deck pitch is 5.5 m; D14 is Y=0, and deck N uses `Y=(14-N)*5.5`. Clear room height is 3.2 m and corridor width is 3 m.

The bay keeps its authored local coordinates. `ShipLayout.bay_to_world()` applies a quarter-turn and translation to place it starboard of D14 section 41. World bay bounds are X 11..19 and Z 1.7..13.7. The hall spans X 6..30; its end hatches lead into connectors. The power room is X 21..33, Z -9.7..-1.7. Use the layout's anchors rather than copying coordinates into a new consumer.

`sim/ship_geometry.gd` and `sim/pod_geometry.gd` supply pure solid recipes. `sim/ship_collision.gd` builds collision from those recipes, preserving opening insertion order and providing deck-local fixtures. Presentation uses `app/ship_scene.gd`, `app/section.gd`, `app/connector.gd` and `app/ladder_shaft.gd`.

## State, interaction and streaming

`sim/doors.gd` stores door progress independently of rendered nodes. Policies are rod-pry, press-slide, crank and never-opens. The four internal D14 connector hatches crank open. Other-deck hatches remain closed except `D16-C-001-H-AFT`, which provides quarters access. Side doors and lifts refuse unless explicitly assigned an opening policy.

`app/interactions.gd` selects after accepted movement and dispatches an actionable edge. `app/game_step.gd` advances logical state at the fixed 60 Hz rate in production and harness play. Capture holds pause movement, doors, attention and fades together. Door audio follows logical work and latch events.

`sim/ladder.gd` owns climbing and landing transfers. Walking stops at supported landing boundaries; transfers use authored clearance paths. Collision does not depend on whether a room's rendered nodes are resident. `app/ship_stream.gd` manages presentation around the player while simulation persists.

`sim/ship_dressing.gd` generates room-owned dressing batches with exclusions for portals, hinges, ladders, services and damage. `app/corridor_dressing.gd` uploads their MultiMeshes without adding interaction or collision. Grating sits above a recessed tray while walk support remains in the simulation slab.

## Labels and audio

Navigation labels use boxed octal deck/section identifiers and quantity-preserving Spanish. `app/ship_text_cache.gd` stores shared immutable raster pairs. Each face has its own blend state and spatial attention tracking. First-resolution memory is shared with the console. See [ship writing](ship-writing.md) for strings and perception timing.

Bay presentation converts local hazards and smoke through the layout frame. Voice triggering uses accepted portal crossings. Hatch audio assets and playback are separate from geometry; the corresponding integration tests exercise production input and audio adapters.

## D16 quarters route (#114)

D16 section 42 spans X 36..60 at Y=-11. The aft ladder reaches its connector, and `D16-C-001-H-AFT` cranks open toward the quarters corridor. Its aft boundary and other side doors remain closed.

The quarters door is `D16-S-042-SIDE-009-STARBOARD`, centered at `(45,-11,1.5)`, with a 1.2 by 2.4 m opening and a corridor-face manual release. It uses press-slide policy without a badge or power gate. The interior is X 41..49, Y -11..-7.8, Z 1.7..7.7. The corridor owns the pierced entrance wall.

`Game.quarters` stores first-entry and playback state for the current game instance. Walking through the open threshold shows Remembered. Console corruption, message and fault phases occupy 60, 180 and 60 ticks before Present replaces it. Re-entry retains Present. The [quarters art guide](../art/quarters/README.md) lists assets, placement rules and open gameplay work.

## Power room terminal and status panel

Six stations use the generated standing console and keyboard under `assets/props/terminal/`. The active console uses `DisplayPlane` for Naleya/Spanish text. Dead screens stay dark; busted stations use damaged presentation, with one keyboard missing. The north-wall board uses `assets/props/status_panel/` and shared writing attention. See [the asset pipeline](asset-pipeline.md) and [status board](status-board.md).

## Rebuild maps and scenarios

From the repository root:

```sh
godot --headless --path . -s tools/export_ship_layout.gd
python docs/art/corridors/build-corridor-maps.py
python docs/art/corridors/build-connector-maps.py
godot --headless --path . -s tools/build_connector_scenarios.gd -- --connector-only
```

The export writes `docs/art/ship/3d/built-layout.json` and updates atlas built records. Python map builders require Pillow. The connector scenario generator replays the route and writes `scenarios/connector-route.json` without rewriting the other scenarios.

## Tests and capture

```sh
godot --headless --path . -s tests/run_tests.gd
godot --headless --path . -s harness/run.gd -- scenarios/connector-route.json
```

The connector lane opens the D14 hatches, visits section 42, climbs through D01 and D30, and returns to D14. Its capture-only logical batching keeps ordinary fixed ticks and stops at each required capture. The harness launches a windowed renderer; protocol evidence includes door attempts, portals, ladders, deck/pose, labels and residency. See [the harness contract](harness.md) for output interpretation.

Coverage includes `tests/ship_layout_test.gd`, `tests/ship_stream_test.gd`, `tests/doors_test.gd`, `tests/connector_geometry_test.gd`, `tests/ladder_test.gd`, `tests/connector_harness_test.gd` and `tests/d16_route_test.gd`. Native input, writing and audio tests complement pure geometry checks.

## Known limitations

Lifts do not operate. Most side doors and other-deck hatches do not open. Atlas facilities, remote rooms, radiation zones and hull dimensions are proposals rather than playable compartments. Motion uses conservative capsule collision without general gravity. Shadowless fixtures require explicit room masks. Harness capture success does not establish visual or listening acceptance.
