"""Shared fitting, UV, export and capture operations for Batch 1 rigid props."""
import math
from pathlib import Path

import bpy
from mathutils import Vector

PAINT = (0.110, 0.145, 0.140, 1.0)


def material(name, color, metallic=.65, roughness=.42):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = color
    shader.inputs['Metallic'].default_value = metallic
    shader.inputs['Roughness'].default_value = roughness
    if name == 'Display':
        shader.inputs['Emission Color'].default_value = color
        shader.inputs['Emission Strength'].default_value = .5
    return mat


def materials(paint_color=PAINT):
    return {
        'PaintedSteel': material('PaintedSteel', paint_color, .15, .60),
        'BareSteel': material('BareSteel', (.76, .78, .77, 1), .65, .25),
        'DarkSteel': material('DarkSteel', (.045, .060, .058, 1), .76, .48),
    }


def reset():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for mesh in list(bpy.data.meshes):
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    for mat in list(bpy.data.materials):
        if mat.users == 0:
            bpy.data.materials.remove(mat)


def empty(name, location=(0, 0, 0), parent=None):
    obj = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    if parent:
        attach(obj, parent)
    return obj


def attach(obj, parent):
    bpy.context.view_layer.update()
    world = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_parent_inverse = parent.matrix_world.inverted()
    obj.matrix_world = world
    return obj


def bevel(obj, radius=.002, segments=2):
    if radius:
        mod = obj.modifiers.new('FoldedEdgeRadius', 'BEVEL')
        mod.width = radius
        mod.segments = segments
        mod.limit_method = 'ANGLE'
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
    return obj


def cage(name, vertices, faces, mat, radius=.002, parent=None):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(mat)
    bevel(obj, radius)
    if parent:
        attach(obj, parent)
    return obj


def panel(name, dims, centre, mat, radius=.002, parent=None):
    # Six closed quad faces are the faired planar cage of a fitted sheet part.
    dx, dy, dz = [v / 2 for v in dims]
    vertices = [(x, y, z) for z in (-dz, dz)
                for y in (-dy, dy) for x in (-dx, dx)]
    faces = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4),
             (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
    obj = cage(name, vertices, faces, mat, radius)
    obj.location = centre
    if parent:
        attach(obj, parent)
    return obj


def cylinder(name, radius, depth, centre, mat, axis=(0, 0, 1), sides=24,
             edge=.0008, parent=None):
    vertices = [(radius*math.cos(i*math.tau/sides),
                 radius*math.sin(i*math.tau/sides), z)
                for z in (-depth/2, depth/2) for i in range(sides)]
    faces = [tuple(reversed(range(sides))), tuple(range(sides, sides*2))]
    faces += [(i, (i+1)%sides, (i+1)%sides+sides, i+sides) for i in range(sides)]
    obj = cage(name, vertices, faces, mat, 0)
    bevel(obj, edge, 2)
    for face in obj.data.polygons:
        face.use_smooth = abs(face.normal.z) < .999
    obj.rotation_euler = Vector(axis).to_track_quat('Z', 'Y').to_euler()
    obj.location = centre
    if parent:
        attach(obj, parent)
    return obj


def beam(name, start, end, thickness, mat, parent=None):
    start, end = Vector(start), Vector(end)
    obj = panel(name, (thickness, thickness, (end-start).length), (0,0,0), mat)
    obj.rotation_euler = (end-start).to_track_quat('Z','Y').to_euler()
    obj.location = (start+end)/2
    if parent:
        attach(obj,parent)
    return obj


def rivets(name, points, mat, axis=(0, -1, 0), radius=.005, parent=None):
    parts=[]
    sides=8
    for i,point in enumerate(points):
        vertices=[(radius*r*math.cos(k*math.tau/sides),radius*r*math.sin(k*math.tau/sides),z)
                  for r,z in ((1,-.0005),(.88,.0014),(.35,.0028)) for k in range(sides)]
        faces=[tuple(reversed(range(sides))),tuple(range(2*sides,3*sides))]
        faces += [(band*sides+k,band*sides+(k+1)%sides,(band+1)*sides+(k+1)%sides,(band+1)*sides+k)
                  for band in range(2) for k in range(sides)]
        obj=cage(f'{name}_{i:03}',vertices,faces,mat,0)
        obj.rotation_euler=Vector(axis).to_track_quat('Z','Y').to_euler()
        obj.location=point
        for face in obj.data.polygons:
            face.use_smooth=True
        parts.append(obj)
    bpy.ops.object.select_all(action='DESELECT')
    for p in parts:
        p.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    obj = parts[0]
    obj.name = name
    obj.data.name = name
    if parent:
        attach(obj, parent)
    return obj



def recess(obj, centre, dims):
    cutter=panel('RecessCutter',dims,centre,obj.data.materials[0],0)
    bpy.context.view_layer.objects.active=obj
    mod=obj.modifiers.new('FoldedPocketCut','BOOLEAN')
    mod.operation='DIFFERENCE'
    mod.solver='EXACT'
    mod.object=cutter
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter,do_unlink=True)

