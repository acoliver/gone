from pathlib import Path
import json, math
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
TERM = ROOT / 'termmodel4' / 'terminal-nobay-finished.blend'
KEYBOARD = ROOT / 'kbmodel' / 'keyboard.blend'
CAPTURES = ROOT / 'terminal' / 'captures'


def bounds(objects):
    points = [o.matrix_world @ Vector(c) for o in objects if o.type == 'MESH' for c in o.bound_box]
    return ([min(p[i] for p in points) for i in range(3)], [max(p[i] for p in points) for i in range(3)])


def box(name, dims, loc, mat, bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o=bpy.context.object; o.name=name; o.dimensions=dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if mat: o.data.materials.append(mat)
    if bevel:
        mod=o.modifiers.new('Rounded formed edges','BEVEL'); mod.width=bevel; mod.segments=3
        o.modifiers.new('Weighted corner normals','WEIGHTED_NORMAL')
    return o


def mesh(name, verts, faces, mat):
    data=bpy.data.meshes.new(name); data.from_pydata(verts, [], faces); data.materials.append(mat); data.update()
    obj=bpy.data.objects.new(name,data); bpy.context.collection.objects.link(obj); return obj


def camera(name, pos, target, lens):
    d=bpy.data.cameras.new(name); o=bpy.data.objects.new(name,d); bpy.context.collection.objects.link(o)
    o.location=pos; o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler(); d.lens=lens; return o


def area(name,pos,target,power,color,size):
    d=bpy.data.lights.new(name,'AREA'); o=bpy.data.objects.new(name,d); bpy.context.collection.objects.link(o)
    o.location=pos; o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler(); d.energy=power; d.color=color; d.shape='DISK'; d.size=size; return o


def main():
    bpy.ops.wm.open_mainfile(filepath=str(TERM)); scene=bpy.context.scene
    terminal=bpy.data.objects['Terminal_GeneratedFit']
    deps=bpy.context.evaluated_depsgraph_get(); ev=terminal.evaluated_get(deps); me=ev.to_mesh()
    verts=[ev.matrix_world@v.co for v in me.vertices]; polys=[list(p.vertices) for p in me.polygons]
    terminal_bvh=BVHTree.FromPolygons(verts,polys)
    flange_measurements=[]
    for x in (-.44,.44):
        for z in (1.0,1.1):
            loc,norm,idx,distance=terminal_bvh.ray_cast(Vector((x,-.8,z)),Vector((0,1,0)),.5)
            assert loc is not None, f'No terminal front hit at flange corner x={x}, z={z}'
            flange_measurements.append((x,z,loc.y))
    ev.to_mesh_clear()
    zmean=sum(p[1] for p in flange_measurements)/len(flange_measurements)
    ymean=sum(p[2] for p in flange_measurements)/len(flange_measurements)
    flange_slope=sum((p[1]-zmean)*(p[2]-ymean) for p in flange_measurements)/sum((p[1]-zmean)**2 for p in flange_measurements)
    flange_angle=-math.atan(flange_slope)
    def front_y(z): return ymean+flange_slope*(z-zmean)
    with bpy.data.libraries.load(str(KEYBOARD), link=False) as (src,dst):
        dst.objects=list(src.objects)
    keyboard=[]
    for obj in dst.objects:
        if obj and obj.type=='MESH' and obj.name!='Dark studio floor':
            bpy.context.collection.objects.link(obj); keyboard.append(obj)
            if obj.name in ('Left hand onset seal','Right hand vowel seal'): obj.hide_render=True; obj.hide_viewport=True
    keyboard=[o for o in keyboard if not o.hide_viewport]
    frame=bpy.data.objects['Rugged olive steel perimeter housing']
    steel=next(m for m in frame.data.materials if m)
    # Position the keyboard over the independent tray, with its rear edge just clear of the terminal.
    bpy.context.view_layer.update(); kblo,kbhi=bounds(keyboard)
    shift=Vector((-(kblo[0]+kbhi[0])/2, -0.638-kbhi[1], 1.008-kblo[2]))
    for o in keyboard: o.location += shift
    bpy.context.view_layer.update(); kblo,kbhi=bounds(keyboard)
    # Tray top slopes down toward the operator. The back flange follows the measured curved front face.
    rear_z=1.105; rear_y=front_y(rear_z)-.001; tray_front_y=rear_y-.27
    drop=.27*math.tan(math.radians(12)); front_z=rear_z-drop
    def top_z(y): return rear_z+(y-rear_y)*math.tan(math.radians(12))
    verts=[]
    for zoff in (0,-.008):
        for x,y,z in [(-.44,rear_y,rear_z),(.44,rear_y,rear_z),(.44,tray_front_y,front_z),(-.44,tray_front_y,front_z)]: verts.append((x,y,z+zoff))
    tray=mesh('Olive steel tray shelf 8mm',verts,[(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],steel)
    bevel=tray.modifiers.new('Rounded plate edges','BEVEL'); bevel.width=.003; bevel.segments=3
    # Front downturned lip, side returns, gussets, and vertical terminal flange.
    lip=box('Tray rounded downturned front lip',(0.88,.008,.020), (0,(tray_front_y+rear_y)/2,front_z-.014),steel,.004)
    for side in (-1,1):
        side_obj=box(f'Tray side return {side:+d}',(.008,.27,.015),(side*.436,(rear_y+tray_front_y)/2,(rear_z+front_z)/2-.002),steel,.003)
        side_obj.rotation_euler[0]=math.radians(-12)
    flange=box('Terminal mounting back flange',(0.88,.008,.10),(0,front_y(1.05)-.005,1.05),steel,.003)
    flange.rotation_euler[0]=flange_angle
    rubber=bpy.data.materials.new('Dark rubber gasket'); rubber.diffuse_color=(.018,.021,.019,1)
    gasket=box('Flange back perimeter rubber gasket',(.90,.010,.12),(0,front_y(1.05)+.006,1.05),rubber,.004)
    gasket.rotation_euler[0]=flange_angle
    gussets=[]
    for x in (-.34,.34):
        gussets.append(mesh(f'Tray triangular gusset {x:+.2f}',[(x,front_y(1.0)-.005,1.0),(x,tray_front_y+.03,top_z(tray_front_y+.03)-.012),(x,front_y(1.095)-.005,1.095)],[(0,1,2)],steel))
        # Gusset plate thickness along X.
        sol=gussets[-1].modifiers.new('Gusset thickness','SOLIDIFY'); sol.thickness=.006
    bolts=[]
    for x in (-.36,-.216,-.072,.072,.216,.36):
        bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=.008, depth=.004, location=(x,front_y(1.05)-.010,1.05), rotation=(math.pi/2+flange_angle,0,0))
        b=bpy.context.object; b.name=f'Flange hex bolt {len(bolts)+1:02d}'; b.data.materials.append(steel); bolts.append(b)
    tray_objs=[tray,lip,flange,gasket,*gussets,*bolts]+[o for o in bpy.context.scene.objects if o.name.startswith('Tray side return')]
    # Position the keyboard module to the 0.88 m shelf width and slope it with the tray.
    pivot=Vector((0,(rear_y+tray_front_y)/2,top_z((rear_y+tray_front_y)/2)+.008))
    for o in keyboard:
        o.location -= pivot
        o.rotation_euler[0]=math.radians(-12)
        o.location += pivot
    bpy.context.view_layer.update(); kblo,kbhi=bounds(keyboard)
    # Center the rotated module on the shelf, then set its lowest point 0.5 mm above the shelf plane.
    shelf_normal=Vector((0,-math.sin(math.radians(12)),math.cos(math.radians(12))))
    shelf_origin=Vector((0,rear_y,rear_z))
    rotated_points=[o.matrix_world@v.co for o in keyboard for v in o.data.vertices]
    dx=-(min(p.x for p in rotated_points)+max(p.x for p in rotated_points))/2
    dy=(rear_y+tray_front_y)/2-(min(p.y for p in rotated_points)+max(p.y for p in rotated_points))/2
    print('KEYBOARD_SHIFT', dx, dy, flush=True)
    for o in keyboard: o.location.y += dy
    for o in keyboard: o.location.x += dx
    bpy.context.view_layer.update()
    bottom_projection=min((o.matrix_world@v.co-shelf_origin).dot(shelf_normal) for o in keyboard for v in o.data.vertices)
    lift=.0005-bottom_projection
    for o in keyboard: o.matrix_world.translation += shelf_normal*lift
    bpy.context.view_layer.update(); kblo,kbhi=bounds(keyboard)
    keyboard_points=[o.matrix_world@v.co for o in keyboard for v in o.data.vertices]
    footprint_y=[p.y for p in keyboard_points]
    footprint_center=(min(footprint_y)+max(footprint_y))/2
    target_center=(rear_y+tray_front_y)/2
    tangent=Vector((0,math.cos(math.radians(12)),math.sin(math.radians(12))))
    tangent_shift=(target_center-footprint_center)/math.cos(math.radians(12))
    for o in keyboard: o.matrix_world.translation += tangent*tangent_shift
    bpy.context.view_layer.update()
    kblo,kbhi=bounds(keyboard)
    keyboard_points=[o.matrix_world@v.co for o in keyboard for v in o.data.vertices]
    footprint_y=[p.y for p in keyboard_points]
    print('KEYBOARD_FOOTPRINT', min(footprint_y), max(footprint_y), tray_front_y, rear_y, flush=True)
    assert min(footprint_y)>=tray_front_y+.005 and max(footprint_y)<=rear_y-.005, 'Keyboard footprint lacks 5 mm tray inset'
    bottom_rays=[]
    for x in (-.30,0,.30):
        for fraction in (.15,.5,.85):
            y=tray_front_y+(rear_y-tray_front_y)*fraction
            surface=Vector((x,y,top_z(y)))
            start=surface+shelf_normal*.0005
            hit,loc,normal,index,obj,material=scene.ray_cast(bpy.context.evaluated_depsgraph_get(),start,-shelf_normal,distance=.01)
            assert hit and obj and obj.name=='Olive steel tray shelf 8mm', f'Keyboard bottom ray missed shelf at {(x,y)}'
            gap=(start-loc).dot(shelf_normal)
            bottom_rays.append(gap)
            assert abs(gap-.0005)<=.001, f'Keyboard shelf clearance {gap:.6f}m is outside tolerance'
    # Place screen image plane over the existing measured display surface.
    perceived=bpy.data.images.load(str(CAPTURES/'console-inactive-perceived.png'),check_existing=True); perceived.pack()
    native=bpy.data.images.load(str(CAPTURES/'console-inactive-native.png'),check_existing=True); native.pack()
    screen=bpy.data.materials.get('Screen'); screen.use_nodes=True; nt=screen.node_tree; nt.nodes.clear()
    uv=nt.nodes.new('ShaderNodeTexCoord'); tex=nt.nodes.new('ShaderNodeTexImage'); tex.image=perceived
    bs=nt.nodes.new('ShaderNodeBsdfPrincipled'); bs.inputs['Emission Strength'].default_value=8
    out=nt.nodes.new('ShaderNodeOutputMaterial'); nt.links.new(uv.outputs['UV'],tex.inputs['Vector']); nt.links.new(tex.outputs['Color'],bs.inputs['Emission Color']); nt.links.new(bs.outputs['BSDF'],out.inputs['Surface'])
    native_screen=bpy.data.materials.new('Screen Native Emissive'); native_screen.use_nodes=True
    native_nodes=native_screen.node_tree.nodes; native_nodes.clear()
    native_uv=native_nodes.new('ShaderNodeTexCoord'); native_tex=native_nodes.new('ShaderNodeTexImage'); native_tex.image=native
    native_bs=native_nodes.new('ShaderNodeBsdfPrincipled'); native_bs.inputs['Emission Strength'].default_value=8
    native_out=native_nodes.new('ShaderNodeOutputMaterial')
    native_screen.node_tree.links.new(native_uv.outputs['UV'],native_tex.inputs['Vector'])
    native_screen.node_tree.links.new(native_tex.outputs['Color'],native_bs.inputs['Emission Color'])
    native_screen.node_tree.links.new(native_bs.outputs['BSDF'],native_out.inputs['Surface'])
    display=bpy.data.objects.new('DisplayPlane',bpy.data.meshes.new('DisplayPlane')); bpy.context.collection.objects.link(display)
    display_mesh=display.data; display_mesh.from_pydata([(-.27,-.511,1.345),(.27,-.511,1.345),(.27,-.511,1.625),(-.27,-.511,1.625)],[],[(0,1,2,3)]); display_mesh.materials.append(screen)
    # Verify the flange's 1 mm offset at nine points across its face.
    validation_failures=[]
    corner_gaps=[]; flange_gap_samples=[]
    for x in (-.39,0,.39):
        for z in (1.0,1.05,1.10):
            loc,norm,idx,distance=terminal_bvh.ray_cast(Vector((x,-.8,z)),Vector((0,1,0)),.5)
            assert loc is not None, f'No terminal front hit at flange sample x={x}, z={z}'
            gap=abs((front_y(z)-.001)-loc.y)
            flange_gap_samples.append(gap)
            limit=.003 if x==0 else .012
            if gap>limit: validation_failures.append(f'Flange gap {gap:.4f}m exceeds {limit:.3f}m at x={x}, z={z}')
            print('FLANGE_SAMPLE', x, z, tuple(loc), gap, flush=True)
    flange_gap=max(flange_gap_samples)
    assert len(flange_gap_samples)==9
    # BVH triangle overlap checks for shelf/brackets and all keyboard components against terminal.
    def tree(obj):
        e=obj.evaluated_get(deps); m=e.to_mesh(); vs=[e.matrix_world@v.co for v in m.vertices]; fs=[list(p.vertices) for p in m.polygons]; t=BVHTree.FromPolygons(vs,fs); e.to_mesh_clear(); return t
    termtree=tree(terminal); collisions=[]
    tray_penetrations={}
    for o in tray_objs:
        if o is flange: continue
        penetrations=[]
        for vert in o.data.vertices:
            point=o.matrix_world@vert.co
            loc,norm,index,distance=terminal_bvh.ray_cast(point,Vector((0,1,0)),.5)
            if loc is not None: penetrations.append(distance)
        tray_penetrations[o.name]=max(penetrations,default=0.0)
    max_penetration=max(tray_penetrations.values(),default=0.0)
    forward_shift=max_penetration+.001
    for o in tray_objs+keyboard: o.location.y-=forward_shift
    bpy.context.view_layer.update()
    for o in keyboard+tray_objs:
        if termtree.overlap(tree(o)): collisions.append(o.name)
    keyboard_tray_collisions=[]
    for ko in keyboard:
        kt=tree(ko)
        for to in tray_objs:
            if kt.overlap(tree(to)): keyboard_tray_collisions.append((ko.name,to.name))
    if keyboard_tray_collisions: validation_failures.append(f'Keyboard intersects tray: {keyboard_tray_collisions}')
    if collisions: validation_failures.append(f'Tray or keyboard intersects terminal: {collisions}')
    if flange_gap>.003: validation_failures.append(f'Flange gap {flange_gap:.4f}m exceeds 3mm')
    caps=[o for o in keyboard if o.name.startswith('Keycap ')]; assert len(caps)==29
    eye=Vector((0,tray_front_y-.50,1.65)); visible=[]
    for cap in caps:
        faces=[(cap.matrix_world@p.center,(cap.matrix_world.to_3x3()@p.normal).normalized()) for p in cap.data.polygons]
        center=max((p for p in faces if p[1].z>.75),key=lambda p:p[0].z)[0]
        hit,loc,n,fi,obj,mat=scene.ray_cast(deps,eye,(center-eye).normalized(),distance=(center-eye).length+.003)
        visible.append(bool(hit and obj and obj.name==cap.name))
    screen_center=Vector((0,-.511,1.485)); ray=screen_center-eye
    hit,loc,n,fi,hitobj,mat=scene.ray_cast(deps,eye,ray.normalized(),distance=ray.length+.002)
    screen_clear=bool(hit and hitobj and hitobj.name=='DisplayPlane')
    if sum(visible)!=29: validation_failures.append(f'Only {sum(visible)}/29 keycaps visible')
    if not screen_clear: validation_failures.append(f'Screen ray blocked by {hitobj.name if hitobj else None}')
    # Studio, lighting, cameras, and required Cycles renders.
    scene.render.engine='CYCLES'; scene.cycles.samples=128; scene.cycles.use_denoising=True
    scene.render.resolution_x=1920; scene.render.resolution_y=1080; scene.render.resolution_percentage=100
    scene.view_settings.view_transform='AgX'; scene.render.image_settings.file_format='PNG'
    look=area('Lookdev key',(-1.8,-2.2,3.1),(0,-.3,.9),300,(1,.98,.68),1.35); fill=area('Lookdev fill',(0,-2.3,1.6),(0,-.3,.9),500,(.88,1,.68),2.2); rim=area('Lookdev rim',(.2,1.4,2.8),(0,-.1,1),180,(1,.98,.72),1.1)
    red=area('Operator red',(0,-.6,2.35),(0,-.4,1.1),300,(1,.012,.006),.45)
    center=Vector((0,-.3,.88)); wide=camera('Front three-quarter',(1.55,-1.85,2.08),center,30); side=camera('Side profile',(-1.8,-.9,1.0),center,45); operator=camera('Operator looking down',(0,tray_front_y-.5,1.65),(0,-.75,1.05),35)
    jobs=[('threequarter',wide,False),('side',side,False),('operator',operator,False),('operator-red',operator,True)]
    for label,cam,isred in jobs:
        scene.camera=cam; red.hide_render=not isred
        for l in (look,fill,rim): l.hide_render=isred
        scene.render.filepath=str(OUT/f'{label}.png'); bpy.ops.render.render(write_still=True)
    # Contact sheet from the required three lookdev views and red operator view.
    import subprocess
    py='/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python'
    subprocess.run([py,'-c',"from PIL import Image,ImageOps,ImageDraw; from pathlib import Path; p=Path(r'%s'); files=['threequarter.png','side.png','operator.png','operator-red.png']; ims=[Image.open(p/f).convert('RGB').resize((640,360)) for f in files]; out=Image.new('RGB',(1280,720)); [out.paste(im,((i%%2)*640,(i//2)*360)) for i,im in enumerate(ims)]; out.save(p/'contact.png')"%OUT],check=True)
    report={'tray_dimensions_m':{'width':.88,'depth':.27,'plate_thickness':.008,'front_lip_drop':.020,'side_lip_height':.015,'tilt_degrees':12},'terminal_front_plane':{'slope_dy_dz':flange_slope,'rotation_x_degrees':math.degrees(flange_angle),'offset_m':.001},'tray_bounds_min_m':bounds(tray_objs)[0],'tray_bounds_max_m':bounds(tray_objs)[1],'keyboard_bounds_min_m':kblo,'keyboard_bounds_max_m':kbhi,'flange_gap_samples_m':flange_gap_samples,'max_flange_gap_m':flange_gap,'keyboard_terminal_tray_bvh_intersections':collisions,'keyboard_tray_intersections':keyboard_tray_collisions,'keyboard_shelf_ray_gaps_m':bottom_rays,'tray_penetration_by_object_m':tray_penetrations,'tray_forward_shift_m':forward_shift,'validation_failures':validation_failures,'keycap_visibility':{'visible':sum(visible),'total':len(caps),'eye_m':list(eye)},'screen_ray':{'clear':screen_clear,'first_hit':hitobj.name if hitobj else None,'screen_center_m':list(screen_center)},'screen_images':[str(CAPTURES/'console-inactive-perceived.png'),str(CAPTURES/'console-inactive-native.png')],'render_settings':{'engine':'Cycles','samples':128,'denoising':True,'resolution_px':[1920,1080]},'files':['threequarter.png','side.png','operator.png','operator-red.png','contact.png','assembly.blend','assembly-report.json','terminal-with-keyboard.glb'],'checks_passed':not validation_failures and sum(visible)==29 and screen_clear}
    scene.camera=wide; scene.render.filepath=str(OUT/'threequarter.png'); bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'assembly.blend'))
    bpy.ops.export_scene.gltf(filepath=str(OUT/'terminal-with-keyboard.glb'),export_format='GLB',export_yup=True)
    (OUT/'assembly-report.json').write_text(json.dumps(report,indent=2)+'\n'); print(json.dumps(report,indent=2))

if __name__=='__main__': main()
