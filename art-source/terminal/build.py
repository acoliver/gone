from pathlib import Path
import json
import math
import sys
import os

import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent.parent / "tmp/issue91/termmodel2/meshes/front-s410.glb"
KEYBOARD_REPORT = ROOT.parent.parent / "tmp/issue91/kbmodel/keyboard-report.json"
HEIGHT = 1.75
VOXEL_SIZE = .011
FRONT_SIGN = -1
NO_BAY = os.environ.get("NO_BAY") == "1"
if "--" in sys.argv:
    NO_BAY = NO_BAY or "--no-bay" in sys.argv[sys.argv.index("--") + 1:]


def active(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def join_meshes():
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    if not meshes:
        raise RuntimeError('GLB import contained no meshes')
    active(meshes[0])
    for obj in meshes:
        obj.select_set(True)
    bpy.ops.object.join()
    return bpy.context.object


def components_and_remove_tiny(obj):
    bm = bmesh.new(); bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-5)
    remaining = set(bm.faces); components = []
    while remaining:
        seed = remaining.pop(); component = [seed]; stack = [seed]
        while stack:
            face = stack.pop()
            for edge in face.edges:
                for linked in edge.link_faces:
                    if linked in remaining:
                        remaining.remove(linked); component.append(linked); stack.append(linked)
        components.append(component)
    total = sum(len(c) for c in components)
    removed = sum(len(c) for c in components if len(c) < total * .005)
    for component in components:
        if len(component) < total * .005:
            bmesh.ops.delete(bm, geom=component, context='FACES')
    bm.to_mesh(obj.data); bm.free(); obj.data.update()
    return len(components), removed


def bounds(obj):
    p = [v.co[:] for v in obj.data.vertices]
    return [min(x[i] for x in p) for i in range(3)], [max(x[i] for x in p) for i in range(3)]


def triangles(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def is_closed(obj):
    bm = bmesh.new(); bm.from_mesh(obj.data)
    boundary = sum(e.is_boundary for e in bm.edges)
    nonmanifold = sum(not e.is_manifold for e in bm.edges)
    bm.free()
    return boundary, nonmanifold


def clipped_floor_area(obj, faces, x0, x1, y0, y1):
    obj.data.calc_loop_triangles()
    selected={p.index for p in faces}
    area=0.0
    for tri in obj.data.loop_triangles:
        if tri.polygon_index not in selected:
            continue
        poly=[(obj.data.vertices[i].co.x,obj.data.vertices[i].co.y) for i in tri.vertices]
        for axis,bound,keep_greater in ((0,x0,True),(0,x1,False),(1,y0,True),(1,y1,False)):
            clipped=[]
            for a,b in zip(poly,poly[1:]+poly[:1]):
                av=a[axis]; bv=b[axis]
                ain=av>=bound if keep_greater else av<=bound
                bin_=bv>=bound if keep_greater else bv<=bound
                if ain: clipped.append(a)
                if ain != bin_:
                    t=(bound-av)/(bv-av)
                    clipped.append((a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1])))
            poly=clipped
            if not poly: break
        if len(poly)>=3:
            area+=abs(sum(poly[i][0]*poly[(i+1)%len(poly)][1]-poly[(i+1)%len(poly)][0]*poly[i][1] for i in range(len(poly)))/2)
    return area


def add_mat(name, color, metallic=0, roughness=.5):
    mat = bpy.data.materials.new(name); mat.diffuse_color = (*color, 1); mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Metallic'].default_value = metallic; bsdf.inputs['Roughness'].default_value = roughness
    return mat


def camera(name, location, target, lens=48):
    data=bpy.data.cameras.new(name); obj=bpy.data.objects.new(name,data); bpy.context.collection.objects.link(obj)
    obj.location=location; obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler(); data.lens=lens
    return obj


def area(name, location, color, power, size, target):
    data=bpy.data.lights.new(name,'AREA'); data.energy=power; data.shape='DISK'; data.size=size; data.color=color
    obj=bpy.data.objects.new(name,data); bpy.context.collection.objects.link(obj); obj.location=location
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()


