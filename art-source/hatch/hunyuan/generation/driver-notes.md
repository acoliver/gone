# Driver notes on Hunyuan hatch inputs (prev-inputs.jpg)
- FLUX inputs drifted from the concept: mostly intact green paint (fine for shape, paint comes later),
  but B-front has a small wheel and a centre seam; concept wheel is ~300 px of a 510 px leaf.
- A-left (side view for multiview) is a deep cabinet/box: would push the assembly into a thick box.
  Compare single-view vs multiview A carefully.
- B-left is a thin slab with the wheel standing off: good for the leaf.

## Driver judgement, category A (whole hatch), prev-A-all.jpg
- A-s410-sv: keep. Front reads as a real hatch (rounded riveted frame, strap hinges, dogs, six-spoke wheel); edge-on is a plate with the wheel on a short axle.
- A-s413-sv: keep. Similar to 410, slightly cleaner silhouette.
- A-s411-sv: reject. A stray flat plate sticks out of the back on a long stalk.
- A-s412-sv: reject. Back filled in as a deep box/cabinet.
- A-s410-mv: reject. The box-shaped side view made the whole thing a deep cabinet, as feared. Multiview with the current A-left input hurts.
- All A meshes fuse leaf and frame; the front plate is thin (structure will need the leaf slab thickened / split in Blender).

## Driver judgement, category B (door alone), prev-B-all.jpg
- All four reject. The FLUX input had a small off-centre wheel and a centre seam, and the meshes copied it:
  a mostly blank slab with a small wheel near the latch edge; the projected concept (big centred wheel)
  does not line up with the mesh wheel. Edge-on they are a thin plate.
- If a separate door is needed, regenerate B from a better input (the concept leaf crop with the frame
  painted out, wheel centred and about 60% of the leaf width), or split the door out of A-s410/A-s413.

## Driver judgement, category C (frame alone), prev-C-all.jpg
- All three usable: a clean rounded ring with a raised bead, evenly spaced rivets, open through the middle,
  one hinge knuckle/plate on the right edge. C-s410-sv and C-s412-sv cleanest.
- Only one hinge mount (concept has two, top and bottom); band width looks close to the concept's,
  check it against the 90 mm target after scaling. A frame from C plus a door from A (or a regenerated
  B) is the likely route.

## Driver judgement, paint (prev-paint.jpg)
- Hunyuan Paint followed the FLUX inputs' pale green paint, not the concept's rust: reject for this asset.
- Concept projection on A-s410 reads close to the concept from the front; at 30 degrees the wheel shows a
  doubled ghost because the front projection smears onto off-plane geometry. Production paint should stay
  the concept-derived atlas on proper UVs (as design.md says), not a raw front projection.

## Licence (read from the exact model card + Tencent Hunyuan 3D 2.0 Community License)
- Commercial use allowed under 1M MAU; outputs are owned by us.
- Territory excludes the EU, UK and South Korea; section 5.c forbids using, distributing or displaying
  outputs outside the Territory. Pushing generated meshes to the public GitHub repo, or shipping the game
  where EU/UK/KR players can get it, conflicts with that. Needs Andrew's call before any push.
- Distribution needs the licence copy + Notice file; AUP 12 asks machine-generated content to be identified
  in public contexts.
