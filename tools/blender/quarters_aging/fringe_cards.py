"""Numpy strand coverage and double-sided alpha-scissor cards on open boundaries."""
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

from fabric_mesh import material, new_object


def strand_atlas(seed, wool=False, width=1024, strip_height=256, variants=8):
    rng = np.random.default_rng(seed)
    rgba = np.zeros((strip_height*variants, width, 4), dtype=np.float32)
    normal = np.empty_like(rgba)
    normal[:] = (.5, .5, 1., 1.)
    color = np.array([.42, .36, .26] if wool else [.15, .16, .14])
    for variant in range(variants):
        coverage = np.zeros((strip_height, width), dtype=np.float32)
        for _ in range(int(rng.integers(40, 121) if wool else rng.integers(40, 71))):
            end = int(rng.uniform(.35, 1.)*strip_height)
            y = np.arange(end)
            root = rng.uniform(0, width)
            slope = rng.normal(0, .1)
            frequency = rng.uniform(.02, .07)
            phase = rng.uniform(0, 2*np.pi)
            amplitude = rng.uniform(1., 6.) if wool else rng.uniform(.2, 1.5)
            path = root+slope*y+amplitude*np.sin(y*frequency+phase)
            x = np.floor(path).astype(int)
            good = (x >= 1) & (x < width-1)
            coverage[y[good], x[good]] = 1
            coverage[y[good], x[good]-1] = np.maximum(coverage[y[good], x[good]-1], .6)
        rows = slice(variant*strip_height, (variant+1)*strip_height)
        rgba[rows, :, :3] = color[None, None, :]*(.9+.1*np.arange(strip_height)[:, None, None]/strip_height)
        rgba[rows, :, 3] = coverage
        gy, gx = np.gradient(coverage)
        n = np.stack([-gx*.7, -gy*.7, np.ones_like(gx)], axis=2)
        n /= np.linalg.norm(n, axis=2, keepdims=True)
        normal[rows, :, :3] = n*.5+.5
    return rgba, normal


def image_from_array(name, array, path, noncolor=False):
    image = bpy.data.images.new(name, width=array.shape[1], height=array.shape[0], alpha=True)
    if noncolor:
        image.colorspace_settings.name = 'Non-Color'
    image.pixels.foreach_set(array.ravel())
    image.filepath_raw = str(Path(path).resolve())
    image.file_format = 'PNG'
    image.save()
    image.pack()
    return image


def fringe_material(out, seed, wool=False):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    rgba, normal = strand_atlas(seed, wool)
    name = 'WoolFringe' if wool else 'UpholsteryFringe'
    color_image = image_from_array(name, rgba, out/f'{name.lower()}_rgba.png')
    normal_image = image_from_array(name+'Normal', normal, out/f'{name.lower()}_normal.png', True)
    mat = material(name, (.4, .35, .26) if wool else (.15, .16, .14))
    mat.use_backface_culling = False
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    shader = nodes.get('Principled BSDF')
    texture = nodes.new('ShaderNodeTexImage')
    texture.image = color_image
    links.new(texture.outputs['Color'], shader.inputs['Base Color'])
    cutoff = nodes.new('ShaderNodeMath')
    cutoff.operation = 'ROUND'
    links.new(texture.outputs['Alpha'], cutoff.inputs[0])
    links.new(cutoff.outputs[0], shader.inputs['Alpha'])
    texture_n = nodes.new('ShaderNodeTexImage')
    texture_n.image = normal_image
    nm = nodes.new('ShaderNodeNormalMap')
    links.new(texture_n.outputs['Color'], nm.inputs['Color'])
    links.new(nm.outputs['Normal'], shader.inputs['Normal'])
    return mat


def cards(obj, mat, seed, wool=False, spacing=.01, boundary_group=None, blockers=None):
    from card_contacts import CardContacts
    contacts = CardContacts(blockers) if blockers is not None else None
    rng = np.random.default_rng(seed)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.normal_update()
    deform = bm.verts.layers.deform.active
    group = obj.vertex_groups[boundary_group].index if boundary_group else None
    vertices, faces, patterns = [], [], []
    covered, total, omitted = 0., 0., 0
    offsets = []
    for edge in bm.edges:
        if not edge.is_boundary or (group is not None and max(v[deform].get(group, 0.) for v in edge.verts) < .5):
            continue
        a, b = [obj.matrix_world@v.co for v in edge.verts]
        length = (b-a).length
        total += length
        count = max(1, int(np.ceil(length/spacing)))
        normal = (obj.matrix_world.to_3x3()@edge.link_faces[0].normal).normalized()
        tangent = (b-a).normalized()
        middle = (a+b)/2
        outward = middle-(obj.matrix_world@edge.link_faces[0].calc_center_median())
        outward = (outward-tangent*outward.dot(tangent)).normalized()
        for i in range(count):
            width = min(rng.uniform(.008, .012), .8*length/count)
            extent = float(np.clip(rng.lognormal(np.log(.009 if wool else .004), .45), .002, .018 if wool else .009))
            droop = float(rng.uniform(0, np.radians(35)))
            direction = (outward*np.cos(droop)+Vector((0, 0, -1))*np.sin(droop)).normalized()
            twist = float(rng.uniform(-.26, .26))
            sideways = tangent*np.cos(twist)+normal*np.sin(twist)
            placement = None
            for extra in [0, .0005, .001, .002]:
                offset = abs(np.sin(twist))*width/2+.0003+extra
                root = a+(b-a)*(i+.5)/count-outward*.0004+normal*offset
                for factor in [1., .75, .5]:
                    tip = root+direction*max(.002, extent*factor)
                    quad = [root-sideways*width/2, root+sideways*width/2,
                            tip+sideways*width/2, tip-sideways*width/2]
                    if contacts is None or contacts.clear(quad):
                        placement = quad
                        break
                if placement is not None:
                    break
            if placement is None:
                omitted += 1
                continue
            if contacts is not None:
                contacts.add(placement)
            offsets.append(offset)
            base = len(vertices)
            vertices.extend(placement)
            faces.append((base, base+1, base+2, base+3))
            covered += width
            variant = int(rng.integers(8))
            patterns.append([(0, variant/8), (1, variant/8), (1, (variant+1)/8), (0, (variant+1)/8)])
    bm.free()
    if not total:
        raise ValueError('No tear boundary to fringe')
    obj_cards = new_object(obj.name+'_Fringe', vertices, faces, mat)
    for face, uv in zip(obj_cards.data.polygons, patterns):
        for index, point in zip(face.loop_indices, uv):
            obj_cards.data.uv_layers.active.data[index].uv = point
    return obj_cards, {'cards': len(faces), 'triangles': len(faces)*2,
                       'boundary_length_m': total, 'authored_coverage': covered/total,
                       'coverage_pass': covered/total >= .5, 'omitted_contacts': omitted,
                       'maximum_root_offset_m': max(offsets, default=0.), 'sat_checked': contacts is not None}
