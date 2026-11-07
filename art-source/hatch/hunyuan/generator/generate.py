#!/usr/bin/env python
"""Generate a 3D mesh from multi-view images with the MLX port of Hunyuan3D-2mv.

Example:
    python generate.py --front test_data/front.png --left test_data/left.png \
        --back test_data/back.png --right test_data/right.png --out out.glb
"""

from __future__ import annotations

import argparse
import os
import time

import mlx.core as mx

from mlx_hunyuan3d import Hunyuan3DDiTFlowMatchingPipeline
from mlx_hunyuan3d.meshclean import prune_specks, report

VIEWS = ("front", "left", "back", "right")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    for view in VIEWS:
        parser.add_argument(
            f"--{view}", help=f"path to the {view} view (RGBA, or use --remove-bg)"
        )
    parser.add_argument("--model-path", default="weights/Hunyuan3D-2mv")
    parser.add_argument("--subfolder", default="hunyuan3d-dit-v2-mv-turbo",
                        choices=["hunyuan3d-dit-v2-mv", "hunyuan3d-dit-v2-mv-turbo"])
    parser.add_argument("--dtype", default="float16", choices=["float16", "bfloat16", "float32"])
    parser.add_argument("--steps", type=int, default=None,
                        help="inference steps (default: 5 for turbo, 30 otherwise)")
    parser.add_argument("--guidance-scale", type=float, default=5.0)
    parser.add_argument("--octree-resolution", type=int, default=256)
    parser.add_argument("--num-chunks", type=int, default=50000)
    parser.add_argument("--mc-level", type=float, default=0.0)
    parser.add_argument("--box-v", type=float, default=1.01)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--remove-bg", action="store_true",
                        help="matte the input with rembg when it has no alpha channel")
    parser.add_argument("--min-component-faces", type=int, default=0,
                        help="drop disconnected components below this many faces "
                             "(0 = keep everything). 50 clears typical marching-cubes "
                             "specks. Keep it low: genuinely separate parts such as the "
                             "Viper's cannon pods run to hundreds of faces")
    parser.add_argument("--out", default="output.glb")
    args = parser.parse_args()

    images = {view: getattr(args, view) for view in VIEWS if getattr(args, view)}
    if not images:
        parser.error("provide at least one view (--front/--left/--back/--right)")
    for view, path in images.items():
        if not os.path.exists(path):
            parser.error(f"{view} image not found: {path}")

    steps = args.steps
    if steps is None:
        steps = 5 if "turbo" in args.subfolder else 30

    print(f"Views: {', '.join(images)}")
    pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
        args.model_path, subfolder=args.subfolder, dtype=args.dtype
    )

    started = time.time()
    meshes = pipeline(
        images,
        num_inference_steps=steps,
        guidance_scale=args.guidance_scale,
        seed=args.seed,
        box_v=args.box_v,
        octree_resolution=args.octree_resolution,
        mc_level=args.mc_level,
        num_chunks=args.num_chunks,
        remove_bg=args.remove_bg,
    )
    elapsed = time.time() - started

    mesh = meshes[0]
    if args.min_component_faces > 0:
        mesh, removed = prune_specks(mesh, args.min_component_faces)
        print(report(removed))
    mesh.export(args.out)
    peak = mx.get_peak_memory() / 1e9
    print(
        f"\nTotal: {elapsed:.1f}s | peak MLX memory: {peak:.2f} GB\n"
        f"Mesh: {len(mesh.vertices)} vertices, {len(mesh.faces)} faces, "
        f"watertight={mesh.is_watertight}\nWrote {args.out}"
    )


if __name__ == "__main__":
    main()
