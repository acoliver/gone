# Her dresses: appearance and camera references

The rose cap-sleeved dress and blue sleeveless dress hang beside the central tunic in the quarters wardrobe. Both are recognizable in the doorway and wardrobe views. Present shows pale, faded cloth with damaged shoulders and hems. The [quarters guide](../../README.md#her-clothes) lists sources, export commands and tests; its [two-state rule](../../README.md#two-finish-states) defines the aging conditions.

## Tracked references

- [Game doorway comparison](game-doorway-comparison.png): both room states at the doorway camera.
- [Wardrobe comparison](comparison.png): room-state views with the two dresses beside the tunic.
- [Camera comparison](camera-comparison.png): the game camera poses under neutral Blender lighting.
- [Shoulder close-up](aged-shoulder.png) and [fibre deposit close-up](aged-heap.png): details that are harder to resolve in the room view.
- [Effect controls](controls-comparison.png): cloth with fold dust disabled and garments with edge fibres and deposits removed.
- [cameras.json](cameras.json): camera transforms, field of view and lighting definitions.

The comparison sheets include earlier assets for context. Use their delivered panels when checking current appearance. The central grey debris belongs to the tunic; the pale deposits beneath the side garments belong to the dresses.

## Sources and checks

The editable sources are `tools/blender/quarters/her_dresses/her_dresses-remembered.blend` and `her_dresses-aged.blend`. Their `build.py` exports both game GLBs. `dress_finish.py` reapplies rail arrangement and dry finishing from retained input meshes. `render.py` renders neutral views; `capture.gd` records the actual room cameras.

`test_export.py`, `test_refine.py` and `test_arrange.py` in that directory cover pigment packing, doorway visibility, damaged boundaries and rail arrangement. `tests/quarters_clothes_test.gd` covers runtime integration. Run the export and test commands in the linked quarters guide before capturing a changed dress.

## Known limitations

At game distance the deposits read mainly as pale patches; their soft fibres are visible in close-up but do not resolve in the room. Fold dust is subtle under the existing lighting. The rose dress has a conspicuously open shoulder/neckline tear in close-up. Some detached specks remain around the deposits.

The difference between close-up and room readability is consistent with detail occupying few pixels, but the captures alone do not isolate that cause. Assess changes in both game cameras before increasing detail or contrast.
