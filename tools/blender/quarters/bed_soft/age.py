"""Derive 1000-year dry oxidative decay from the remembered simulated bedding."""
import json
from pathlib import Path
import sys

import bpy
import bmesh
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build import ASSETS, SCRATCH, bake_origin, drop_to, mesh_points, unwrap
sys.path.insert(0, str(HERE.parents[1] / 'quarters_aging'))
from common import apply, assert_collision_clear, assert_surface_clear, collision, export, midsurface, save, settle, solidify, surface_tree
from cloth_decay import attachment_distance
from debris import scatter
from fabric_mesh import material
from foam_collapse import collapse
from powder_cards import powder_card
from stress_cut import cut_faces, fractal


def cloth_settings(frames=160):
    return dict(quality=24, time_scale=.3, mass=.15, stiffness=160, bending=.35,
                frames=frames, collision_quality=10, collision_distance_m=.001,
                self_distance_m=.003, air_damping=10)


def clear_left_rail(quilt):
    bm = bmesh.new()
    bm.from_mesh(quilt.data)
    # Reduction can replace the convex rail turn with a chord through steel.
    # Split that chord at the outside corner, retaining an explicit wrap ridge.
    outside = -.8055
    bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
                          dist=1e-7, plane_co=(outside, 0, 0), plane_no=(1, 0, 0))
    moved = 0
    for vertex in bm.verts:
        p = vertex.co
        if outside - 1e-6 <= p.x < -.71 and -1.15 < p.y < 1.05 and p.z < .5525:
            p.z = .5525
            moved += 1
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bm.to_mesh(quilt.data)
    bm.free()
    return {'outside_x_m': outside, 'rail_clear_top_m': .5525, 'fitted_vertices': moved}


def aged_quilt(quilt, mattress, old_top):
    midsurface(quilt)
    new_top = float(mesh_points(mattress)[:, 2].max())
    supports = [surface_tree(mattress)] + [surface_tree(o) for o in bpy.context.scene.objects if o.get('bed_frame')]
    for vertex in quilt.data.vertices:
        vertex.co.x -= .17
        vertex.co.z -= old_top - new_top
    # Vertex rays miss rail crossings between cloth samples. Start the entire
    # connected sheet above the rail/crust envelope without flattening its cuff.
    lift = max(new_top, .55) + .025 - min(v.co.z for v in quilt.data.vertices)
    for vertex in quilt.data.vertices:
        vertex.co.z += lift
    assert_surface_clear(quilt)
    assert_collision_clear(quilt)
    initial_distance = min(attachment_distance(v.co, supports) for v in quilt.data.vertices)
    def split(point):
        # The head cuff and two long crease lines split, with varying widths.
        cuff = abs(point.y - (.19 + fractal(point.x, 95241, .025))) < .022 and -.61 < point.x < .20
        fold = abs(point.x - (-.34 + fractal(point.y, 95242, .035))) < .06 + .035 * np.sin(point.y * 12) ** 2 and -.90 < point.y < -.18
        side = abs(point.x + .72 + fractal(point.y, 95243, .025)) < .027 and -.64 < point.y < -.04
        return cuff or fold or side
    # Refined tear fans are a finishing mesh, not a stable working cloth cage.
    # Friction, rather than suspended stitches, holds the free aged sheet.
    record = settle(quilt, cloth_settings(220), {})
    record['initial_collision_clear'] = True
    record['initial_nearest_support_m'] = initial_distance
    record['initial_whole_sheet_lift_m'] = lift
    record['cuts'] = cut_faces(quilt, split, 95241, refine=True)
    record['side_slide_m'] = -.17
    quilt.data.materials.clear()
    quilt.data.materials.append(material('BrittleWool', (.32, .27, .21)))
    for face in quilt.data.polygons:
        face.material_index = 0
    reduction = quilt.modifiers.new('Brittle wool runtime reduction', 'DECIMATE')
    reduction.ratio = .65
    apply(quilt, reduction)
    record['rail_wrap_finish'] = clear_left_rail(quilt)
    solidify(quilt, .0018)
    bake_origin(quilt)
    unwrap(quilt)
    return record


def age_pillow(obj, mattress, seed):
    points = mesh_points(obj)
    bottom = points[:, 2].min()
    for vertex in obj.data.vertices:
        p = vertex.co
        p.z = bottom + (p.z - bottom) * .12
        p.z += .003 * np.sin(p.x * 27 + p.y * 18 + seed)
    shift = drop_to(obj, mattress, .001)
    report = cut_faces(obj, lambda p: abs(p.y - (.69 + fractal(p.x, seed, .022))) < .014
                       and abs(p.x - (-.355 if obj.name.endswith('L') else .355)) < .22,
                       seed, refine=True)
    obj.data.materials.clear()
    obj.data.materials.append(material('BrittleCotton', (.47, .425, .34)))
    bake_origin(obj)
    unwrap(obj)
    report.update({'height_ratio': .12, 'support_translation_m': shift})
    return report