def main():
    bpy.ops.import_scene.gltf(filepath=str(SOURCE))
    obj=join_meshes(); obj.name='Terminal_GeneratedFit'
    component_count, removed_faces=components_and_remove_tiny(obj)
    lo,hi=bounds(obj); spans=[hi[i]-lo[i] for i in range(3)]
    uniform=HEIGHT/spans[2]
    for v in obj.data.vertices:
        v.co.x=(v.co.x-(lo[0]+hi[0])/2)*uniform
        v.co.y=(v.co.y-hi[1])*uniform+.002
        v.co.z=(v.co.z-lo[2])*uniform
    obj.data.update()
    # Preserve an unremeshed surface tree for a deterministic distance sample.
    deps=bpy.context.evaluated_depsgraph_get()
    source_tree=BVHTree.FromObject(obj,deps,epsilon=0.0)
    source_vertices=list(obj.data.vertices)
    sample_points=[v.co.copy() for v in source_vertices[::max(1,len(source_vertices)//4000)][:4000]]
    obj.data.remesh_voxel_size=VOXEL_SIZE
    obj.data.remesh_voxel_adaptivity=0.0
    remesh=obj.modifiers.new('WatertightVoxelSolid','REMESH'); remesh.mode='VOXEL'; remesh.voxel_size=VOXEL_SIZE; remesh.adaptivity=0.0
    active(obj); bpy.ops.object.modifier_apply(modifier=remesh.name)
    # Sample source-to-solid distances after remeshing.
    tree=BVHTree.FromObject(obj,bpy.context.evaluated_depsgraph_get(),epsilon=0.0)
    distances=[]
    for p in sample_points:
        hit=tree.find_nearest(p)
        if hit and hit[0] is not None: distances.append(hit[3])
    boundary,nonmanifold=is_closed(obj)
    if boundary or nonmanifold: raise RuntimeError(f'Voxel solid not closed before cuts: boundary={boundary}, nonmanifold={nonmanifold}')
    # Flatten the wall-facing back to Y=0, then close the planar cut.
    bm=bmesh.new(); bm.from_mesh(obj.data)
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-6,plane_co=(0,0,0),plane_no=(0,1,0),clear_outer=True,clear_inner=False)
    back_edges=[e for e in bm.edges if e.is_boundary and all(abs(v.co.y)<.006 for v in e.verts)]
    if back_edges: bmesh.ops.holes_fill(bm,edges=back_edges,sides=0)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(obj.data); bm.free(); obj.data.update()
    # Voxel close the clipped wall face before boolean operations.
    remesh=obj.modifiers.new('CloseFlattenedRear','REMESH'); remesh.mode='VOXEL'; remesh.voxel_size=VOXEL_SIZE; remesh.adaptivity=0.0
    active(obj); bpy.ops.object.modifier_apply(modifier=remesh.name)
    lo,hi=bounds(obj); post_remesh_height=hi[2]-lo[2]; post_remesh_scale=HEIGHT/post_remesh_height
    for v in obj.data.vertices: v.co*=post_remesh_scale
    obj.data.update()
    lo,hi=bounds(obj); dims=[hi[i]-lo[i] for i in range(3)]
    if not .55 <= dims[1] <= .65: raise RuntimeError(f'Uniformly scaled source depth {dims[1]:.3f}m is outside 0.55-0.65m')
    if not NO_BAY:
        # Find the usable upward shelf in the specified height band and front half.
        shelf_faces=[p for p in obj.data.polygons if p.normal.z>.94 and .85<=p.center.z<=1.15 and p.center.y < (lo[1]+hi[1])/2]
        if not shelf_faces: raise RuntimeError('No upward-facing shelf faces between z=.85 and 1.15m in front half')
        shelf_top=max(p.center.z for p in shelf_faces)
        chosen=[p for p in shelf_faces if p.center.z >= shelf_top-.015]
        shelf_x=[obj.data.vertices[i].co.x for p in chosen for i in p.vertices]
        shelf_y=[obj.data.vertices[i].co.y for p in chosen for i in p.vertices]
        shelf_min_y=min(shelf_y); shelf_max_y=max(shelf_y)
        keyboard=json.loads(KEYBOARD_REPORT.read_text())['dimensions_m']
        kw,kd=keyboard['width'],keyboard['depth']; pocket_w=kw+.090; pocket_d=kd+.070
        # Place the rear edge on the shelf and open the pocket through its -Y front edge.
        front_y=min(shelf_y); rear_y=front_y+pocket_d
        floor_z=shelf_top-.040
        # Extend the shallow shelf into a solid keyboard deck before cutting the recess.
        deck_depth=pocket_d+.08
        bpy.ops.mesh.primitive_cube_add(size=1,location=(0,(front_y+rear_y)/2,shelf_top-.06))
        deck=bpy.context.object; deck.name='KeyboardDeckUnion'; deck.dimensions=(pocket_w+.08,deck_depth,.14)
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        active(obj); union=obj.modifiers.new('SolidKeyboardDeck','BOOLEAN'); union.operation='UNION'; union.solver='EXACT'; union.object=deck
        bpy.ops.object.modifier_apply(modifier=union.name); bpy.data.objects.remove(deck,do_unlink=True)
        # Carry the pocket opening through the terminal's front silhouette so no shelf lip remains.
        opening_front_y=lo[1]-.03
        opening_rear_y=rear_y+.03
        cutter_depth=opening_rear_y-opening_front_y
        cutter_center=(0,(opening_front_y+opening_rear_y)/2,floor_z+.12)
        bpy.ops.mesh.primitive_cube_add(size=1,location=cutter_center)
        cutter=bpy.context.object; cutter.dimensions=(pocket_w,cutter_depth,.24)
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        active(obj); mod=obj.modifiers.new('OpenFrontKeyboardPocket','BOOLEAN'); mod.operation='DIFFERENCE'; mod.solver='EXACT'; mod.object=cutter
        bpy.ops.object.modifier_apply(modifier=mod.name); bpy.data.objects.remove(cutter,do_unlink=True)
        bevel=obj.modifiers.new('KeyboardPocketRimBevel','BEVEL'); bevel.width=.006; bevel.segments=3; bevel.limit_method='ANGLE'; bevel.angle_limit=math.radians(40)
        active(obj); bpy.ops.object.modifier_apply(modifier=bevel.name)
        # Check manifoldness after the cut and measure the pocket floor geometry.
        boundary,nonmanifold=is_closed(obj)
        if boundary or nonmanifold: raise RuntimeError(f'Pocket cut damaged watertight solid: boundary={boundary}, nonmanifold={nonmanifold}')
        floor_faces=[p for p in obj.data.polygons if p.normal.z>.999 and abs(p.center.z-floor_z)<.006 and abs(p.center.x)<pocket_w/2+.01 and front_y-.01<=p.center.y<=rear_y+.01]
        footprint=pocket_w*pocket_d
        floor_area=clipped_floor_area(obj,floor_faces,-pocket_w/2,pocket_w/2,front_y,rear_y)
        print('POCKET_DEBUG', {'shelf_top':shelf_top,'shelf_x':(min(shelf_x),max(shelf_x)),'shelf_y':(shelf_min_y,shelf_max_y),'front_y':front_y,'rear_y':rear_y,'floor_z':floor_z,'floor_faces':len(floor_faces),'floor_area':floor_area,'footprint':footprint},flush=True)
        if not NO_BAY and (not floor_faces or abs(floor_area/footprint-1)>.05): raise RuntimeError(f'Pocket floor area {floor_area:.5f} vs footprint {footprint:.5f}')
    # Ray tests from the floor downward must encounter the solid top-to-bottom structure.
    screen_mat=add_mat('Screen',(.006,.012,.016),.05,.18)
    screen= bmesh.new();
    # plane faces -Y and sits slightly forward of the existing recess.
    # The display fits the inset front panel with a 10 mm border left visible.
    screen_left, screen_right = -.270, .270
    screen_bottom, screen_top = 1.345, 1.625
    screen_hits = []
    deps = bpy.context.evaluated_depsgraph_get()
    for screen_x in [screen_left + (screen_right-screen_left)*i/20 for i in range(21)]:
        for screen_z in [screen_bottom + (screen_top-screen_bottom)*i/12 for i in range(13)]:
            hit, location, normal, face_index, hit_object, material = bpy.context.scene.ray_cast(
                deps, Vector((screen_x, -1.0, screen_z)), Vector((0, 1, 0)), distance=1.5
            )
            if hit and hit_object == obj:
                screen_hits.append(location.y)
    if len(screen_hits) != 21 * 13:
        raise RuntimeError(f'Screen opening ray grid hit {len(screen_hits)}/273 terminal faces')
    screen_frontmost_y = min(screen_hits)
    screen_y = screen_frontmost_y - .002
    mesh=bpy.data.meshes.new('DisplayPlaneMesh'); mesh.from_pydata([(screen_left,screen_y,screen_bottom),(screen_right,screen_y,screen_bottom),(screen_right,screen_y,screen_top),(screen_left,screen_y,screen_top)],[],[(0,3,2,1)]); mesh.materials.append(screen_mat)
    display=bpy.data.objects.new('DisplayPlane',mesh); bpy.context.collection.objects.link(display)
    display['material']='Screen'; display['screen_boolean_cut']=False
    display['frontmost_surface_y_m']=screen_frontmost_y
    display['screen_offset_m']=.002
    paint=add_mat('OliveDrab_WornMetal',(.105,.145,.075),.25,.48); obj.data.materials.clear(); obj.data.materials.append(paint)
    # Screen socket locates the independently modeled display plane.
    empty=bpy.data.objects.new('ScreenSocket',None); bpy.context.collection.objects.link(empty); empty.empty_display_type='CUBE'; empty.empty_display_size=.03; empty.location=(0,screen_y-.004,1.485)
    empty['interface_dimensions_m']=[screen_right-screen_left,screen_top-screen_bottom]
    # Decimate only after booleans; preserve planar cuts, with collapse for final count.
    active(obj); dec=obj.modifiers.new('PlanarReduction','DECIMATE'); dec.decimate_type='DISSOLVE'; dec.angle_limit=math.radians(1.0); bpy.ops.object.modifier_apply(modifier=dec.name)
    print('AFTER_PLANAR',triangles(obj),is_closed(obj),flush=True)
    if triangles(obj)>40000: raise RuntimeError(f'Triangle cap exceeded without topology-damaging collapse: {triangles(obj)}')
    boundary,nonmanifold=is_closed(obj)
    if boundary or nonmanifold: raise RuntimeError(f'Final mesh not watertight: boundary={boundary}, nonmanifold={nonmanifold}')
    floor=add_mat('StudioFloor',(.20,.20,.20),0,.8)
    bpy.ops.mesh.primitive_plane_add(size=20,location=(0,0,-.01)); bpy.context.object.name='StudioBackdrop'; bpy.context.object.data.materials.append(floor)
    area('Key_Light',(2.5,-2.4,2.7),(1,.91,.78),1800,2.2,(0,-.25,.9)); area('Fill_Light',(-2.5,-1.3,1.8),(.72,.78,1),1300,2.5,(0,-.25,.9)); area('Rim_Light',(0,2,2.8),(.8,.85,1),1400,1.5,(0,0,.9))
    cams={'FrontThreeQuarter':camera('FrontThreeQuarter',(2.1,-2.5,2.6),(0,-.25,.9),42),'SideProfile':camera('SideProfile',(3.3,-.3,.95),(0,-.3,.9),42),'OperatorRecess':camera('OperatorRecess',(0,-1.35,1.28),(0,-.22,1.0),42)}
    scene=bpy.context.scene; scene.render.engine='CYCLES'; scene.cycles.samples=128; scene.cycles.use_denoising=True; scene.render.resolution_x=1920; scene.render.resolution_y=1080; scene.render.resolution_percentage=100; scene.render.image_settings.file_format='PNG'; scene.view_settings.view_transform='AgX'
    scene.world.color=(.15,.15,.15); (ROOT/'renders').mkdir(exist_ok=True)
    for name,cam in cams.items():
        scene.camera=cam; scene.render.filepath=str(ROOT/'renders'/f'{name.lower()}.png'); bpy.ops.render.render(write_still=True)
    report={'source':str(SOURCE),'source_dimensions_xyz_m':spans,'uniform_scale_to_1_75m':uniform,'axis_correction':[1,1,1],'final_dimensions_width_depth_height_m':dims,'voxel_size_m':VOXEL_SIZE,'component_count':component_count,'removed_tiny_component_faces':removed_faces,'source_sample_count':len(distances),'source_to_remesh_mean_distance_m':sum(distances)/len(distances),'source_to_remesh_max_sample_distance_m':max(distances),'triangles':triangles(obj),'boundary_edges':boundary,'nonmanifold_edges':nonmanifold,'back_plane_y_m':0.0,'screen_frontmost_surface_y_m':screen_frontmost_y,'screen_plane_y_m':screen_y,'screen_offset_m':.002,'screen_ray_samples':len(screen_hits),'screen_boolean_cut':False,'screen_plane':'DisplayPlane','render_samples':128,'resolution':[1920,1080]}
    if NO_BAY:
        report['keyboard_bay_skipped']=True
    else:
        report.update({'keyboard_bay_skipped':False,'keyboard_dimensions_m':[kw,kd,.06],'pocket_footprint_m':[pocket_w,pocket_d],'pocket_floor_z_m':floor_z,'shelf_top_z_m':shelf_top,'pocket_floor_area_m2':floor_area,'pocket_footprint_area_m2':footprint,'floor_area_relative_error':abs(floor_area/footprint-1),'keyboard_deck_thickness_m':.14})
    output_stem='terminal-nobay' if NO_BAY else 'terminal'
    report['keyboard_bay_skipped']=NO_BAY
    (ROOT/('nobay-build-report.json' if NO_BAY else 'build-report.json')).write_text(json.dumps(report,indent=2)+'\n')
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/f'{output_stem}.blend'))
    bpy.ops.export_scene.gltf(filepath=str(ROOT/f'{output_stem}.glb'),export_format='GLB',export_apply=True,export_image_format='AUTO',export_materials='EXPORT')
    print('BUILD_REPORT',json.dumps(report),flush=True)

if __name__=='__main__': main()
