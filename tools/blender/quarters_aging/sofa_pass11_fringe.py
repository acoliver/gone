"""Physical-arclength fibre bundles, independent of cut-edge tessellation."""
import bmesh
import bpy
import numpy as np
from mathutils import Vector

from card_contacts import CardContacts
from fabric_mesh import new_object
from fringe_cards import image_from_array
from sofa_decay_policy import ORDER


def stations(points, spacing):
    lengths = np.linalg.norm(np.diff(points, axis=0), axis=1)
    cumulative = np.r_[0., np.cumsum(lengths)]
    if cumulative[-1] <= 0:
        raise ValueError('Fringe chain has zero physical length')
    count = max(1, int(np.ceil(cumulative[-1]/spacing)))
    distances = (np.arange(count)+.5)*cumulative[-1]/count
    edges = np.minimum(np.searchsorted(cumulative, distances, side='right')-1, len(lengths)-1)
    return edges, (distances-cumulative[edges])/lengths[edges], cumulative[-1]/count


def bundle_atlas(seed, wool=False):
    rng = np.random.default_rng(seed)
    width, height, variants = 1024, 256, 8
    rgba = np.zeros((height*variants, width, 4), np.float32)
    rgba[:, :, :3] = (.44, .37, .27) if wool else (.16, .17, .15)
    y, x = np.mgrid[0:height, 0:width]
    for variant in range(variants):
        alpha = np.zeros((height, width), np.float32)
        for root in np.linspace(55, width-55, 8)+rng.uniform(-12, 12, 8):
            end = rng.uniform(.38, 1.)*height
            path = root+rng.uniform(-28, 28)*(y/height)+rng.uniform(5, 15)*np.sin(y*rng.uniform(.01, .04)+rng.uniform(0, 6.28))
            radius = rng.uniform(37, 42)*np.sqrt(np.maximum(0., 1-y/end))
            strand = np.clip(radius-np.abs(x-path)+.5, 0, 1)*(y < end)
            alpha = np.maximum(alpha, strand)
        rgba[variant*height:(variant+1)*height, :, 3] = alpha
    return rgba


def install_atlas(mat, out, seed, wool):
    rgba = bundle_atlas(seed, wool)
    image = image_from_array(mat.name+'_Bundles', rgba, out/(mat.name.lower()+'_bundles.png'))
    for node in mat.node_tree.nodes:
        if node.type == 'TEX_IMAGE' and node.image.colorspace_settings.name != 'Non-Color':
            node.image = image


def fringe(obj, mat, contacts, seed, wool=False):
    rng = np.random.default_rng(seed)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.normal_update()
    deform = bm.verts.layers.deform.active
    group = obj.vertex_groups['Lip shrink'].index if not wool else None
    remaining = {e for e in bm.edges if e.is_boundary and
                 (group is None or max(v[deform].get(group, 0.) for v in e.verts) >= .5)}
    vertices, faces, patterns = [], [], []
    total, covered, omitted = 0., 0., 0
    while remaining:
        # Start open selected runs at their endpoint; closed loops can start anywhere.
        endpoints = [v for e in remaining for v in e.verts if sum(other in remaining for other in v.link_edges) == 1]
        current = min(endpoints, key=lambda v: tuple(v.co)) if endpoints else min(remaining, key=lambda e: tuple(e.verts[0].co)).verts[0]
        chain, edges = [current], []
        while True:
            edge = next((e for e in current.link_edges if e in remaining), None)
            if edge is None:
                break
            remaining.remove(edge)
            edges.append(edge)
            current = edge.other_vert(current)
            chain.append(current)
        p = np.array([tuple(obj.matrix_world@v.co) for v in chain])
        indices, fractions, spacing = stations(p, .012)
        total += float(np.linalg.norm(np.diff(p, axis=0), axis=1).sum())
        for index, fraction in zip(indices, fractions):
            edge = edges[index]
            a, b = Vector(p[index]), Vector(p[index+1])
            tangent = (b-a).normalized()
            normal = (obj.matrix_world.to_3x3()@edge.link_faces[0].normal).normalized()
            middle = a+(b-a)*float(fraction)
            outward = middle-(obj.matrix_world@edge.link_faces[0].calc_center_median())
            outward = (outward-tangent*outward.dot(tangent)).normalized()
            width = spacing*float(rng.uniform(.78, .98))
            extent = float(rng.uniform(.004, .010) if wool else rng.uniform(.003, .008))
            placement = None
            for lift in [.0005, .001, .002]:
                root = middle-outward*.0003+normal*lift
                for factor in [1., .7, .45]:
                    tip = root+outward*(extent*factor)+normal*.0008
                    quad = [root-tangent*width/2, root+tangent*width/2,
                            tip+tangent*width/2, tip-tangent*width/2]
                    if contacts.clear(quad):
                        placement = quad
                        break
                if placement is not None:
                    break
            if placement is None:
                omitted += 1
                continue
            contacts.add(placement)
            offset = len(vertices)
            vertices.extend(placement)
            faces.append((offset, offset+1, offset+2, offset+3))
            variant = int(rng.integers(8))
            patterns.append([(0, variant/8), (1, variant/8), (1, (variant+1)/8), (0, (variant+1)/8)])
            covered += width
    bm.free()
    result = new_object(obj.name.replace('_GameContact', '')+'_Fringe', vertices, faces, mat)
    for face, uv in zip(result.data.polygons, patterns):
        for loop, point in zip(face.loop_indices, uv):
            result.data.uv_layers.active.data[loop].uv = point
    return dict(cards=len(faces), triangles=len(faces)*2, boundary_length_m=total,
                authored_coverage=covered/total, omitted_contacts=omitted,
                method='12 mm physical-arclength stations; visible bundled roots, not one card per tessellated edge')


def finish(out, record):
    for obj in list(bpy.context.scene.objects):
        if obj.name.endswith('_Fringe'):
            bpy.data.objects.remove(obj, do_unlink=True)
    supports = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH' and obj.get('aged_export')]
    contacts = CardContacts(supports)
    for wool, material_name in [(False, 'UpholsteryFringe'), (True, 'WoolFringe')]:
        install_atlas(bpy.data.materials[material_name], out/'textures/fringe', 10031+int(wool), wool)
    reports = {}
    for index, name in enumerate([*ORDER, 'Throw']):
        wool = name == 'Throw'
        reports[name] = fringe(bpy.data.objects[name+'_GameContact'], bpy.data.materials['WoolFringe' if wool else 'UpholsteryFringe'],
                               contacts, 10111+index*37, wool)
        if wool:
            record['throw']['materials']['fringe'] = reports[name]
        else:
            record['materials'][name]['fringe'] = reports[name]
    record['pass11']['fringe'] = reports
