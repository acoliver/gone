"""Finish accepted pass-12 geometry, with only the requested free-hem changes."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np


def hem_displacement(points):
    x, y, z = points.T
    left = (x > -.141) & (x < -.079) & (y < .015)
    right = (x > .130) & (x < .167) & (y < .015)
    length = np.maximum(-z-.840, 0)*np.where(left, 4., np.where(right, 2.5, 0.))
    displacement = np.zeros_like(points)
    displacement[:, 1] = -length*.7
    displacement[:, 2] = -length
    return displacement


def card_groups(obj):
    parent = list(range(len(obj.data.vertices)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    positions = {}
    for vertex in obj.data.vertices:
        key = tuple(round(v, 7) for v in vertex.co)
        if key in positions:
            parent[find(vertex.index)] = find(positions[key])
        else:
            positions[key] = vertex.index
    for face in obj.data.polygons:
        for i in face.vertices[1:]:
            parent[find(i)] = find(face.vertices[0])
    groups = {}
    for i in range(len(parent)):
        groups.setdefault(find(i), []).append(i)
    return list(groups.values())


def stretch_hem(body, fringe, sheet):
    import bmesh
    from mathutils import Vector
    moved = {}
    for obj in [body, fringe]:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        # Each triangle must stay on one side of the extension's root plane.
        # Otherwise straight interpolation cuts across the piecewise-affine
        # bend and can push a neighbouring cut rim through the sheet.
        affected = [f for f in bm.faces if np.any(hem_displacement(np.array([v.co[:] for v in f.verts])))]
        edges = {e for f in affected for e in f.edges}
        vertices = {v for f in affected for v in f.verts}
        bmesh.ops.bisect_plane(bm, geom=list(vertices)+list(edges)+affected,
                              dist=1e-8, plane_co=(0, 0, -.840), plane_no=(0, 0, 1))
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces
                                        if np.any(hem_displacement(np.array([v.co[:] for v in f.verts])))])
        bm.to_mesh(obj.data)
        bm.free()
        points = np.array([obj.matrix_world @ v.co for v in obj.data.vertices])
        delta = hem_displacement(points)
        inverse = obj.matrix_world.inverted()
        for vertex, point, change in zip(obj.data.vertices, points+delta, delta):
            if np.any(change):
                vertex.co = inverse @ Vector(point)
        obj.data.update()
        moved[obj.name] = dict(vertices=int(np.sum(np.linalg.norm(delta, axis=1) > 1e-8)),
                               maximum_m=float(np.linalg.norm(delta, axis=1).max()))
    body.data.calc_loop_triangles()
    triangles = [t for t in body.data.loop_triangles if body.data.polygons[t.polygon_index].material_index == 0]
    faces = np.array([t.vertices[:] for t in triangles])
    used, inverse = np.unique(faces, return_inverse=True)
    from tear_boundaries import release_weights
    sheet.update(vertices=np.array([body.matrix_world @ body.data.vertices[i].co for i in used]),
                 faces=inverse.reshape(-1, 3), released=release_weights(body)[used],
                 uv=np.array([[body.data.uv_layers[0].data[i].uv[:] for i in t.loops] for t in triangles]))
    return moved




def rebake_cloth_ao(body, out):
    import bpy
    from common import activate
    scene = bpy.context.scene
    hidden = {o: o.hide_render for o in scene.objects if o.type == 'MESH'}
    for obj in hidden:
        obj.hide_render = obj != body
    originals = list(body.data.materials)
    mat = bpy.data.materials.new('Current cloth self-occlusion bake')
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    ao = nodes.new('ShaderNodeAmbientOcclusion')
    ao.inputs['Distance'].default_value = .06
    ao.only_local = True
    emission = nodes.new('ShaderNodeEmission')
    links.new(ao.outputs['Color'], emission.inputs[0])
    links.new(emission.outputs[0], nodes['Material Output'].inputs['Surface'])
    image = bpy.data.images.new('Pilot current cloth AO', width=2048, height=2048, alpha=False)
    image.colorspace_settings.name = 'Non-Color'
    target = nodes.new('ShaderNodeTexImage')
    target.image = image
    nodes.active = target
    for i in range(len(originals)):
        body.data.materials[i] = mat
    body.data.uv_layers.active = body.data.uv_layers['BakeUV']
    body.data.uv_layers['BakeUV'].active_render = True
    activate(body)
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 32
    scene.cycles.seed = 9513
    scene.render.bake.use_selected_to_active = False
    scene.render.bake.margin = 8
    bpy.ops.object.bake(type='EMIT')
    image.filepath_raw = str(out/'textures/tunicbody_current_ao.png')
    image.file_format = 'PNG'
    image.save()
    image.pack()
    for i, material in enumerate(originals):
        body.data.materials[i] = material
        node = material.node_tree.nodes.get('AO')
        if node:
            node.image = image
    for obj, value in hidden.items():
        obj.hide_render = value
    pixels = np.empty(2048*2048*4, np.float32)
    image.pixels.foreach_get(pixels)
    sample = pixels.reshape(2048, 2048, 4)[int(.1188486367*2048), int(.2021920681*2048), 0]
    if sample < .8:
        raise ValueError(f'Chest artefact remains in current-cloth AO: {sample}')
    return dict(cause='Stale selected-to-active AO transfer: opaque chest had AO=0 and neutral tangent normal; not an alpha hole',
                previous_ao=0., repaired_ao=float(sample), alpha=1.,
                repair='60 mm current-cloth-only ambient occlusion emission bake; no hidden dense meshes or fittings',
                image=image.filepath_raw)


def hem_coverage(sheet, fringe):
    import bpy
    from fringe_boundary import boundary_chains, measured_coverage
    mesh = bpy.data.meshes.new('Pilot hem measurement')
    mesh.from_pydata(sheet['vertices'], [], sheet['faces'])
    obj = bpy.data.objects.new(mesh.name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    vertex_uv = np.zeros((len(sheet['vertices']), 2))
    for face, uv in zip(sheet['faces'], sheet['uv']):
        vertex_uv[face] = uv
    group = obj.vertex_groups.new(name='Open hem')
    ids = np.flatnonzero((vertex_uv[:, 1] < .06) & (vertex_uv[:, 0] < 1.))
    group.add(ids.tolist(), 1., 'REPLACE')
    chains = boundary_chains(obj, 'Open hem')
    tex = {}
    for face in fringe.data.polygons:
        for loop in face.loop_indices:
            tex[fringe.data.loops[loop].vertex_index] = fringe.data.uv_layers[0].data[loop].uv.y
    pairs = []
    for ids in card_groups(fringe):
        minimum = min(tex[i] for i in ids)
        roots = [i for i in ids if abs(tex[i]-minimum) < 1e-7]
        a, b = max(((a, b) for a in roots for b in roots),
                   key=lambda pair: (fringe.data.vertices[pair[0]].co-fringe.data.vertices[pair[1]].co).length)
        pairs.append((a, b))
    report = measured_coverage(fringe, chains, pairs)
    bpy.data.objects.remove(obj, do_unlink=True)
    if report['authored_coverage'] < .70:
        raise ValueError(f'Extended hem lacks fringe coverage: {report}')
    return report


def finish(base, out, palette):
    import bpy
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from age_tunic import save_checkpoint
    from baked_age_colour import apply_colours
    from common import export
    out.mkdir(parents=True, exist_ok=True)
    (out/'textures').mkdir(exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(base/'finished.blend'))
    record = json.loads(bpy.context.scene['tunic5_record'])
    sheet = dict(np.load(base/'game-sheet.npz'))
    moved = stretch_hem(bpy.data.objects['TunicBody'], bpy.data.objects['Hemfringe'], sheet)
    np.savez_compressed(out/'game-sheet.npz', **sheet)
    coverage = hem_coverage(sheet, bpy.data.objects['Hemfringe'])
    record['fringe']['Hem fringe'].update(coverage)
    record['pass13'] = dict(geometry='Pass12 frozen except two retained free-hem tongues and their attached fringe',
                            hem=moved, hem_coverage=coverage)
    record['pass13']['chest_patch'] = rebake_cloth_ao(bpy.data.objects['TunicBody'], out)
    record['pass13']['colour'] = apply_colours(out, record, palette)
    save_checkpoint(out, 'finished', record)
    export(out/'candidate.glb')
    bpy.ops.wm.open_mainfile(filepath=str(out/'finished.blend'))
    export(out/'repeat.glb')
    identical = (out/'candidate.glb').read_bytes() == (out/'repeat.glb').read_bytes()
    (out/'repeat.json').write_text(json.dumps(dict(byte_identical=identical))+'\n')
    if not identical:
        raise ValueError('Pilot source does not re-export byte-identically')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--palette', type=Path, default=Path(__file__).with_name('target-colours.json'))
    a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
    finish(a.base.resolve(), a.out.resolve(), a.palette.resolve())
