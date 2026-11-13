"""Stage-two CPU studio, identical mesh/camera lanes and effect-off controls."""
import json
import math
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
ROOT = HERE.parents[3]
MASTER = ROOT / 'assets/props/quarters/dress_uniform/medal'


def image(path, color=False):
    im = bpy.data.images.load(str(path), check_existing=True)
    im.colorspace_settings.name = 'sRGB' if color else 'Non-Color'
    return im


def first_hit_masks(out, objects):
    size=672
    for obj in objects:
        mesh=obj.data
        tree=BVHTree.FromPolygons([v.co[:] for v in mesh.vertices],[p.vertices[:] for p in mesh.polygons],all_triangles=True)
        features=np.array([a.value for a in mesh.attributes['FeatureRegion'].data])
        regions=np.full((size,size),-1,np.int16)
        triangles=np.full((size,size),-1,np.int32)
        for row in range(size):
            z=.002+(.5-(row+.5)/size)*.043
            for col in range(size):
                x=((col+.5)/size-.5)*.043
                _,_,face,_=tree.ray_cast(Vector((x,-.12,z)),Vector((0,1,0)),.3)
                if face is not None:regions[row,col]=features[face];triangles[row,col]=face
        key='high' if obj.name=='MedalHigh' else 'low'
        np.save(out/(key+'-first-hit-regions.npy'),regions)
        np.save(out/(key+'-first-hit-triangles.npy'),triangles)




def transfer_uv(high, low, out):
    """Project a high face into its corresponding low chart without moving either mesh."""
    names = json.loads(low['feature_names'])
    a = np.array([x.value for x in low.data.attributes['FeatureRegion'].data])
    vertices = [v.co[:] for v in low.data.vertices]
    polygons = [p.vertices[:] for p in low.data.polygons]
    uv = np.array([x.uv[:] for x in low.data.uv_layers.active.data]).reshape(-1, 3, 2)
    trees = {}
    for i in range(len(names)):
        ids = np.flatnonzero(a == i)
        trees[i] = (BVHTree.FromPolygons(vertices, [polygons[k] for k in ids], all_triangles=True), ids)
    layer = high.data.uv_layers.new(name='MedalUV')
    regions = high.data.attributes['FeatureRegion']
    outside = 0
    atlas_data=np.load(out/'atlas-context.npz')
    atlas={'mask':atlas_data['mask'],'expected':atlas_data['expected']}
    corrected=0
    for p in high.data.polygons:
        tree, ids = trees[regions.data[p.index].value]
        _, _, idx, _ = tree.find_nearest(p.center)
        face = int(ids[idx])
        points = np.array([vertices[k] for k in polygons[face]])
        axes = np.stack((points[1]-points[0], points[2]-points[0]), 1)
        inv = np.linalg.pinv(axes)
        weights=[]
        for loop in p.loop_indices:
            point = np.array(high.data.vertices[high.data.loops[loop].vertex_index].co[:])
            ab = inv @ (point-points[0]); bc = np.r_[1-ab.sum(),ab]
            outside += int(bc.min() < -.05)
            weights.append(bc)
        weights=np.array(weights)
        coords=weights@uv[face]
        centre=np.clip((coords.mean(axis=0)*2048).astype(int),0,2047)
        source_enamel=regions.data[p.index].value==names.index('enamel')
        if atlas['mask'][centre[1],centre[0]] and ((atlas['expected'][centre[1],centre[0]]==2)!=source_enamel):
            weights=np.maximum(weights,.02);weights/=weights.sum(axis=1,keepdims=True)
            coords=.25*(weights@uv[face])+.75*uv[face].mean(axis=0);corrected+=1
        for loop,value in zip(p.loop_indices,coords):layer.data[loop].uv=value
    print('HIGH UV TRANSFER extrapolated corners', outside,'material-boundary faces constrained',corrected, flush=True)
    return outside


