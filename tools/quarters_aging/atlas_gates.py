"""Exported-UV and baked finish checks independent of the Blender baker."""
import numpy as np
from PIL import Image
import trimesh


def repeat_metrics(directory, repeat):
    names = ['geometry_masks.png', 'weather_masks.png', 'region_masks.png',
             'masks.json', 'finishes.json', 'streak_sources.tres', 'aged_dust.png', 'aged_rust.png']
    names += [f'{state}_{kind}.png' for state in ('as_built', 'aged') for kind in ('albedo', 'normal', 'orm')]
    matches = [name for name in names if (directory / name).read_bytes() == (repeat / name).read_bytes()]
    exported = directory.with_suffix('.glb').read_bytes() == (repeat / 'storage_locker_module.glb').read_bytes()
    return dict(byte_identical_bake_files=len(matches), byte_identical_bakes=len(matches) == len(names), byte_identical_export=exported)


def uv_metrics(path, resolution=2048):
    scene = trimesh.load(path, force='scene', process=False)
    densities, stretches = [], []
    for node in scene.graph.nodes_geometry:
        transform, name = scene.graph[node]
        mesh = scene.geometry[name].copy()
        mesh.apply_transform(transform)
        for vertices, uv in zip(mesh.triangles, mesh.visual.uv[mesh.faces]):
            first, second = vertices[1:] - vertices[0]
            tangent = first / np.linalg.norm(first)
            normal = np.cross(first, second)
            normal /= np.linalg.norm(normal)
            bitangent = np.cross(normal, tangent)
            physical = np.array([[np.dot(first, tangent), np.dot(second, tangent)], [0, np.dot(second, bitangent)]])
            jacobian = (uv[1:] - uv[0]).T @ np.linalg.inv(physical) * resolution
            singular = np.linalg.svd(jacobian, compute_uv=False)
            densities.extend(singular.tolist())
            stretches.append(singular[0] / singular[1])
    return dict(density_min=float(min(densities)), density_max=float(max(densities)), max_stretch=float(max(stretches)))


def measure_atlases(directory, fields):
    arrays = np.load(fields)
    occupied, owner = arrays['occupied'], arrays['ownership']
    bare, paint = occupied & (owner == 2), occupied & (owner == 1)
    clean = np.asarray(Image.open(directory / 'as_built_orm.png'), np.float32) / 255
    normal = np.asarray(Image.open(directory / 'aged_normal.png'), np.float32)[..., :2] / 255 * 2 - 1
    magnitude = np.linalg.norm(normal[bare], axis=-1)
    from locker_gates import rust_pixels
    aged = np.asarray(Image.open(directory / 'aged_albedo.png'), np.float32)[..., :3] / 255
    oxide = rust_pixels(aged)[occupied]
    pits = np.linalg.norm(normal[occupied], axis=-1)
    hardware = {}
    names = arrays['part_names'][arrays['part_index'][occupied]]
    from locker_swatches import paint_field
    chroma_rust = paint_field(aged)[occupied] < .5
    for part in ('Rivets', 'Hinges', 'DoorVents', 'Handle', 'KickPlate'):
        selected = names == part
        if not selected.any(): raise ValueError('no hardware samples: ' + part)
        hardware[part] = dict(rust_fraction=float(oxide[selected].mean()),
                              chroma_rust_fraction=float(chroma_rust[selected].mean()),
                              pit_normal_rms=float(np.sqrt(np.mean(pits[selected] ** 2))))
    return dict(paint_roughness_range=[float(clean[..., 1][paint].min()), float(clean[..., 1][paint].max())],
                bare_steel_pit_normal_rms=float(np.sqrt(np.mean(magnitude ** 2))), hardware=hardware)