def hinge_origin(obj, point):
    bpy.context.scene.cursor.location = point
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')


def unwrap(objects):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(30), island_margin=.003)
    bpy.ops.uv.average_islands_scale()
    bpy.ops.uv.pack_islands(rotate=True, margin=.002, shape_method='CONCAVE')
    bpy.ops.object.mode_set(mode='OBJECT')
    for obj in objects:
        obj.data.uv_layers.active.name = 'UVMap'


def load_guide(path, size, collection_name='HunyuanGuide', body_bounds=None):
    before=set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(Path(path).resolve()))
    imported=[o for o in bpy.data.objects if o not in before]
    meshes=[o for o in imported if o.type=='MESH']
    points=[o.matrix_world@v.co for o in meshes for v in o.data.vertices]
    minimum=Vector([min(p[i] for p in points) for i in range(3)])
    maximum=Vector([max(p[i] for p in points) for i in range(3)])
    source_bounds=[list(minimum),list(maximum)]
    if body_bounds is not None:
        minimum,maximum=map(Vector,body_bounds)
    target=Vector((size[0],size[2],size[1]))
    extent=maximum-minimum
    collection=bpy.data.collections.new(collection_name)
    bpy.context.scene.collection.children.link(collection)
    for obj in meshes:
        world=obj.matrix_world.copy()
        obj.parent=None
        obj.matrix_world.identity()
        for v in obj.data.vertices:
            p=world@v.co
            v.co=Vector(((p.x-(minimum.x+maximum.x)/2)*target.x/extent.x,
                         (p.y-(minimum.y+maximum.y)/2)*target.y/extent.y,
                         (p.z-minimum.z)*target.z/extent.z))
        for c in list(obj.users_collection):
            c.objects.unlink(obj)
        collection.objects.link(obj)
        obj.name='Guide_'+obj.name
        obj.display_type='WIRE'
        obj.hide_render=True
    for obj in imported:
        if obj.type!='MESH':
            bpy.data.objects.remove(obj,do_unlink=True)
    collection.hide_render=True
    collection.hide_viewport=True
    import numpy as np
    fitted=np.array([list(v.co) for obj in meshes for v in obj.data.vertices])
    sections=[]
    for fraction in (.1,.25,.5,.75,.9):
        z=size[1]*fraction
        sample=fitted[np.abs(fitted[:,2]-z)<size[1]*.01]
        sections.append({'height_m':z,'vertices':len(sample),
                         'xy_min':sample[:,:2].min(axis=0).tolist(),
                         'xy_max':sample[:,:2].max(axis=0).tolist()})
    return {'source_bounds_native': source_bounds,'carcass_fitting_bounds_native':[list(minimum),list(maximum)],
            'fitted_size_whd': list(size), 'sections':sections,
            'mesh_triangles': sum(len(o.data.polygons) for o in meshes)}


def export(output, objects):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    bpy.ops.export_scene.gltf(filepath=str(Path(output).resolve()), export_format='GLB',
        use_selection=True, export_yup=True, export_apply=False,
        export_materials='EXPORT', export_cameras=False, export_lights=False,
        export_extras=True)