def material(obj, state, out, control='full'):
    aged = state == 'present'
    prefix = 'aged' if aged else 'as_built'
    low = obj.name == 'MedalLow'
    names = json.loads(obj['feature_names'])
    saved = np.array([p.material_index for p in obj.data.polygons])
    # Repeated lanes must retain the enamel material region independently of replaced slots.
    if 'Stage2Enamel' not in obj.data.attributes:
        attr = obj.data.attributes.new('Stage2Enamel', 'INT', 'FACE')
        attr.data.foreach_set('value', saved.astype(np.int32))
    saved = np.array([a.value for a in obj.data.attributes['Stage2Enamel'].data])
    obj.data.materials.clear()
    for enamel in [False, True]:
        mat = bpy.data.materials.new(obj.name+'_'+state+'_'+control+('_enamel' if enamel else '_brass'))
        mat.use_nodes = True; nt = mat.node_tree; nt.nodes.clear()
        bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled'); output = nt.nodes.new('ShaderNodeOutputMaterial')
        nt.links.new(bsdf.outputs[0], output.inputs['Surface'])
        uvnode = nt.nodes.new('ShaderNodeUVMap'); uvnode.uv_map='MedalUV'
        uv = uvnode.outputs[0]
        if control == 'wrong_uv':
            add=nt.nodes.new('ShaderNodeVectorMath');add.operation='ADD'
            nt.links.new(uv,add.inputs[0]);add.inputs[1].default_value=(.19,.23,0);uv=add.outputs[0]
        def tex(path, color=False, interpolation='Linear'):
            node = nt.nodes.new('ShaderNodeTexImage');node.image=image(path,color)
            node.interpolation=interpolation;node.extension='EXTEND'
            nt.links.new(uv,node.inputs['Vector'])
            return node.outputs['Color']
        albedo=tex(out/(prefix+'_untarnished_albedo.png') if control=='no_tarnish' else MASTER/(prefix+'_albedo.png'), True)
        orm_path=out/(prefix+'_no_scratch_orm.png') if control in ['no_scratch','no_scratch_quantized'] else MASTER/(prefix+'_orm.png')
        if control=='no_tarnish':orm_path=out/(prefix+'_untarnished_orm.png')
        orm=tex(orm_path)
        split=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(orm,split.inputs[0])
        nt.links.new(albedo,bsdf.inputs['Base Color'])
        nt.links.new(split.outputs[1],bsdf.inputs['Roughness'])
        nt.links.new(split.outputs[2],bsdf.inputs['Metallic'])
        # Cycles supplies local physical occlusion; ORM.R is wired for future glTF export, not darkened albedo.
        group=bpy.data.node_groups.get('glTF Material Output')
        if group is None:
            group=bpy.data.node_groups.new('glTF Material Output','ShaderNodeTree')
            group.interface.new_socket(name='Occlusion',in_out='INPUT',socket_type='NodeSocketFloat')
            group.nodes.new('NodeGroupInput')
        occ=nt.nodes.new('ShaderNodeGroup');occ.node_tree=group
        nt.links.new(split.outputs[0],occ.inputs['Occlusion'])
        if enamel:
            bsdf.inputs['Coat Weight'].default_value=.65
            bsdf.inputs['Coat Roughness'].default_value=.23 if aged else .13
            bsdf.inputs['Specular IOR Level'].default_value=.5
        normal=nt.nodes.new('ShaderNodeNormalMap');normal.uv_map='MedalUV'
        if low and control not in ['flat_normal','ignored_normal','smooth_rim']:
            path=MASTER/(prefix+'_normal.png')
            if control in ['geometry_only','no_scratch']:path=MASTER/'geometry_normal.png'
            if control=='no_scratch_quantized':path=out/'geometry_runtime_normal.png'
            if control=='green_inverted':path=out/'inverted_green_normal.png'
            if control=='overstrong_scratch':path=out/'overstrong_normal.png'
            nt.links.new(tex(path,interpolation='Closest' if control=='overstrong_scratch' else 'Linear'),normal.inputs['Color'])
            nt.links.new(normal.outputs[0],bsdf.inputs['Normal'])
        if control=='rough_enamel' and enamel:
            for socket in ['Roughness','Coat Roughness']:
                for link in list(bsdf.inputs[socket].links):nt.links.remove(link)
                bsdf.inputs[socket].default_value=1
            bsdf.inputs['Coat Weight'].default_value=0
        if control=='smooth_rim':
            normal_constant=nt.nodes.new('ShaderNodeCombineXYZ')
            normal_constant.inputs['Y'].default_value=-1
            nt.links.new(normal_constant.outputs[0],bsdf.inputs['Normal'])
        if control in ['tarnish_mask','cavity_mask','convex_edge_mask']:
            emit=nt.nodes.new('ShaderNodeEmission')
            nt.links.new(tex(out/(control+'.png')),emit.inputs['Color'])
            nt.links.new(emit.outputs[0],output.inputs['Surface'])
        if control.startswith('normal_buffer') or control=='mask':
            emit=nt.nodes.new('ShaderNodeEmission')
            if control=='mask':
                attr=nt.nodes.new('ShaderNodeAttribute');attr.attribute_name='Stage2RegionRGB'
                socket=attr.outputs['Vector']
            else:
                suffix=control.removeprefix('normal_buffer_')
                geom=nt.nodes.new('ShaderNodeNewGeometry')
                socket=geom.outputs['Normal']
                if low and suffix not in ['flat','ignored']:
                    path=out/'geometry_runtime_normal.png' if suffix=='runtime' else MASTER/'geometry_normal.png'
                    if suffix=='inverted':path=out/'inverted_green_normal.png'
                    if suffix=='delivery':path=MASTER/(prefix+'_normal.png')
                    n=nt.nodes.new('ShaderNodeNormalMap');n.uv_map='MedalUV'
                    nt.links.new(tex(path),n.inputs['Color']);socket=n.outputs[0]
                scale=nt.nodes.new('ShaderNodeVectorMath');scale.operation='MULTIPLY_ADD'
                nt.links.new(socket,scale.inputs[0]);scale.inputs[1].default_value=(.5,.5,.5);scale.inputs[2].default_value=(.5,.5,.5)
                socket=scale.outputs[0]
            nt.links.new(socket,emit.inputs['Color']);nt.links.new(emit.outputs[0],output.inputs['Surface'])
        obj.data.materials.append(mat)
    for p,idx in zip(obj.data.polygons,saved):p.material_index=int(idx)


