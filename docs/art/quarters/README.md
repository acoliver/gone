# Quarters art

## Plan view

Regenerate `plan.png` and its check report from the repository root with `/Volumes/XS1000/tools/mlximg-venv/bin/python tools/art/quarters_plan.py --layout docs/art/quarters/layout.json --out docs/art/quarters/plan.png --report docs/art/quarters/plan-checks.json`. The checks cover room bounds, intersecting floor footprints, player reachability and route clearance, entrance-wall storage, and the clear doorway opening. The command exits with a nonzero status when a check fails.

## Contact sheets

Run the commands from the repository root with `/Volumes/XS1000/tools/mlximg-venv/bin/python tools/art/contact_sheet.py`. The `hero --prompts docs/art/quarters/prompts/pilot.json --prop storage_locker_module --out tmp/contact` command generates a hero for each seed in the prompt file. Add `--seeds 101` to select a specific seed. Add `--dry-run` to print the commands without generating images.

The `views --prompts docs/art/quarters/prompts/pilot.json --prop storage_locker_module --hero tmp/contact/storage_locker_module/hero-s101.png --out tmp/contact` command generates the four view edits from a hero image. Add `--seed 1` to set the edit seed. Add `--dry-run` to print the edit commands without generating images.

The `sheet --prop storage_locker_module --out tmp/contact` command composes the hero and four views into `sheet.png` and writes `sheet.json` with input hashes. It selects the first hero image by seed order.

Generated images, prompt files and provenance stay in the gitignored `tmp/` directory until a sheet is approved. After approval, copy the chosen hero, views, sheet and provenance JSON to `docs/art/quarters/sheets/<prop>/`.

### What the pilot showed about generated views (2026-11-07)

The FLUX.2-klein edit model does not turn an object. Asked for a left, right or back view, it either redraws the front face again or changes the object.
- **Sofa:** all four views became a two-seat sofa with a throw on each arm.
- **Locker:** the left, right and back views each showed the door face again. Only the straight front view agreed with the hero.

So the hero image is the main input to Hunyuan. A generated view goes in alongside it only if the reviewer confirms it shows the same object at the requested angle. For the pilot props the inputs are:

| Prop | Hunyuan input |
| --- | --- |
| Locker | hero plus the front view |
| Sofa | hero alone |
| Tunic | hero alone, unless a view passes review |

Side and back geometry is filled in by Hunyuan and then corrected during fitting.

Two more pilot findings:
- **Uniform:** the image model kept hanging the trousers on a separate clip hanger, so the pilot uses the tunic alone and the trousers become their own prop.
- **Locker hero:** this is an edit of seed 107 that closed the open legs and recessed the handle. Its base flange sticks out slightly, and that gets corrected when the mesh is fitted.