def aim(obj, target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()


def render(folder, size, hero=(-2, -3.5, 2.6), target=None, angles=(30,120,210,300), scale=1.4):
    folder=Path(folder); folder.mkdir(parents=True,exist_ok=True)
    scene=bpy.context.scene
    scene.render.engine='CYCLES'
    scene.cycles.device='CPU'
    scene.cycles.samples=24
    scene.cycles.use_denoising=True
    scene.render.resolution_x=768
    scene.render.resolution_y=768
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.65,.65,.65,1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.7
    scene.view_settings.view_transform='Standard'
    scene.view_settings.look='None'
    for name,location,energy in [('Key',(-3,-4,5),650),('Fill',(4,-2,4),400),('Rear',(0,4,4),500)]:
        data=bpy.data.lights.new(name,'AREA'); obj=bpy.data.objects.new(name,data)
        scene.collection.objects.link(obj); obj.location=location; data.energy=energy; data.size=4
        aim(obj,(0,0,size[1]/2))
    data=bpy.data.cameras.new('CaptureCamera'); cam=bpy.data.objects.new('CaptureCamera',data)
    scene.collection.objects.link(cam); scene.camera=cam; data.type='ORTHO'
    data.ortho_scale=max(size)*scale
    target=target or (0,0,size[1]/2)
    cam.location=hero; aim(cam,target)
    scene.render.filepath=str(folder/'hero.png'); bpy.ops.render.render(write_still=True)
    radius=max(size)*2.4
    for angle in angles:
        rad=math.radians(angle)
        cam.location=(radius*math.sin(rad),-radius*math.cos(rad),size[1]*.5+radius*.28)
        aim(cam,target)
        scene.render.filepath=str(folder/f'view-{angle}.png')
        bpy.ops.render.render(write_still=True)


def reflect_x(objects):
    import bmesh
    from mathutils import Matrix

    reflection=Matrix.Diagonal((-1,1,1,1))
    bpy.context.view_layer.update()
    parents={o:o.parent for o in objects}
    worlds={o:reflection@o.matrix_world.copy()@reflection for o in objects}
    for obj in objects:
        if obj.type=='MESH':
            for vertex in obj.data.vertices:
                vertex.co.x=-vertex.co.x
            bm=bmesh.new()
            bm.from_mesh(obj.data)
            bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
            bm.to_mesh(obj.data)
            bm.free()
        obj.parent=None
        obj.matrix_world=worlds[obj]
    bpy.context.view_layer.update()
    for obj in objects:
        if parents[obj]:
            obj.parent=parents[obj]
            obj.matrix_parent_inverse=obj.parent.matrix_world.inverted()
            obj.matrix_world=worlds[obj]
    bpy.context.view_layer.update()


def build_main(script, prop_id, assemble, spec, default_size):
    import argparse
    import json
    import sys

    folder=Path(script).resolve().parent
    root=folder.parents[3]
    parser=argparse.ArgumentParser()
    parser.add_argument('--assemble',action='store_true')
    parser.add_argument('--output',type=Path,default=root/f'assets/props/quarters/{prop_id}.glb')
    parser.add_argument('--guide',type=Path,default=root/f'tmp/props/{prop_id}/guide.glb')
    parser.add_argument('--render-dir',type=Path)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    source=folder/f'{prop_id}-working.blend'
    if args.assemble:
        if not args.guide.is_file():
            raise FileNotFoundError('Fit requires the approved-image Hunyuan guide: '+str(args.guide))
        reset()
        guide=load_guide(args.guide,default_size,body_bounds=spec.get('guide_body_bounds_native'))
        before=set(bpy.data.objects)
        assemble(guide)
        asset=[o for o in bpy.context.scene.objects if o not in before and o.type in {'MESH','EMPTY'}]
        for obj in asset:
            obj['quarters_prop']=prop_id
        unwrap([o for o in asset if o.type=='MESH'])
        spec['guide']=guide
        spec['guide']['source']=str(args.guide.relative_to(root))
        spec['id']=prop_id
        (folder/'construction.json').write_text(json.dumps(spec,indent=2)+'\n')
        bpy.context.preferences.filepaths.save_version=0
        bpy.ops.wm.save_as_mainfile(filepath=str(source))
    else:
        bpy.ops.wm.open_mainfile(filepath=str(source))
        asset=[o for o in bpy.context.scene.objects if o.get('quarters_prop')==prop_id]
    args.output.parent.mkdir(parents=True,exist_ok=True)
    export(args.output,asset)
    if args.render_dir:
        render(args.render_dir,default_size,hero=spec['hero_camera_native'],target=spec.get('hero_target_native'),scale=spec.get('capture_scale',1.4))
