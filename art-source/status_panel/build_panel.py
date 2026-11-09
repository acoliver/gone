from pathlib import Path
import json, math, sys
import bpy, bmesh
from mathutils import Vector

ROOT=Path(__file__).resolve().parent
VOXEL=.009
FRONT=-1

def active(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active=o

def join(meshes,name):
    active(meshes[0])
    for o in meshes: o.select_set(True)
    bpy.ops.object.join(); o=bpy.context.object; o.name=name; return o

def bounds(o):
    co=[v.co[:] for v in o.data.vertices]
    return [min(p[i] for p in co) for i in range(3)],[max(p[i] for p in co) for i in range(3)]
def mat(name,color,metal=0,rough=.5):
    m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.use_nodes=True
    b=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'); b.inputs['Base Color'].default_value=(*color,1); b.inputs['Metallic'].default_value=metal; b.inputs['Roughness'].default_value=rough
    return m
def cube(name,loc,dims,material,bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc); o=bpy.context.object; o.name=name; o.dimensions=dims; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); o.data.materials.append(material)
    if bevel:
        mod=o.modifiers.new('Edge radii','BEVEL'); mod.width=bevel; mod.segments=3; active(o); bpy.ops.object.modifier_apply(modifier=mod.name)
    return o
def uv_sphere(name,loc,scale,material):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,radius=1,location=loc); o=bpy.context.object; o.name=name; o.scale=scale; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); o.data.materials.append(material); bpy.ops.object.shade_smooth(); return o
def cylinder(name,loc,radius,depth,axis,material,vertices=20):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=radius,depth=depth,location=loc); o=bpy.context.object; o.name=name
    if axis=='X': o.rotation_euler[1]=math.pi/2
    if axis=='Y': o.rotation_euler[0]=math.pi/2
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=True); o.data.materials.append(material); return o
def camera(name,location,target,lens=50):
    d=bpy.data.cameras.new(name); o=bpy.data.objects.new(name,d); bpy.context.collection.objects.link(o); o.location=location; o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler(); d.lens=lens; return o
def area(name,loc,power,color,size,target):
    d=bpy.data.lights.new(name,'AREA'); d.energy=power; d.color=color; d.shape='DISK'; d.size=size; o=bpy.data.objects.new(name,d); bpy.context.collection.objects.link(o); o.location=loc; o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
def silhouette_iou(obj,alpha_path):
    W,H=256,128
    img=bpy.data.images.load(str(alpha_path),check_existing=True)
    pix=[0.0]*(img.size[0]*img.size[1]*4); img.pixels.foreach_get(pix)
    xs=[]; ys=[]
    for y in range(img.size[1]):
        for x in range(img.size[0]):
            if pix[(y*img.size[0]+x)*4+3]>.5: xs.append(x); ys.append(y)
    x0,x1=min(xs),max(xs)+1; y0,y1=min(ys),max(ys)+1
    target=[]
    for y in range(H):
        sy=y0+min(y1-y0-1,int(y*(y1-y0)/H))
        for x in range(W):
            sx=x0+min(x1-x0-1,int(x*(x1-x0)/W))
            target.append(pix[(sy*img.size[0]+sx)*4+3]>.5)
    lo,hi=bounds(obj); cx=(lo[0]+hi[0])/2; cz=(lo[2]+hi[2])/2
    width=hi[0]-lo[0]; height=hi[2]-lo[2]
    bpy.context.scene.render.engine='CYCLES'; bpy.context.scene.cycles.samples=1
    bpy.context.scene.render.resolution_x=W; bpy.context.scene.render.resolution_y=H; bpy.context.scene.render.resolution_percentage=100
    bpy.context.scene.render.film_transparent=False
    if bpy.context.scene.world is None: bpy.context.scene.world=bpy.data.worlds.new('SilhouetteWorld')
    bpy.context.scene.world.color=(0,0,0)
    d=bpy.data.cameras.new('SilhouetteCamera'); cam=bpy.data.objects.new('SilhouetteCamera',d); bpy.context.collection.objects.link(cam)
    cam.location=(cx,-3,cz); cam.rotation_euler=(Vector((cx,0,cz))-cam.location).to_track_quat('-Z','Y').to_euler(); d.type='ORTHO'; d.ortho_scale=max(width,height*W/H)*1.002
    bpy.context.scene.camera=cam
    material=bpy.data.materials.new('SilhouetteWhite'); material.use_nodes=True; material.node_tree.nodes.clear()
    em=material.node_tree.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value=(1,1,1,1); out=material.node_tree.nodes.new('ShaderNodeOutputMaterial'); material.node_tree.links.new(em.outputs[0],out.inputs['Surface'])
    old=list(obj.data.materials); obj.data.materials.clear(); obj.data.materials.append(material)
    bpy.context.scene.render.image_settings.file_format='PNG'; bpy.context.scene.render.filepath=str(ROOT/'logs/silhouette-candidate.png')
    bpy.ops.render.render(write_still=True)
    result=bpy.data.images.load(str(ROOT/'logs/silhouette-candidate.png'),check_existing=False); rp=[0.0]*(W*H*4); result.pixels.foreach_get(rp)
    inter=union=0
    for i,a in enumerate(target):
        rendered=rp[i*4]>.5
        inter+=a and rendered; union+=a or rendered
    obj.data.materials.clear()
    for m in old: obj.data.materials.append(m)
    bpy.data.objects.remove(cam,do_unlink=True); bpy.data.cameras.remove(d)
    return inter/union if union else 0

