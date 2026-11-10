"""Cut distinct retained hem tongues and scatter mass-accounted fallen wool."""
import bmesh
import bpy
import numpy as np

from common import recalc
from wear_pass10 import smoothstep


def torn_hem(body):
    bm = bmesh.new()
    bm.from_mesh(body.data)
    uv = bm.loops.layers.uv[0]
    deform = bm.verts.layers.deform.active
    patch = body.vertex_groups['DetailPatch'].index
    selected = {edge for face in bm.faces
                if max(loop[uv].uv.x for loop in face.loops) < 1. and
                max(loop[uv].uv.y for loop in face.loops) < .14 for edge in face.edges}
    bmesh.ops.subdivide_edges(bm, edges=list(selected), cuts=1, use_grid_fill=True)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    before = sum(face.calc_area() for face in bm.faces)
    slots = [(-.159, .006, .026), (-.131, .011, .048), (-.067, .008, .035),
             (.045, .012, .054), (.133, .009, .022), (.168, .005, .043)]
    remove = []
    for face in bm.faces:
        pattern = np.array([loop[uv].uv[:] for loop in face.loops])
        if (pattern[:, 0].max() >= 1. or pattern[:, 1].max() >= .14 or
                any(vertex[deform].get(patch, 0.) > 0 for vertex in face.verts)):
            continue
        x, y, z = face.calc_center_median()
        pattern_height = pattern[:, 1].mean()
        for center, half_width, top in slots:
            depth = float(smoothstep((top-pattern_height)/.012))
            ragged = .0012*np.sin(z*770+center*80)+.0006*np.sin(z*1790)
            if abs(x-center+ragged) < half_width*depth and pattern_height < top:
                remove.append(face)
                break
    lost = sum(face.calc_area() for face in remove)
    bmesh.ops.delete(bm, geom=remove, context='FACES')
    # A centroid cut can leave two surface fans touching at one corner.
    # Remove the smaller remnant rather than exporting a branched tear lip.
    while True:
        extra = set()
        for vertex in bm.verts:
            if sum(edge.is_boundary for edge in vertex.link_edges) <= 2:
                continue
            pending = set(vertex.link_faces)
            fans = []
            while pending:
                fan = {pending.pop()}
                frontier = set(fan)
                while frontier:
                    following = {face for own in frontier for edge in own.edges
                                 if vertex in edge.verts for face in edge.link_faces} & pending
                    pending -= following
                    fan |= following
                    frontier = following
                fans.append(fan)
            if len(fans) > 1:
                fans.sort(key=lambda fan: sum(face.calc_area() for face in fan), reverse=True)
                extra.update(face for fan in fans[1:] for face in fan)
        if not extra:
            break
        lost += sum(face.calc_area() for face in extra)
        bmesh.ops.delete(bm, geom=list(extra), context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    # Relax the already-retained narrow hem tongues downwards, with no motion
    # in the torso, sleeves or seated attachment regions.
    maximum = 0.
    for vertex in bm.verts:
        pattern = next(iter(vertex.link_loops))[uv].uv
        if pattern.x >= 1. or pattern.y >= .10 or vertex[deform].get(patch, 0.) > 0:
            continue
        x, y, z = vertex.co
        free_hem = float(smoothstep((abs(x)-.035)/.02))
        tongues = [(-.145, .007, .014), (-.101, .015, .032), (-.045, .020, .024),
                   (.090, .021, .041), (.151, .009, .012)]
        tongue = max(np.exp(-((x-center)/width)**4) for center, width, _ in tongues)
        length = max(height*np.exp(-((x-center)/width)**4) for center, width, height in tongues)
        amount = float(length*smoothstep((-z-.795)/.065))*free_hem
        vertex.co.z -= amount
        vertex.co.y -= .005*tongue*smoothstep((-z-.80)/.06)*free_hem
        maximum = max(maximum, amount)
    bm.to_mesh(body.data)
    bm.free()
    recalc(body)
    return dict(removed_area_m2=float(lost), removed_triangles=len(remove),
                pre_cut_sheet_area_m2=float(before), maximum_tongue_relaxation_m=maximum,
                construction='six unequally spaced slots cut into existing hem, leaving five tongues of different widths and lengths')


def scatter_debris(record, added_loss):
    from bake_down import decimate
    scale = np.array([1.50, 2.00, 1.23])
    origin = np.array([0., 0., -.95])
    # The locker-context transform rotates 55 degrees and shifts 100 mm
    # forward. Centre the broader deposit over its inner floor again.
    offset = np.array([.0819152044, .0573576436, 0.])
    names = ['FibreDust']+[p['name'] for p in record['fallen']]
    for name in names:
        obj = bpy.data.objects[name]
        inverse = obj.matrix_world.inverted()
        from mathutils import Vector
        for vertex in obj.data.vertices:
            world = np.array(obj.matrix_world @ vertex.co)
            vertex.co = inverse @ Vector((world-origin)*scale+origin+offset)
        recalc(obj)
        if name.startswith('FallenHem_'):
            obj['pass11_wear'] = True
            obj['pass12_wear'] = True
    mound = bpy.data.objects['FibreDust']
    mound.data.calc_loop_triangles()
    points = np.array([mound.matrix_world @ v.co for v in mound.data.vertices])
    triangles = points[np.array([t.vertices[:] for t in mound.data.loop_triangles])]
    volume = abs(np.einsum('ij,ij->i', triangles[:, 0], np.cross(triangles[:, 1], triangles[:, 2])).sum()/6)
    source = bpy.data.objects[record['fallen'][0]['name']]
    source.data.calc_loop_triangles()
    source_area = sum(p.area for p in source.data.polygons)
    allocated = added_loss*.45
    size = np.sqrt(allocated/(3*source_area))
    pieces = []
    for number, (x, y, angle) in enumerate([(-.20, -.045, -.6), (.18, .135, .9), (-.055, -.17, 1.7)], 4):
        obj = source.copy()
        obj.data = source.data.copy()
        bpy.context.collection.objects.link(obj)
        obj.name = f'FallenHem_{number}'
        p = np.array([obj.matrix_world @ v.co for v in obj.data.vertices])
        p = (p-p.mean(0))*size
        rotation = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
        p[:, :2] = p[:, :2]@rotation.T+np.array([x, y])+offset[:2]
        p[:, 2] += -.9485-p[:, 2].min()
        inverse = obj.matrix_world.inverted()
        for vertex, point in zip(obj.data.vertices, p):
            vertex.co = inverse @ Vector(point)
        recalc(obj)
        obj['pass11_wear'] = True
        obj['pass12_wear'] = True
        obj['aged_export'] = False
        low, reduction = decimate(obj, 280, protect=.002, keep_factor=20)
        bpy.data.objects.remove(obj, do_unlink=True)
        low.name = f'FallenHem_{number}'
        low['aged_export'] = True
        low['pass11_wear'] = True
        low['pass12_wear'] = True
        area = sum(p.area for p in low.data.polygons)
        piece = dict(name=low.name, area_m2=float(area), lost_area_m2=0., source='new hem loss, curled fallen-strip surface')
        record['fallen'].append(piece)
        record['reduction'][low.name] = reduction
        pieces.append(piece)
    fallen_area = sum(p['area_m2'] for p in pieces)
    if not 0. < fallen_area < added_loss:
        raise ValueError('Fallen-strip area must be a positive portion of the measured new hem loss')
    record['heap']['lost_area_m2'] += added_loss-fallen_area
    record['heap']['measured_volume_m3'] = float(volume)
    record['heap']['height_m'] = float(points[:, 2].max()+.95)
    return dict(common_debris_affine_scale=scale.tolist(), common_floor_offset_blender_m=offset.tolist(), new_fallen=pieces,
                hem_loss_to_fallen_area_m2=float(fallen_area),
                hem_loss_to_fibre_dust_area_m2=float(added_loss-fallen_area),
                mound_volume_m3=float(volume), mound_height_m=record['heap']['height_m'])
