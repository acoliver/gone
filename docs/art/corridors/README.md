# Corridor and connector art

These images are concept and planning art. They show proposals, not built geometry, except for `corridor-current.png`, which records the opening as it is built today. Concept images were generated with an image model. They set direction, not exact geometry.

## Maps

- **[corridor-current.png](corridor-current.png)** shows the built opening today: the stasis bay, corridor, and secondary power room. The corridor's other side doors remain closed.
- **[ship-scale.png](ship-scale.png)** locates the built rooms on the proposed 2,400 m, 30-deck ship. The rooms occupy about 30 m on deck 14. The ship envelope and surrounding layout are planning proposals.
- **[d14-local-plan.png](d14-local-plan.png)** shows the proposed deck 14 arrangement. The stasis bay moves to the starboard side door at X=15, and the secondary power room stays in its current position. The other corridor side doors stay closed. A connector sits at each end of the corridor, with a hatch at both ends. Each connector has an open ladder doorway in the port wall and dead lifts on the starboard wall. The aft connector's ladder doorway sits at X=34.5 to clear the power room.
- **[connector-section.png](connector-section.png)** cuts through a connector across decks 12 to 16. The per-deck hatch states show an example pattern. Their final states remain undecided.

## Concept images

The hatch images show three operating ideas: a manual wheel turn, powered operation with a button and card reader, and a hatch rusted shut. The connector images show an overview, a ladder well, and closed lift doors with call buttons. `connector-concept-ladder.png` shows a hinged door swung open. The design calls for an open doorway with no door.

These concept images are visual references, not precise plans. Use the maps above for the current built layout and the proposed corridor arrangement. For the whole-ship atlas, see the [ship art guide](../ship/README.md).

## Rebuild the maps

From the repository root, run both builders with a Python environment that has Pillow installed:

```sh
/Volumes/XS1000/tools/mlximg-venv/bin/python docs/art/corridors/build-corridor-maps.py
/Volumes/XS1000/tools/mlximg-venv/bin/python docs/art/corridors/build-connector-maps.py
```

The first command writes `corridor-current.png`. The second writes `ship-scale.png`, `d14-local-plan.png`, and `connector-section.png`. Each builder reads its source data from the repository and writes the PNGs beside its script.

## Troubleshooting

- If a builder reports `No module named PIL`, run it with a Python environment that has Pillow installed. The command above uses the local MLX image environment.
- If a builder fails its label-overlap or image validation assertions, treat that as a build error. Fix the drawing or label layout before using its output.
- The connector builder reads the ship atlas at `docs/art/ship/3d/ship_atlas.json`. Run it from the repository root so the documented paths resolve as shown.