def setup(out):
    bpy.ops.wm.open_mainfile(filepath=str(out/'medal-bake.blend'))
    high,low=bpy.data.objects['MedalHigh'],bpy.data.objects['MedalLow']
    from medal_stage2_bake import image_from
    for key in ['geometry_normal','curvature_convex','curvature_concave','ao_near','ao_local']:
        image_from(key,np.load(out/(key+'.npy')),MASTER,depth=16)
    # Bake materials were temporary. Restore original enamel membership from the frozen bake context.
    context=np.load(out/'low-bake-context.npz')
    for o in [high,low]:
        for p,r in zip(o.data.polygons,o.data.attributes['FeatureRegion'].data):
            p.material_index=int(r.value==json.loads(o['feature_names']).index('enamel'))
        attr=o.data.attributes.new('Stage2RegionRGB','FLOAT_VECTOR','FACE')
        values=np.array([r.value for r in o.data.attributes['FeatureRegion'].data])
        attr.data.foreach_set('vector',np.repeat(((values+1)/16)[:,None],3,axis=1).astype(np.float32).ravel())
    transfer_uv(high,low,out)
    for obj in bpy.context.scene.objects:
        obj.hide_render=obj not in [high,low];obj.hide_set(obj not in [high,low])
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU'
    scene.cycles.samples=64;scene.cycles.seed=130303;scene.cycles.use_animated_seed=False
    scene.cycles.use_denoising=True;scene.render.threads_mode='FIXED';scene.render.threads=10
    scene.render.resolution_x=1200;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='OPEN_EXR';scene.render.image_settings.color_depth='32'
    scene.render.image_settings.color_mode='RGBA'
    scene.view_settings.view_transform='AgX';scene.view_settings.exposure=0
    scene.world=bpy.data.worlds.new('Stage2NeutralGrey');scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.18,.18,.18,1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.5
    lights=[]
    for name,loc,power,size in [('LargeWhiteArea',(-.048,-.060,.062),.10,.045),
                              ('SoftFill',(.055,-.035,.005),.035,.032),
                              ('RearRim',(.025,.040,.048),.13,.025),
                              ('RearSoftbox',(-.04,.055,.020),.045,.035)]:
        data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
        obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.location=loc
        obj.rotation_euler=(Vector((0,0,.002))-obj.location).to_track_quat('-Z','Y').to_euler()
        lights.append(obj)
    # A black card is reflection-visible but camera-invisible, with no geometry overlap.
    bpy.ops.mesh.primitive_plane_add(size=1,location=(.035,-.04,.025))
    card=bpy.context.object;card.name='DarkReflectionCard';card.scale=(.022,.040,1)
    card.rotation_euler=(Vector((0,0,.002))-card.location).to_track_quat('Z','Y').to_euler()
    card.visible_camera=False
    mat=bpy.data.materials.new('UnlitDarkCard');mat.use_nodes=True
    bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.003,.003,.003,1);bs.inputs['Roughness'].default_value=1
    card.data.materials.append(mat)
    data=bpy.data.cameras.new('Stage2ReviewCamera');data.type='ORTHO';data.ortho_scale=.043;data.clip_start=.001;data.clip_end=1
    camera=bpy.data.objects.new('Stage2ReviewCamera',data);scene.collection.objects.link(camera);scene.camera=camera
    return high,low,camera,lights