def deposits(source):
    records = []
    texture_dir = ASSETS / 'bed_soft_textures'
    # The side spill is outside the rail/feet envelope; the platform spill sits
    # in the exposed strip beyond the mattress foot, not inside the crust.
    for name, centre, radius, floor in (
        ('FoamCrumbs_Floor', (-.98, -.40, 0), (.15, .58), True),
        ('FoamCrumbs_Platform', (0, -1.017, .5), (.50, .009), False),
    ):
        config = dict(name=name, material='FoamPowder', color=[.34, .235, .12],
                      center_blender_m=centre, radius_xy_m=radius, count=72 if floor else 36,
                      piece_size_m=[.003, .014] if floor else [.003, .007], piece_thickness_m=.001,
                      heap_height_m=.003, floor_gap_m=.0007)
        records.append(scatter(source, config, 95244 if floor else 95245))
    for name, centre, extent, seed in (
        ('FibreFoamPowder_Floor', (-.98, -.40, .0008), (.15, .58), 95246),
        ('FibreFoamPowder_Platform', (0, -1.017, .5008), (.50, .009), 95247),
    ):
        obj = powder_card(name, centre, extent, texture_dir, seed, sectors=24)
        obj['aged_export'] = True
        # glTF and Blender both retain the binary grain alpha as a cutout.
        shader = obj.data.materials[0].node_tree.nodes.get('Principled BSDF')
        image_node = next(n for n in obj.data.materials[0].node_tree.nodes if n.type == 'TEX_IMAGE' and n.image and not n.image.name.endswith('Normal'))
        obj.data.materials[0].node_tree.links.new(image_node.outputs['Alpha'], shader.inputs['Alpha'])
        obj.data.materials[0].surface_render_method = 'DITHERED'
        obj.data.materials[0].alpha_threshold = .5
        bake_origin(obj)
    return records


def main():
    bpy.ops.wm.open_mainfile(filepath=str(HERE / 'bed-soft-working.blend'))
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH' and (obj.get('bed_frame') or obj.name == 'SupportFloor'):
            collision(obj, .0005)
    mattress = bpy.data.objects['Mattress']
    old_top = float(mesh_points(mattress)[:, 2].max())
    config = dict(support_z_m=.5, support_gap_m=.001, height_ratio=.34,
                  back_depth_ratio=1, back_support_y_shift_m=0, core_reduction=.30,
                  voronoi_cells=22, crack_width_m=.006, cover_lift_m=.007,
                  cover_loss_fraction=.22, cover_reduction=.86, cover_thickness_m=.0018,
                  contact_clearance_m=.0005, cloth=cloth_settings(160))
    records = {'Mattress': collapse(mattress, config, 95240)}
    from finish_aged import repair_cover
    records['Mattress']['cover_finish'] = repair_cover(mattress)
    # The shared module supplies closed crust plates and a separately settled
    # upper cover, joined into the original Mattress node.
    foam = bpy.data.materials['Foam']
    foam.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value = (.32, .18, .075, 1)
    foam.diffuse_color = (.32, .18, .075, 1)
    cotton = bpy.data.materials['CottonTicking']
    cotton.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value = (.43, .365, .26, 1)
    cotton.diffuse_color = (.43, .365, .26, 1)
    unwrap(mattress)
    collision(mattress, .0005)
    for name, seed in (('Pillow_L', 95248), ('Pillow_R', 95249)):
        records[name] = age_pillow(bpy.data.objects[name], mattress, seed)
        collision(bpy.data.objects[name], .0005)
    records['Quilt'] = aged_quilt(bpy.data.objects['Quilt'], mattress, old_top)
    records['debris'] = deposits(mattress)
    (HERE / 'aging.json').write_text(json.dumps(records, indent=2) + '\n')
    save(HERE / 'bed-soft-aged.blend', records)
    export(ASSETS / 'bed_soft_aged.glb')


def quilt_only():
    bpy.ops.wm.open_mainfile(filepath=str(HERE / 'bed-soft-aged.blend'))
    records = json.loads((HERE / 'aging.json').read_text())
    bpy.data.objects.remove(bpy.data.objects['Quilt'], do_unlink=True)
    with bpy.data.libraries.load(str(HERE / 'bed-soft-working.blend')) as (source, target):
        target.objects = ['Quilt']
    quilt = target.objects[0]
    bpy.context.collection.objects.link(quilt)
    mattress = bpy.data.objects['Mattress']
    for name in ('Pillow_L', 'Pillow_R'):
        obj = bpy.data.objects[name]
        points = mesh_points(obj)
        bottom, top = points[:, 2].min(), points[:, 2].max()
        for vertex in obj.data.vertices:
            vertex.co.z = bottom + (vertex.co.z - bottom) * .0144 / (top - bottom)
        drop_to(obj, mattress)
        records[name]['finished_height_m'] = .0144
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH' and (obj.get('bed_frame') or obj.name in ('Mattress', 'Pillow_L', 'Pillow_R', 'SupportFloor')):
            collision(obj, .0005)
    original = json.loads((HERE / 'simulation.json').read_text())
    old_top = original['Mattress']['bounds_native_m'][1][2]
    records['Quilt'] = aged_quilt(quilt, mattress, old_top)
    (HERE / 'aging.json').write_text(json.dumps(records, indent=2) + chr(10))
    save(HERE / 'bed-soft-aged.blend', records)
    export(ASSETS / 'bed_soft_aged.glb')


def rail_only():
    bpy.ops.wm.open_mainfile(filepath=str(HERE / 'bed-soft-aged.blend'))
    records = json.loads((HERE / 'aging.json').read_text())
    quilt = bpy.data.objects['Quilt']
    midsurface(quilt)
    records['Quilt']['rail_wrap_finish'] = clear_left_rail(quilt)
    solidify(quilt, .0018)
    bake_origin(quilt)
    unwrap(quilt)
    (HERE / 'aging.json').write_text(json.dumps(records, indent=2) + chr(10))
    save(HERE / 'bed-soft-aged.blend', records)
    export(ASSETS / 'bed_soft_aged.glb')


if __name__ == '__main__':
    if '--quilt-only' in sys.argv:
        quilt_only()
    elif '--rail-only' in sys.argv:
        rail_only()
    else:
        main()