def main():
    candidates=sorted((ROOT/'meshes').glob('panel-s*.glb'))
    if len(candidates)<2: raise RuntimeError('Both Hunyuan candidate meshes are required')
    alpha=ROOT/'inputs/front-s410-rgba.png'
    scores=[]
    for path in candidates:
        bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=str(path))
        meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']; obj=join(meshes,'candidate')
        scores.append({'mesh':path.name,'silhouette_iou':silhouette_iou(obj,alpha),'vertices':len(obj.data.vertices),'faces':len(obj.data.polygons)})
    selected=max(scores,key=lambda r:r['silhouette_iou'])['mesh']
    bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=str(ROOT/'meshes'/selected))
    obj=join([o for o in bpy.context.scene.objects if o.type=='MESH'],'Panel_ArmoredBody')
    # Drop disconnected flecks below half a percent of faces, preserving genuine assembly parts.
    bm=bmesh.new(); bm.from_mesh(obj.data); remaining=set(bm.faces); comps=[]
    while remaining:
        seed=remaining.pop(); comp=[seed]; stack=[seed]
        while stack:
            f=stack.pop()
            for e in f.edges:
                for q in e.link_faces:
                    if q in remaining: remaining.remove(q); comp.append(q); stack.append(q)
        comps.append(comp)
    total=sum(len(c) for c in comps)
    for c in comps:
        if len(c)<total*.005: bmesh.ops.delete(bm,geom=c,context='FACES')
    bm.to_mesh(obj.data); bm.free(); obj.data.update()
    lo,hi=bounds(obj); raw=[hi[i]-lo[i] for i in range(3)]
    # Uniformly set the height, then correct width and depth to the known enclosure envelope.
    scale=1.40/raw[2]
    for v in obj.data.vertices:
        v.co.x=(v.co.x-(lo[0]+hi[0])/2)*scale
        v.co.y=(v.co.y-hi[1])*scale
        v.co.z=(v.co.z-lo[2])*scale
    obj.data.update(); lo,hi=bounds(obj); scaled=[hi[i]-lo[i] for i in range(3)]
    corr=[2.80/scaled[0],1.0,1.0]
    if any(abs(c-1)>.15 for c in corr):
        print('AXIS_CORRECTION_OVER_15_PERCENT',corr,flush=True)
    for v in obj.data.vertices: v.co.x*=corr[0]; v.co.y*=corr[1]
    # Crop the excess rear depth without compressing the generated shape, then flatten the cut onto the wall plane.
    lo,hi=bounds(obj)
    depth_before_crop=hi[1]-lo[1]
    cut_y=lo[1]+.35
    bm=bmesh.new(); bm.from_mesh(obj.data)
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-6,plane_co=(0,cut_y,0),plane_no=(0,1,0),clear_outer=True,clear_inner=False)
    cut_edges=[e for e in bm.edges if e.is_boundary and all(abs(v.co.y-cut_y)<.012 for v in e.verts)]
    if cut_edges: bmesh.ops.holes_fill(bm,edges=cut_edges,sides=0)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(obj.data); bm.free(); obj.data.update()
    for v in obj.data.vertices: v.co.y-=cut_y
    obj.data.update()
    # Voxel-remesh the single generated shell and clip a planar wall-facing rear.
    obj.data.remesh_voxel_size=VOXEL; obj.data.remesh_voxel_adaptivity=0
    mod=obj.modifiers.new('WatertightVoxelSolid','REMESH'); mod.mode='VOXEL'; mod.voxel_size=VOXEL; mod.adaptivity=0
    active(obj); bpy.ops.object.modifier_apply(modifier=mod.name)
    bm=bmesh.new(); bm.from_mesh(obj.data)
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-6,plane_co=(0,0,0),plane_no=(0,1,0),clear_outer=True,clear_inner=False)
    edges=[e for e in bm.edges if e.is_boundary and all(abs(v.co.y)<.012 for v in e.verts)]
    if edges: bmesh.ops.holes_fill(bm,edges=edges,sides=0)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(obj.data); bm.free(); obj.data.update()
    rem=obj.modifiers.new('CloseWallPlane','REMESH'); rem.mode='VOXEL'; rem.voxel_size=VOXEL; rem.adaptivity=0; active(obj); bpy.ops.object.modifier_apply(modifier=rem.name)
    lo,hi=bounds(obj); dims=[hi[i]-lo[i] for i in range(3)]
    # Restore the known front envelope after remeshing. Depth is established by the flattened crop.
    adjust=[2.80/dims[0],1.0,1.40/dims[2]]
    for v in obj.data.vertices: v.co.x*=adjust[0]; v.co.y*=adjust[1]; v.co.z*=adjust[2]
    obj.data.update(); lo,hi=bounds(obj)
    for v in obj.data.vertices: v.co.y-=hi[1]
    obj.data.update(); dims=[bounds(obj)[1][i]-bounds(obj)[0][i] for i in range(3)]
    if not (.33<=dims[1]<=.37): raise RuntimeError(f'Flattened rear crop depth outside target tolerance: {dims[1]}')
    bm=bmesh.new(); bm.from_mesh(obj.data); boundary=sum(e.is_boundary for e in bm.edges); nonmanifold=sum(not e.is_manifold for e in bm.edges); bm.free()
    if boundary or nonmanifold: raise RuntimeError(f'Watertight check failed boundary={boundary} nonmanifold={nonmanifold}')
    olive=mat('OliveDrab_WornMetal',(.16,.18,.075),.32,.56); metal=mat('RivetSteel',(.12,.11,.075),.72,.38); rubber=mat('RubberBumper',(.012,.015,.013),.02,.8); black=mat('Screen',(.003,.005,.006),.08,.12)
    # Scan texture on the shell, tinted toward the approved olive paint; subtle pointiness wear.
    steel=ROOT.parent/'rustlook/art-source/steel/rusty_metal_04_albedo.jpg'
    green=ROOT.parent/'rustlook/art-source/steel/green_metal_rust_albedo.jpg'
    nt=olive.node_tree; nt.nodes.clear(); n=nt.nodes; l=nt.links
    bs=n.new('ShaderNodeBsdfPrincipled'); output=n.new('ShaderNodeOutputMaterial'); l.new(bs.outputs[0],output.inputs['Surface'])
    coord=n.new('ShaderNodeTexCoord'); mapping=n.new('ShaderNodeVectorMath'); mapping.operation='SCALE'; mapping.inputs[3].default_value=7; l.new(coord.outputs['Generated'],mapping.inputs[0])
    tex=n.new('ShaderNodeTexImage'); tex.image=bpy.data.images.load(str(green),check_existing=True); tex.image.colorspace_settings.name='sRGB'; l.new(mapping.outputs[0],tex.inputs['Vector'])
    tint=n.new('ShaderNodeMixRGB'); tint.blend_type='MULTIPLY'; tint.inputs[0].default_value=.62; tint.inputs[2].default_value=(1.49,1.12,.66,1); l.new(tex.outputs['Color'],tint.inputs[1])
    geom=n.new('ShaderNodeNewGeometry'); edge=n.new('ShaderNodeMapRange'); edge.inputs['From Min'].default_value=.72; edge.inputs['From Max'].default_value=.93; edge.inputs['To Min'].default_value=0; edge.inputs['To Max'].default_value=.68; edge.clamp=True; l.new(geom.outputs['Pointiness'],edge.inputs['Value'])
    rusty=n.new('ShaderNodeTexImage'); rusty.image=bpy.data.images.load(str(steel),check_existing=True); rusty.image.colorspace_settings.name='sRGB'; l.new(mapping.outputs[0],rusty.inputs['Vector'])
    mix=n.new('ShaderNodeMixRGB'); mix.blend_type='MIX'; l.new(edge.outputs['Result'],mix.inputs[0]); l.new(tint.outputs[0],mix.inputs[1]); l.new(rusty.outputs['Color'],mix.inputs[2])
    bs=next(x for x in n if x.type=='BSDF_PRINCIPLED'); l.new(mix.outputs[0],bs.inputs['Base Color']); bs.inputs['Metallic'].default_value=.02; bs.inputs['Roughness'].default_value=.68
    obj.data.materials.append(olive)
    # Uniform screen placement is deliberately independent of generated image bevel geometry.
    sy=hi[1] if False else -dims[1]-.012
    z0=(1.40-1.02)/2
    bpy.ops.mesh.primitive_plane_add(size=1,location=(0,sy,z0+1.02/2),rotation=(math.pi/2,0,0)); screen=bpy.context.object; screen.name='DisplayPlane'; screen.dimensions=(2.40,1.02,0); bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); screen.data.materials.append(black)
    screen['dimensions_m']=[2.40,1.02]; screen['aspect_ratio']=2.352941
    socket=bpy.data.objects.new('ScreenSocket',None); bpy.context.collection.objects.link(socket); socket.location=(0,sy,z0+1.02/2); socket.rotation_euler=(math.pi/2,0,0); socket.empty_display_type='CIRCLE'; socket.empty_display_size=.05; socket['normal_local']=[0,0,1]
    # Hardware on the face: a rivet border, corner bumpers, rib bridge hood, glands, and short wall conduits.
    fy=sy-.012
    for x in [-1.28,-.96,-.64,-.32,0,.32,.64,.96,1.28]:
        for z in [.115,1.285]: uv_sphere('BezelRivet',(x,fy,z),(.018,.012,.018),metal)
    for z in [.32,.70,1.08]:
        for x in [-1.31,1.31]: uv_sphere('BezelRivet',(x,fy,z),(.018,.012,.018),metal)
    for x in [-1.32,1.32]:
        for z in [.08,1.32]: cube('RubberCornerBumper',(x,sy-.04,z),(.105,.07,.105),rubber,.018)
    # The ribs bridge the top hood in shallow relief above the screen.
    hood=cube('RibBridgeHood',(0,-.20,1.365),(2.72,.29,.07),olive,.02)
    for z in [1.345,1.365,1.385]: cube('HoodCrossRib',(0,-.20,z),(2.66,.30,.012),metal,.004)
    for x in [-1.12,1.12]:
        for z in [.18,1.22]:
            cylinder('CableGland',(x,-.18,z),.045,.11,'Y',metal)
        cylinder('WallConduit',(x,-.005,.70),.025,.24,'Y',olive)
        cylinder('WallEntryCollar',(x,.001,.70),.05,.04,'Y',metal)
    # Preserve complete screen target view and render cameras.
    floor_mat=mat('Backdrop',(.085,.095,.09),0,.9)
    bpy.ops.mesh.primitive_plane_add(size=30,location=(0,0,-.02)); bpy.context.object.name='StudioFloor'; bpy.context.object.data.materials.append(floor_mat)
    area('Key',(-2.8,-3.4,3.5),1800,(1,1,1),3,(0,-.15,.7)); area('Fill',(3,-2.4,1.7),1200,(1,1,1),2.6,(0,-.2,.7)); area('Rim',(0,1.4,2.8),1500,(1,1,1),1.7,(0,-.1,.7))
    cams={'front':camera('FrontCamera',(0,-4.6,.70),(0,-.15,.70),48),'threequarter':camera('ThreeQuarterCamera',(2.5,-3.1,2.2),(0,-.15,.70),48),'side':camera('SideCamera',(3.7,-.45,.70),(0,-.15,.70),48)}
    scene=bpy.context.scene; scene.render.engine='CYCLES'; scene.cycles.samples=128; scene.cycles.use_denoising=True; scene.render.resolution_x=1920; scene.render.resolution_y=1080; scene.render.resolution_percentage=100; scene.render.image_settings.file_format='PNG'; scene.view_settings.view_transform='AgX'
    if scene.world is None: scene.world=bpy.data.worlds.new('PanelStudioWorld')
    scene.world.color=(.10,.10,.10)
    (ROOT/'renders').mkdir(exist_ok=True)
    for name,cam in cams.items():
        scene.camera=cam; scene.render.filepath=str(ROOT/'renders'/f'panel-{name}.png'); bpy.ops.render.render(write_still=True)
    # Emissive board image render; native image preserved beside the perceived screen texture.
    board=ROOT.parent/'display/board-v2-perceived.png'; board_native=ROOT.parent/'display/board-v2-native.png'
    im=bpy.data.images.load(str(board),check_existing=True)
    sm=bpy.data.materials.new('ScreenBoardEmission'); sm.use_nodes=True; sn=sm.node_tree.nodes; sl=sm.node_tree.links; sn.clear(); ti=sn.new('ShaderNodeTexImage'); ti.image=im; ti.image.colorspace_settings.name='sRGB'; em=sn.new('ShaderNodeEmission'); out=sn.new('ShaderNodeOutputMaterial'); sl.new(ti.outputs['Color'],em.inputs['Color']); sl.new(em.outputs[0],out.inputs['Surface']); screen.data.materials.clear(); screen.data.materials.append(sm)
    scene.camera=cams['front']; scene.render.filepath=str(ROOT/'renders/panel-board-v2-perceived.png'); bpy.ops.render.render(write_still=True)
    # Repack body UVs and bake base albedo, tangent normal, and ORM at 2048.
    active(obj); bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.uv.smart_project(island_margin=.018,angle_limit=math.radians(66),correct_aspect=True,scale_to_bounds=False); bpy.ops.object.mode_set(mode='OBJECT')
    scene.render.bake.margin=16; scene.render.bake.margin_type='EXTEND'; scene.cycles.samples=16
    nt=olive.node_tree; bs=next(x for x in nt.nodes if x.type=='BSDF_PRINCIPLED'); output=next(x for x in nt.nodes if x.type=='OUTPUT_MATERIAL')
    uv=nt.nodes.new('ShaderNodeTexCoord').outputs['UV']; targetnode=nt.nodes.new('ShaderNodeTexImage')
    def bake(name,kind,colorspace='Non-Color',socket=None):
        image=bpy.data.images.new(name,2048,2048,alpha=False); image.colorspace_settings.name=colorspace; targetnode.image=image; nt.nodes.active=targetnode
        if socket:
            emit=nt.nodes.new('ShaderNodeEmission'); nt.links.new(socket,emit.inputs['Color']); nt.links.new(emit.outputs[0],output.inputs['Surface'])
        else: nt.links.new(bs.outputs[0],output.inputs['Surface'])
        bpy.ops.object.bake(type=kind,uv_layer=obj.data.uv_layers.active.name)
        image.filepath_raw=str(ROOT/'textures'/f'panel-{name.lower()}.png'); image.file_format='PNG'; image.save(); image.pack()
        return image
    albedo=bake('Albedo','EMIT','sRGB',mix.outputs[0])
    normal=bake('Normal','NORMAL')
    # Use baked AO in R, fixed roughness and metallic in G/B.
    ao=bake('AO','AO')
    ao_tex=nt.nodes.new('ShaderNodeTexImage'); ao_tex.image=ao; nt.links.new(uv,ao_tex.inputs['Vector']); sep=nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(ao_tex.outputs['Color'],sep.inputs[0]); combine=nt.nodes.new('ShaderNodeCombineColor'); nt.links.new(sep.outputs[0],combine.inputs[0]); combine.inputs[1].default_value=.56; combine.inputs[2].default_value=.02
    orm=bake('ORM','EMIT','Non-Color',combine.outputs[0])
    # Runtime shader uses the delivered maps. Keep scans embedded through packed baked output.
    nt.nodes.clear(); links=nt.links; nodes=nt.nodes; co=nodes.new('ShaderNodeTexCoord')
    def texmap(image,label,space):
        t=nodes.new('ShaderNodeTexImage'); t.image=image; t.label=label; t.image.colorspace_settings.name=space; links.new(co.outputs['UV'],t.inputs['Vector']); return t.outputs['Color']
    col=texmap(albedo,'Baked albedo','sRGB'); ormcol=texmap(orm,'Baked ORM','Non-Color'); nmcol=texmap(normal,'Baked normal','Non-Color')
    bs2=nodes.new('ShaderNodeBsdfPrincipled'); links.new(col,bs2.inputs['Base Color']); split=nodes.new('ShaderNodeSeparateColor'); links.new(ormcol,split.inputs[0]); links.new(split.outputs[1],bs2.inputs['Roughness']); links.new(split.outputs[2],bs2.inputs['Metallic']); nm=nodes.new('ShaderNodeNormalMap'); links.new(nmcol,nm.inputs['Color']); links.new(nm.outputs[0],bs2.inputs['Normal']); oo=nodes.new('ShaderNodeOutputMaterial'); links.new(bs2.outputs[0],oo.inputs['Surface'])
    screen.data.materials.clear(); screen.data.materials.append(black)
    scene.cycles.samples=128
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'panel.blend'))
    body=bpy.data.objects['Panel_ArmoredBody']
    budget=body.modifiers.new('Runtime triangle budget','DECIMATE'); budget.ratio=.17
    active(body); bpy.ops.object.modifier_apply(modifier=budget.name)
    export_objects=[bpy.data.objects[name] for name in ('Panel_ArmoredBody','DisplayPlane','ScreenSocket')]
    bpy.ops.object.select_all(action='DESELECT')
    for export_object in export_objects: export_object.select_set(True)
    screen_object=bpy.data.objects['DisplayPlane']
    active(screen_object); bpy.ops.object.transform_apply(location=False,rotation=True,scale=False)
    bpy.data.objects['ScreenSocket'].rotation_euler=(0,0,0)
    bpy.context.view_layer.objects.active=export_objects[0]
    bpy.ops.export_scene.gltf(filepath=str(ROOT/'panel.glb'),export_format='GLB',export_apply=True,export_image_format='AUTO',export_materials='EXPORT',use_selection=True)
    report={'candidates':scores,'selected_mesh':selected,'uniform_height_scale':scale,'axis_correction_before_remesh':corr,'generated_depth_after_uniform_scale_m':depth_before_crop,'depth_reduced_by_flattened_rear_crop':True,'post_remesh_adjustment':adjust,'final_dimensions_width_depth_height_m':dims,'depth_target_m':.35,'voxel_size_m':VOXEL,'boundary_edges':boundary,'nonmanifold_edges':nonmanifold,'screen_dimensions_m':[2.40,1.02],'screen_aspect':2.4/1.02,'textures':['panel-albedo.png','panel-normal.png','panel-orm.png','panel-ao.png'],'texture_resolution':2048,'renders':['panel-front.png','panel-threequarter.png','panel-side.png','panel-board-v2-perceived.png'],'board_native_source':str(board_native),'selected_shape_front_silhouette_iou':next(r['silhouette_iou'] for r in scores if r['mesh']==selected)}
    (ROOT/'build-report.json').write_text(json.dumps(report,indent=2)+'\n'); print('BUILD_REPORT',json.dumps(report),flush=True)
if __name__=='__main__': main()
