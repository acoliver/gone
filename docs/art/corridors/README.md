# Corridor and connector art

These images provide concepts and metric planning views for the ship's corridors, wheel hatches, ladder wells and closed lifts. The playable layout is defined by `sim/ship_layout.gd`; the [runtime layout guide](../../dev/ship-layout.md) describes current traversal and door policies.

## Maps

- [corridor-current.png](corridor-current.png): exported opening geometry, including the stasis bay, hall and secondary-power room.
- [ship-scale.png](ship-scale.png): the opening within the proposed 2400 m, 30-deck ship.
- [d14-local-plan.png](d14-local-plan.png): D14 sections, connectors, ladder access and the bay/power-room relationship.
- [connector-section.png](connector-section.png): a connector section across several decks.

The ship envelope and surrounding districts remain planning proposals. The playable route includes D14 connectors and ladder wells, plus the D16 quarters exception. Older map annotations may describe an earlier construction slice; consult the runtime layout for the current allowed-door set.

## Concepts

The hatch images explore manual-wheel, powered and rusted-shut operation. Connector concepts show the room, ladder well and closed lift fronts. They guide appearance rather than exact construction. In particular, `connector-concept-ladder.png` shows a hinged ladder door while the implemented access is an open doorway.

The concepts are generated images and do not provide measured clearance or matching unseen geometry. Use layout data for dimensions, and inspect the [whole-ship atlas](../ship/README.md) for broader proposals.

## Rebuild and verify

From the repository root, using Godot and a Python environment with Pillow:

```sh
godot --headless --path . -s tools/export_ship_layout.gd
python docs/art/corridors/build-corridor-maps.py
python docs/art/corridors/build-connector-maps.py
godot --headless --path . -s tests/run_tests.gd
```

The export writes `docs/art/ship/3d/built-layout.json` and updates atlas built records. The first builder writes the opening PNG; the second writes the scale, local plan and connector section beside its script. Their assertions check image dimensions and label layout. `tests/ship_layout_test.gd` and `tests/connector_geometry_test.gd` cover the runtime geometry behind the maps.

## Known limitations

Concepts and proposed ship context are not construction drawings. Map builders retain planning annotations alongside exported built data. A failed builder assertion needs correction in the drawing or source layout before publishing its output.
