"""Seat the generated #130 medal while preserving its front atlas and saved cloth."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))
from tunic_details import points, geometry_hash, extract_ribbon, binding
from build import join_named, tree
from detail_clearance import continuous_gap, triangles
from reduced_clearance import crossing_pairs


def image_node(mat, path, colour=False):
    node = mat.node_tree.nodes.new('ShaderNodeTexImage')
    node.image = bpy.data.images.load(str(path), check_existing=False)
    node.image.colorspace_settings.name = 'sRGB' if colour else 'Non-Color'
    node.image.pack()
    uv = mat.node_tree.nodes.get('MedalCoordinates')
    if uv is None:
        uv = mat.node_tree.nodes.new('ShaderNodeUVMap')
        uv.name = 'MedalCoordinates'
        uv.uv_map = 'DetailUV'
    mat.node_tree.links.new(uv.outputs['UV'], node.inputs['Vector'])
    return node


def materials(directory, state):
    prefix = 'aged' if state == 'present' else 'as_built'
    result = []
    for enamel in [False, True]:
        mat = bpy.data.materials.new(('MedalEnamel_Aged' if state == 'present' else 'MedalEnamel') if enamel else 'MedalBrass_' + state)
        mat.use_nodes = True
        mat.use_backface_culling = True
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        bsdf = nodes.get('Principled BSDF')
        bsdf.inputs['Metallic'].default_value = 1
        bsdf.inputs['Roughness'].default_value = 1
        links.new(image_node(mat, directory / (prefix + '_albedo.png'), True).outputs['Color'], bsdf.inputs['Base Color'])
        packed = image_node(mat, directory / (prefix + '_orm.png'))
        channels = nodes.new('ShaderNodeSeparateColor')
        links.new(packed.outputs['Color'], channels.inputs['Color'])
        links.new(channels.outputs['Green'], bsdf.inputs['Roughness'])
        links.new(channels.outputs['Blue'], bsdf.inputs['Metallic'])
        group = bpy.data.node_groups.get('glTF Material Output')
        if group is None:
            group = bpy.data.node_groups.new('glTF Material Output', 'ShaderNodeTree')
            group.interface.new_socket(name='Occlusion', in_out='INPUT', socket_type='NodeSocketFloat')
        output = nodes.new('ShaderNodeGroup')
        output.node_tree = group
        links.new(channels.outputs['Red'], output.inputs['Occlusion'])
        normal = nodes.new('ShaderNodeNormalMap')
        normal.uv_map = 'DetailUV'
        links.new(image_node(mat, directory / (prefix + '_normal.png')).outputs['Color'], normal.inputs['Color'])
        links.new(normal.outputs['Normal'], bsdf.inputs['Normal'])
        if enamel:
            bsdf.inputs['Coat Weight'].default_value = 1
            bsdf.inputs['Coat Roughness'].default_value = .30 if state == 'present' else .09
            links.new(image_node(mat, directory / (prefix + '_coat.png')).outputs['Color'], bsdf.inputs['Coat Weight'])
        result.append(mat)
    return result


def load_objects(path, names):
    with bpy.data.libraries.load(str(path), link=False) as (_, dest):
        dest.objects = names
    for obj in dest.objects:
        bpy.context.collection.objects.link(obj)
    return dest.objects


def mount(baseline, generated, output, maps):
    output.mkdir(parents=True, exist_ok=True)
    report = {}
    for name, state in [('working', 'remembered'), ('pilot', 'present')]:
        bpy.ops.wm.open_mainfile(filepath=str(baseline / f'tunic-{name}.blend'))
        old, body = bpy.data.objects['Medal'], bpy.data.objects['TunicBody']
        frozen = {o.name: geometry_hash(o) for o in bpy.context.scene.objects if o.type == 'MESH' and o != old}
        record = json.loads(old['medal_frame'])
        old_origin, old_frame = np.array(record['origin']), np.array(record['frame'])
        metadata = {key: value.to_list() if hasattr(value, 'to_list') else value for key, value in old.items()}
        ribbon_material = old.data.materials[2]
        # Retain the entire accepted stage-3b fold, not an assumed sewn-index prefix.
        ribbon = extract_ribbon(old)
        ribbon.data.materials[0] = ribbon_material
        ribbon_positions = points(ribbon)
        assert len(ribbon_positions) == 372
        metal_parts = load_objects(generated / 'medal-fitted.blend', ['Body_Low', 'Loop_Low', 'Bar_Low'])
        native = [points(o).copy() for o in metal_parts]
        source_body_points = native[0].copy()
        metal_parts[0].data.calc_loop_triangles()
        source_body_faces = [t.vertices[:] for t in metal_parts[0].data.loop_triangles]
        # Seat the generated bar beneath the accepted full-width ribbon wrap.
        bar_shift = np.array([0., -.0028-float((native[2][:, 1].min()+native[2][:, 1].max())/2), .0254-float(native[2][:, 2].max())])
        native[2] += bar_shift
        for vertex, point in zip(metal_parts[2].data.vertices, native[2]):
            vertex.co = point
        support = tree(body)
        from medal_generated_hardware import cloth_frame
        origin, frame = cloth_frame(old_origin, old_frame, support)
        angle = float(np.arccos(np.clip(np.dot(frame[1], old_frame[1]), -1, 1)))
        normal = -frame[1]
        from medal_generated_seat import fit_reverse
        native[0], reverse = fit_reverse(metal_parts[0], origin, frame, support)
        assert len(reverse) >= 25
        native[2] = np.einsum('ij,kj->ik', old_origin + np.einsum('ij,jk->ik', native[2], old_frame) - origin, frame)
        for obj, positions in zip(metal_parts, native):
            for vertex, point in zip(obj.data.vertices, positions):
                vertex.co = point
            obj.data.update()
        faces = []
        offset = 0
        for obj in metal_parts:
            obj.data.calc_loop_triangles()
            faces.extend([[offset+i for i in t.vertices] for t in obj.data.loop_triangles])
            offset += len(obj.data.vertices)
        faces = np.array(faces)
        local = np.concatenate(native)
        lo, hi = len(native[0]), len(native[0])+len(native[1])
        loop_faces = faces[np.all((faces >= lo) & (faces < hi), axis=1)]
        loop_gap = continuous_gap((origin + np.einsum('ij,jk->ik', local, frame))[loop_faces], triangles(body), normal)
        local[lo:hi, 1] -= max(0., .000251-loop_gap)
        native[1] = local[lo:hi].copy()
        for vertex, point in zip(metal_parts[1].data.vertices, native[1]):
            vertex.co = point
        gap = continuous_gap((origin + np.einsum('ij,jk->ik', local, frame))[faces], triangles(body), normal)
        print(name, 'pre-shift minimum', gap, flush=True)
        shift = normal * max(0., .000251-gap)
        origin += shift
        local[hi:] -= shift @ frame.T
        native[2] = local[hi:].copy()
        for vertex, point in zip(metal_parts[2].data.vertices, native[2]):
            vertex.co = point
        solid_count = len(faces)
        world = origin + np.einsum('ij,jk->ik', local, frame)
        metal_materials = materials(maps, state)
        # Mixed boundary pixels keep the shared PBR maps without a pure-enamel coat.
        enamel_image = bpy.data.images.load(str(generated.parent / 'bakes/enamel-id.png'), check_existing=False)
        enamel_image.colorspace_settings.name = 'Non-Color'
        width, height = enamel_image.size
        pixels = np.empty(width * height * 4, np.float32)
        enamel_image.pixels.foreach_get(pixels)
        pixels = pixels.reshape(height, width, 4)
        for obj, original in zip(metal_parts, native):
            obj.data.materials.clear()
            for material in metal_materials:
                obj.data.materials.append(material)
            uv = obj.data.uv_layers[0]
            uv.name = 'DetailUV'
            bake = obj.data.uv_layers.new(name='BakeUV')
            uv = obj.data.uv_layers['DetailUV']
            for a, b in zip(bake.data, uv.data):
                a.uv = b.uv
            for polygon in obj.data.polygons:
                coordinates = np.array([uv.data[i].uv[:] for i in polygon.loop_indices]).mean(0)
                col, row = np.clip((coordinates * [width, height]).astype(int), 0, [width-1, height-1])
                polygon.material_index = int(pixels[row, col, 0] >= 1.-1e-6)
            colors = obj.data.color_attributes.new(name='RibbonColours', type='FLOAT_COLOR', domain='CORNER')
            for color in colors.data:
                color.color = (1, 1, 1, 1)
            transform = Matrix.Translation(Vector(origin)) @ Matrix(frame.T.tolist()).to_4x4()
            obj.data.transform(transform)
            obj.matrix_world = Matrix.Identity(4)
        from medal_generated_seat import clean_world_cap
        clean_world_cap(metal_parts[0])
        for part in metal_parts:
            for color in part.data.color_attributes['RibbonColours'].data:
                color.color = (1, 1, 1, 1)
        world = np.concatenate([points(part) for part in metal_parts])
        native = [np.einsum('ij,kj->ik', points(part)-origin, frame) for part in metal_parts]
        local = np.concatenate(native)
        faces = []
        offset = 0
        for part in metal_parts:
            part.data.calc_loop_triangles()
            faces.extend([[offset+i for i in t.vertices] for t in part.data.loop_triangles])
            offset += len(part.data.vertices)
        faces = np.array(faces)
        solid_count = len(faces)
        # Include the full cap and geometrically certified rear-envelope shoulders.
        # Selection never uses the measured support distance.
        from medal_generated_seat import reverse_anchors
        reverse = reverse_anchors(metal_parts[0], source_body_points, source_body_faces)
        # Preserve the whole saved fold, including every sewn corner channel.
        metal_count = len(local)
        old_attachment = json.loads(metadata['attachment'])
        support = tree(body)
        distances = np.array([support.find_nearest(Vector(p))[3] for p in world])
        # All source rear-cap anchors are retained, including any failing ones.
        supported = reverse[distances[reverse] <= .002]
        print(name, 'supported body reverse vertices', len(supported), 'of', len(reverse), 'gap', continuous_gap(world[faces], triangles(body), normal), flush=True)
        anchors = np.array(old_attachment['base_blender_m'])[len(old_attachment['metal_base_vertex_indices']):]
        ribbon_ids = np.argmin(np.linalg.norm(anchors[:, None]-ribbon_positions[None, :], axis=2), axis=1)
        ribbon_ids = np.unique(ribbon_ids)
        enamel_depth = np.median([native[0][list(p.vertices), 1].mean() for p in metal_parts[0].data.polygons if p.material_index == 1])
        apex = native[0][np.linalg.norm(native[0][:, [0, 2]], axis=1) < .0012, 1].min()
        bpy.data.objects.remove(old, do_unlink=True)
        obj = metal_parts[0]
        for following in metal_parts[1:] + [ribbon]:
            obj = join_named([obj, following], 'Medal')
        obj.data.name = 'Medal'
        for mesh in list(bpy.data.meshes):
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        for material in list(bpy.data.materials):
            if material.users == 0:
                bpy.data.materials.remove(material)
        obj.data.materials[0].name = 'MedalBrass_' + state
        obj.data.materials[1].name = 'MedalEnamel_Aged' if state == 'present' else 'MedalEnamel'
        for key, value in metadata.items():
            obj[key] = value
        obj['export'] = name == 'working'
        obj['aged_export'] = name == 'pilot'
        current = points(obj)
        np.testing.assert_allclose(current[:metal_count], world, atol=3e-8, rtol=0)
        np.testing.assert_array_equal(current[metal_count:], ribbon_positions)
        bases = reverse.tolist() + (metal_count+ribbon_ids).tolist()
        obj['attachment'] = json.dumps(dict(base_blender_m=current[bases].tolist(), support='TunicBody', metal_base_vertex_indices=reverse.tolist(), base_vertex_indices=bases, nominal_offset_range_m=[.00025, .002], anchor_definition='Entire source rear cap plus source rear-envelope shoulders: positive native Y, first rear ray hit within 1 micrometre, rear normal Y above 0.25. No support-distance filtering.'))
        obj['body_vertex_indices'] = list(range(len(native[0])))
        fitted = dict(guide_sha256=hashlib.sha256((generated/'medal-low.glb').read_bytes()).hexdigest(), image_sha256='8ce646f90c311b3c2e8985a7d4ca3b63f87e91dd042c539487af56c8a4d1c47c', raw_sample_count=186080, body_diameter_m=.032, body_depth_m=float(np.ptp(native[0][:, 1])), relief_m=float(enamel_depth-apex), relief_reference='Median enamel-face depth minus central generated apex depth', solid_triangles=solid_count, photoreal_source=str(generated/'medal-low.glb'), parent_generated_sha256='b98c7c4e688f1f3f6723db629493f965b2df3bb17b30fe923917092d525c3340', parent_fitted_low_sha256='5e6ba1c8a6712f09dadb22bbb25cedef9c56ff20ef7287694081778aece71cd9', method='Generated high/low face-normal depth scaling; repaired tip before reduction; high-only apex fairing. Hidden reverse tessellated and fitted to frozen wool; overlapping interior caps removed by exact self-union at stored world precision. Visible generated front and its atlas retained.')
        obj['fitted_medal'] = json.dumps(fitted)
        obj['medal_frame'] = json.dumps(dict(origin=origin.tolist(), frame=frame.tolist(), body_vertices=len(native[0])))
        obj['ribbon_loop'] = json.dumps(dict(loop_wrap_degrees=180, folded_tongues=1, full_width=True, cloth_thickness_m=.0008, minimum_design_clearance_m=.00008, ring_lug_separate_from_ribbon=False, slot_height_m=0., slot_width_m=0., construction='Stage-3b continuous sewn U-fold fitted over the generated straight bar', preserved_vertex_indices=list(range(len(ribbon_positions))), source_sew_base_indices=ribbon_ids.tolist()))
        obj['eyelet'] = json.dumps(dict(construction='Generated body, loop and straight bar', ribbon_loop=json.loads(obj['ribbon_loop'])))
        if name == 'pilot':
            aged = json.loads(bpy.context.scene['tunic5_record'])
            aged['bindings']['Medal'] = binding(obj, [list(range(metal_count)), list(range(metal_count, len(current)))], body, True)
            bpy.context.scene['tunic5_record'] = json.dumps(aged)
        assert all(geometry_hash(bpy.data.objects[n]) == h for n, h in frozen.items())
        self_contacts = len(crossing_pairs(obj))
        cloth_contacts = len(crossing_pairs(obj, body))
        report[name] = dict(metal_triangles=solid_count, metal_vertices=metal_count, ribbon_triangles=sum(len(p.vertices)-2 for p in obj.data.polygons if obj.data.materials[p.material_index].name.startswith('RibbonFabric')), body_depth_m=fitted['body_depth_m'], rigid_lean_radians=angle, bar_translation_m=bar_shift.tolist(), supported_metal_vertices=len(supported), supported_metal_max_distance_m=float(distances[supported].max()) if len(supported) else None, continuous_metal_clearance_m=float(continuous_gap(world[faces], triangles(body), normal)), self_crossings=self_contacts, cloth_crossings=cloth_contacts, unrelated_geometry_exact=True, source_frame=json.loads(obj['medal_frame']))
        report[name].update(reverse_body_vertices=len(reverse), reverse_body_max_distance_m=float(distances[reverse].max()), all_reverse_body_anchors_within_2mm=bool(np.all(distances[reverse] <= .002)), evaluation_only=True)
        print(name, report[name], flush=True)
        for mesh in bpy.context.scene.objects:
            if mesh.type == 'MESH' and mesh.get('aged_export' if name == 'pilot' else 'export'):
                mesh.data.name = mesh.name
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str(output/f'tunic-{name}.blend'))
    (output/'mounting.json').write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ['baseline', 'generated', 'output', 'maps']:
        parser.add_argument('--'+key, type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    mount(args.baseline.resolve(), args.generated.resolve(), args.output.resolve(), args.maps.resolve())
