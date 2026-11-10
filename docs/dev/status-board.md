# North-wall status board

The production textures are generated from `StatusBoardData` and `Naleya` by
`tools/build_status_board.gd`. From the project root, run the windowed renderer
at the asset's native resolution:

```
godot --path . --resolution 2560x1080 -s res://tools/build_status_board.gd
godot --headless --path . --import
```

The source screen is 2.40 × 1.02 m, the PNGs are 2560 × 1080, and the board
uses three systems columns. Keep the 40 px render-ink perimeter, verify no ink
intersections, and preserve identical layout geometry in both languages.
`StatusBoardData.MINIMUM_ROW_CELL_PX` is the minimum systems-row cell height.

The main drawing is a side elevation, with stern left and bow right. Its hull
profile, 30 deck levels and 5.5 m floor pitch come from
`docs/art/ship/3d/ship_atlas.json` through `StatusBoardData.side_elevation()`.
D14 is green, with the location marker on its floor line. Both languages name
the deck count; native quantities use octal Naleya glyphs. The 300 px-high hull
maps each deck pitch to 8.59 px. The systems keep their 60 px row cells in the
three columns below it. There is no additional plan inset, so neither the deck
lines nor the systems rows need to shrink.

For a 1600 × 900 capture with a 60-degree vertical field of view, a front-facing
screen at distance `d` projects to `900 × 1.02 / (2 × d × tan(30°))` pixels
tall. Each texture pixel projects to that value divided by 1080. This gives
0.3682 screen pixels per texture pixel at 2 m and 0.2455 at 3 m. A 60 px
texture cap therefore projects to 22.09 px at 2 m and 14.73 px at 3 m. The
minimum texture cap required by 14 px at 2 m is 38.03 px; the 10 px at 3 m
requirement is 40.74 px. The stricter requirement is 40.74 px. These figures
assume straight-on viewing, no perspective foreshortening, and no later image
scaling.