def studio(out,mode='main'):
    renderdir=out/'renders';renderdir.mkdir(exist_ok=True)
    rawdir=out/'linear';rawdir.mkdir(exist_ok=True)
    high,low,camera,lights=setup(out)
    if mode=='main':first_hit_masks(out,[high,low])
    scene=bpy.context.scene
    angles={'front':((0,-.12,.002),(0,0,.002),.043),
            'three-quarter':((-.075,-.12,.052),(0,0,.002),.043),
            'minus35':((-.12*math.sin(math.radians(35)),-.12*math.cos(math.radians(35)),.002),(0,0,.002),.043),
            'plus35':((.12*math.sin(math.radians(35)),-.12*math.cos(math.radians(35)),.002),(0,0,.002),.043),
            'rim-star-close':((-.018,-.12,.024),(0,0,.004),.034)}
    frames=[]
    def render(obj,state,angle,control='full',key=None,size=1200):
        high.hide_render=obj!=high;low.hide_render=obj!=low
        material(obj,state,out,control)
        location,target,scale=angles[angle]
        camera.location=location;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=scale
        key=key or f'{"high" if obj==high else "low"}-{state}-{angle}-{control}'
        scene.render.resolution_x=size;scene.render.resolution_y=size
        scene.render.image_settings.file_format='OPEN_EXR';scene.render.image_settings.color_depth='32'
        scene.render.image_settings.color_mode='RGBA'
        scene.render.filepath=str(rawdir/(key+'.exr'))
        bpy.ops.render.render(write_still=True)
        loaded=bpy.data.images.load(scene.render.filepath,check_existing=False)
        values=np.empty(size*size*4,np.float32);loaded.pixels.foreach_get(values)
        np.save(rawdir/(key+'.npy'),np.flipud(values.reshape(size,size,4)))
        bpy.data.images.remove(loaded)
        scene.render.image_settings.file_format='JPEG';scene.render.image_settings.color_depth='8';scene.render.image_settings.color_mode='RGB';scene.render.image_settings.quality=94
        path=renderdir/(key+'.jpg');bpy.data.images['Render Result'].save_render(str(path),scene=scene)
        frames.append(dict(key=key,mesh=obj.name,state=state,control=control,camera_location=list(location),
            camera_target=list(target),ortho_scale_m=scale,resolution=size,jpeg=str(path),linear=str(rawdir/(key+'.npy')),
            light_locations={l.name:list(l.location) for l in lights}))
        (out/('studio-'+mode+'.json')).write_text(json.dumps(dict(renderer='Cycles CPU',samples=scene.cycles.samples,
            seed=130303,exposure=0,world_grey=.18,world_strength=.5,card_location=[.035,-.04,.025],
            lights=[dict(name=l.name,location=list(l.location),power=l.data.energy,size=l.data.size) for l in lights],frames=frames),indent=2))
        print('RENDER COMPLETE',key,flush=True)
    if mode=='main':
        for obj in [high,low]:
            for state in ['remembered','present']:
                for angle in ['front','three-quarter','minus35','plus35','rim-star-close']:
                    render(obj,state,angle)
        for obj in [high,low]:
            render(obj,'remembered','front','mask',size=672)
            render(obj,'remembered','front','normal_buffer_full',size=672)
        for control in ['flat','ignored','inverted']:
            render(low,'remembered','front','normal_buffer_'+control,size=672)
        for state in ['remembered','present']:
            for control in ['full','flat_normal','ignored_normal','rough_enamel','no_tarnish','wrong_uv','green_inverted']:
                render(low,state,'front',control,key=f'gate-{state}-{control}',size=672)
        # Save PBR candidate sources separately, never overwrite accepted geometry inputs.
        material(high,'remembered',out);material(low,'remembered',out)
        bpy.context.preferences.filepaths.save_version=0
        bpy.ops.wm.save_as_mainfile(filepath=str(out/'medal-pbr-remembered.blend'))
        material(high,'present',out);material(low,'present',out)
        bpy.ops.wm.save_as_mainfile(filepath=str(out/'medal-pbr-present.blend'))
    elif mode=='high-refresh':
        for state in ['remembered','present']:
            for angle in ['front','three-quarter','minus35','plus35','rim-star-close']:
                render(high,state,angle)
            material(high,state,out);material(low,state,out)
            bpy.context.preferences.filepaths.save_version=0
            bpy.ops.wm.save_as_mainfile(filepath=str(out/f'medal-pbr-{state}.blend'))
    elif mode=='age-controls':
        for state in ['remembered','present']:
            for control in ['no_tarnish','smooth_rim']:
                render(low,state,'front',control,key=f'gate-{state}-{control}',size=672)
        for control in ['tarnish_mask','cavity_mask','convex_edge_mask']:
            render(low,'present','front',control,key=f'gate-present-{control}',size=672)
    elif mode=='delivery-normal':
        render(low,'remembered','front','normal_buffer_delivery',size=672)
    elif mode=='quantized-baseline':
        render(low,'remembered','front','normal_buffer_runtime',size=672)
        scene.cycles.samples=48
        for state in ['remembered','present']:
            for frame in range(24):
                angle=2*math.pi*frame/24
                lights[0].location=(.070*math.sin(angle),-.070*math.cos(angle),.045)
                lights[0].rotation_euler=(Vector((0,0,.002))-lights[0].location).to_track_quat('-Z','Y').to_euler()
                for size,width in [(672,500),(46,34),(10,7)]:
                    infix='' if width==500 else f'width{width}-'
                    render(low,state,'front','no_scratch_quantized',key=f'rotate-{state}-{frame:02}-{infix}no_scratch_quantized',size=size)
    elif mode=='sweep':
        scene.cycles.samples=48
        for state in ['remembered','present']:
            for frame in range(24):
                angle=2*math.pi*frame/24
                lights[0].location=(.070*math.sin(angle),-.070*math.cos(angle),.045)
                lights[0].rotation_euler=(Vector((0,0,.002))-lights[0].location).to_track_quat('-Z','Y').to_euler()
                for control in ['full','no_scratch','rough_enamel','overstrong_scratch']:
                    render(low,state,'front',control,key=f'rotate-{state}-{frame:02}-{control}',size=672)
                for size,width in [(46,34),(10,7)]:
                    for control in ['full','no_scratch','overstrong_scratch']:
                        render(low,state,'front',control,key=f'rotate-{state}-{frame:02}-width{width}-{control}',size=size)
    else:raise ValueError(mode)
    print('STUDIO COMPLETE',mode,flush=True)


if __name__=='__main__':
    args=sys.argv[sys.argv.index('--')+1:]
    studio(Path(args[0]),args[1] if len(args)>1 else 'main')
