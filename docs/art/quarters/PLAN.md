# Quarters production workflow

The playable room and its furniture are implemented. This guide describes how to change or replace its art. The [quarters guide](README.md) lists current assets, export commands, tests and limitations. Narrative and aging decisions remain in [the design decisions](../../design/decisions.md).

## Room constraints

The room is an 8 by 6 m officers' cabin for a couple, with 3.2 m clear height. It has a double bed, sofa and wall screen, dining table with two chairs, desk console, open wardrobe, wall storage and personal belongings. There are no windows, books or paper. The photo is a durable polymer print behind glass.

The industrial direction uses grey-green painted steel, rivets, ribs, pipes and conduits, softened by the couple's possessions. [concept-pair.png](concept-pair.png) shows the intended two-state contrast. The [aging rule](README.md#two-finish-states) applies to new art as well as replacements.

`layout.json` owns approved footprints and use points. `sim/quarters_layout.gd` owns the room-to-ship mapping. Keep those records as the placement source for both states and collision. Run the [plan command](README.md#layout-and-runtime-ownership) after changing a footprint.

## From image to editable asset

Start substantial props with a selected generated hero image and a Hunyuan mesh. Retain both with their prompts and source settings. Fit clean cages directly to the generated surface, preserving the selected silhouette and substantial details. Avoid reconstructing a small prop from a few measured radii or profiles. The tunic medal uses a generated-surface fit for this reason.

Use additional generated views only after checking that they show the same object at the requested angle. The [contact-sheet tool](README.md#contact-sheets) can print generation commands with `--dry-run`. Source sheets belong under `sheets/`; prompts belong under `prompts/`.

Cloth uses sewn patterns, pressure shells and gravity drapes where needed. Keep the supporting generated shape or furniture as a fitting reference. Bake the simulation before export and retain the editable source. The cloth builders are under `tools/blender/quarters/bed_soft/`, `sofa/`, `dress_uniform/`, `her_jacket/` and `her_dresses/`.

## States and materials

Derive the aged state from the same base asset. Rigid props should retain geometry, names, pivots and footprint while changing finish. Collapsed foam, torn cloth and curled leather need separate geometry with compatible roots and supports.

Use image-derived colour and wear placement. The shared steel library maps complete face images into fitted UVs; the wardrobe and locker retain per-face images. Geometry masks may control relief, roughness and exposure without replacing the source image's wear layout. Keep display, glass, enamel and fabric roles separate from steel.

## Export and integration

Author quarters assets in Blender's native +Z-up frame, front -Y, and export with `export_yup=True`. Check the resulting glTF +Y-up bounds outside Blender. Keep editable sources and exporters under `tools/blender/quarters/<asset>/`; outputs go under `assets/props/quarters/`.

Use the saved-source export commands in the [asset guide](README.md). Verify named parts, closed surfaces where required, winding, UVs, actual support/contact, triangle allocation and repeat exports. Refresh Godot imports before capturing a changed asset.

Room tests cover shared placements, collision and state changes. Capture the ordinary-input quarters scenario to inspect assets under game lighting. Dust, fading and frayed edges must remain visible at the actual camera distance. Compare effect-enabled and effect-disabled views where the effect can be isolated.

## Known limitations

Storage drawer/shelf modules and leftover infill remain stand-ins. The console message, badge gameplay and cross-session state saving remain unfinished. Several assets retain visual limitations listed in the quarters guide. Some original assembly routes depend on untracked simulation or generation intermediates; committed saved sources support current exports without those files.
