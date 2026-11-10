"""Settle cut upholstery on collapsed crust, slide torn wool, and drop rigid crumbs."""
import json
import math

import bmesh
import bpy
import numpy as np
from mathutils import Vector

from common import activate, apply, assert_collision_clear, assert_surface_clear, collision, midsurface, recalc, settle, surface_tree
from fabric_mesh import fray, join, material, new_object, volume
from foam_collapse import largest_shell, plates
from stress_cut import cut_faces, fractal


CUSHIONS=['SeatCushion_L','SeatCushion_C','SeatCushion_R','BackCushion_L','BackCushion_C','BackCushion_R']


def restore_parts(bake, source, parts):
    selected=set(parts)
    if not selected or selected-set(CUSHIONS+['Throw','ThrowDetachedPiece','FoamDebris']):
        raise ValueError('Select named sofa cushions, Throw, ThrowDetachedPiece or FoamDebris')
    bpy.ops.wm.open_mainfile(filepath=str(bake.resolve()))
    remove=selected|({'ThrowDetachedPiece'} if 'Throw' in selected else set())
    for name in remove:
        if name in bpy.data.objects:bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
    load=selected-{'FoamDebris','ThrowDetachedPiece'}
    if 'ThrowDetachedPiece' in selected:load.add('Throw')
    with bpy.data.libraries.load(str(source.resolve()),link=False) as (_, target):
        target.objects=sorted(load)
    for obj in target.objects:
        bpy.context.collection.objects.link(obj)
        for slot in obj.material_slots:
            original=bpy.data.materials.get(slot.material.name.split('.')[0])
            if original:slot.material=original
        if obj.name.startswith('Throw') and 'Throw' not in selected:
            detach_corner(obj)
            bpy.data.objects.remove(obj,do_unlink=True)


def settings(frames):
    return {'quality':30,'frames':frames,'time_scale':.25,'mass':.12,'stiffness':180,'bending':.08,
            'self_collision':True,'self_distance_m':.0008,'collision_distance_m':.003,'collision_quality':12}


def prepare_cushion(obj, seed):
    original_volume=volume(obj)
    largest_shell(obj)
    core=obj.copy();core.data=obj.data.copy();bpy.context.collection.objects.link(core)
    core.name=obj.name+'_Crust';core['aged_export']=False
    points=np.asarray([v.co[:] for v in core.data.vertices]);lo,hi=points.min(0),points.max(0)
    back=obj.name.startswith('Back')
    centre=(lo+hi)/2
    scale=np.array([.91,.45 if back else .78,.65 if back else .39])
    offset=np.array([centre[0]*(1-scale[0]),centre[1]*(1-scale[1])-(0 if back else .045),
                     (.411 if back else lo[2])-scale[2]*lo[2]])
    for vertex,p in zip(core.data.vertices,points*scale+offset):vertex.co=p
    mod=core.modifiers.new('Crust collider reduction','DECIMATE');mod.ratio=.23;apply(core,mod)
    # Scale the crust to the required retained volume before carving cracks.
    ratio=original_volume*.29/volume(core)
    base=min(v.co.z for v in core.data.vertices)
    for v in core.data.vertices:v.co.z=base+(v.co.z-base)*ratio
    scale[2]*=ratio;offset[2]=base+(offset[2]-base)*ratio
    envelope=core.copy();envelope.data=core.data.copy();bpy.context.collection.objects.link(envelope)
    envelope.name=obj.name+'_CrustCollider';envelope.hide_render=True;envelope['aged_export']=False
    basis=envelope.shape_key_add(name='Fitted filling contact')
    collapsed=envelope.shape_key_add(name='Collapsed filling contact')
    source_tree=surface_tree(obj)
    inverse=obj.matrix_world.inverted()
    for vertex in basis.data:
        original=(np.asarray(vertex.co)-offset)/scale
        point,normal,_,_=source_tree.find_nearest(obj.matrix_world@Vector(original))
        vertex.co=inverse@(point-normal*.008)
    collapsed.value=0;collapsed.keyframe_insert(data_path='value',frame=1)
    collapsed.value=1;collapsed.keyframe_insert(data_path='value',frame=480)
    for curve in envelope.data.shape_keys.animation_data.action.fcurves:
        for point in curve.keyframe_points:point.interpolation='LINEAR'
    collision(envelope,.001)
    cells=plates(core,seed,9,.0015)
    core.data.materials.clear();core.data.materials.append(material('Foam',(.16,.065,.022)))
    bm=bmesh.new();bm.from_mesh(obj.data);bm.normal_update()
    # Keep the rear cloth: it holds the collapsed cover around the crust as a sack.
    bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.normal.z < -.2],context='FACES')
    bm.to_mesh(obj.data);bm.free()
    cx=obj.matrix_world.translation.x
    def cut(p):
        if back:
            return p.z < .49 or (p.y < .29 and abs(p.x-cx+.06*math.sin(20*p.z)) < .022+fractal(p.z,seed) and .49 < p.z < .70)
        # Lower side returns have rotted away, clearing the deck before gravity starts.
        x=p.x-cx
        return p.z < .410 or (p.y < -.30+fractal(p.x,seed+3) and x < -.25+fractal(p.y,seed+4)) or (abs(x-.075+.08*(p.y+.15)) < .032+fractal(p.y,seed) and -.37 < p.y < -.10 and p.z > .43) or (abs(x+.15) < .024+fractal(p.y,seed+1) and -.22 < p.y < .08 and p.z > .43)
    cuts=cut_faces(obj,cut,seed,noise_region=lambda p:not back or p.y<.31)
    return {'object':obj,'core':core,'envelope':envelope,'pins':{},'back':back,
            'original_volume':original_volume,'cells':cells,'cuts':cuts,'seed':seed}


def finish_cushion(state, result, config):
    obj,core,envelope=state['object'],state['core'],state['envelope']
    back,seed=state['back'],state['seed']
    fibres=fray(obj,seed+1,probability=.28,length=(.002,.008),max_edge=.04,region=lambda p:p.z>(.49 if back else .43))
    from section_contacts import prune_surface_fibres
    prune_surface_fibres(obj)
    obj.data.materials[0].use_backface_culling=False
    obj['bounded_cloth']=True
    bpy.data.objects.remove(envelope,do_unlink=True)
    core.modifiers.clear();crust_ratio=volume(core)/state['original_volume']
    join(obj,[core]);obj['aged_export']=True
    return {'method':'Cut fitted covers simulated together at zero pressure on shrunken crust colliders, with inter-cover self-collision; no cloth pose constructed; double-sided cover midsurfaces',
            'original_volume_m3':state['original_volume'],'crust_volume_ratio':crust_ratio,
            'initial_width_ratio':1,'initial_rear_contact_inset_m':0,
            'collider_collapse':{'start_frame':1,'end_frame':480,'initial_envelope_inset_m':.008,'interpolation':'LINEAR'},
            'crust_cells':state['cells'],'cuts':state['cuts'],'simulation':result,'settings':config,'frays':fibres}


def cushion_group(names, seed, frames):
    states=[prepare_cushion(bpy.data.objects[name],seed+31*CUSHIONS.index(name)) for name in names]
    vertices,faces,patterns,pins=[],[],[],{}
    slices={}
    for state in states:
        obj=state['object'];offset=len(vertices)
        vertices.extend(tuple(obj.matrix_world@v.co) for v in obj.data.vertices)
        slices[obj.name]=(offset,len(vertices))
        for face in obj.data.polygons:
            faces.append(tuple(offset+i for i in face.vertices))
            patterns.append([tuple(obj.data.uv_layers.active.data[i].uv) for i in face.loop_indices])
        pins.update({offset+i:weight for i,weight in state['pins'].items()})
    cloth=new_object('JointCushionCovers',vertices,faces,states[0]['object'].data.materials[0])
    cloth['aged_export']=False
    for face,uv in zip(cloth.data.polygons,patterns):
        for i,p in zip(face.loop_indices,uv):cloth.data.uv_layers.active.data[i].uv=p
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    assert_surface_clear(cloth)
    assert_collision_clear(cloth)
    config=settings(max(frames,1000))
    config.update({'quality':50,'time_scale':.15,'self_distance_m':.002,
                   'air_damping':8,'structural_damping':25,'bending_damping':8})
    result=settle(cloth,config,pins,pressure=0)
    result['joint_cover_nodes']=names
    for state in states:
        obj=state['object'];start,end=slices[obj.name];inverse=obj.matrix_world.inverted()
        for vertex,p in zip(obj.data.vertices,cloth.data.vertices[start:end]):vertex.co=inverse@p.co
        recalc(obj)
    bpy.data.objects.remove(cloth,do_unlink=True)
    return {state['object'].name:finish_cushion(state,result,config) for state in states}


def detach_corner(obj):
    midsurface(obj)
    # Detach the lower forward corner of the existing throw, before either part falls.
    mesh=obj.data
    ids={p.index for p in mesh.polygons if sum(mesh.vertices[i].co.z for i in p.vertices)/len(p.vertices)<.65 and sum(mesh.vertices[i].co.y for i in p.vertices)/len(p.vertices)<-.15 and sum(mesh.vertices[i].co.x for i in p.vertices)/len(p.vertices)>1.13}
    selected=[tuple(mesh.polygons[i].vertices) for i in sorted(ids)]
    used=sorted({v for f in selected for v in f});mapping={v:i for i,v in enumerate(used)}
    scrap=new_object('ThrowDetachedPiece',[mesh.vertices[i].co[:] for i in used],[tuple(mapping[i] for i in f) for f in selected],obj.data.materials[0])
    bm=bmesh.new();bm.from_mesh(mesh);bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm,geom=[bm.faces[i] for i in sorted(ids)],context='FACES')
    bm.to_mesh(mesh);bm.free()
    return scrap


def drop_piece(scrap, seed, frames):
    config=settings(max(frames,800))
    config.update({'quality':45,'time_scale':.20,'stiffness':150,'bending':.005,'mass':.06,
                   'self_distance_m':.003,'structural_damping':25,'bending_damping':8,'air_damping':8})
    bpy.data.objects['AgingFloorCollider'].collision.cloth_friction=2
    assert_surface_clear(scrap)
    assert_collision_clear(scrap)
    record=settle(scrap,config,{})
    fray(scrap,seed+4,probability=.45,length=(.004,.015),max_edge=.03)
    from section_contacts import prune_surface_fibres
    prune_surface_fibres(scrap)
    scrap.data.materials[0].use_backface_culling=False
    scrap['bounded_cloth']=True
    return config,record


def throw(obj, seed, frames):
    scrap=detach_corner(obj)
    cuts=cut_faces(obj,lambda p:abs(p.y+.08+.04*(p.z-.6)) < .015+fractal(p.z,seed) and .45 < p.z < .73,seed)
    # No pins: low arm friction allows the unbalanced exterior sheet to slide.
    config=settings(max(frames,800));config.update({'stiffness':150,'bending':.06,'mass':.15,'self_distance_m':.0015})
    assert_surface_clear(obj)
    assert_surface_clear(scrap)
    record=settle(obj,config,{})
    fibres=fray(obj,seed+3,probability=.45,length=(.004,.017),max_edge=.03)
    from section_contacts import prune_surface_fibres
    prune_surface_fibres(obj)
    obj.data.materials[0].use_backface_culling=False
    obj['bounded_cloth']=True
    collision(obj,.001)
    # The dropped remnant also collides with the already settled main cloth.
    scrap_settings,scrap_record=drop_piece(scrap,seed,frames)
    return {'method':'Both cut original throw and detached corner simulated with zero pins, gravity and low frame friction',
            'cuts':cuts,'settings':config,'simulation':record,'detached_settings':scrap_settings,'detached_simulation':scrap_record,'frays':fibres}


def rigid_crumbs(seed, frames):
    rng=np.random.default_rng(seed)
    scene=bpy.context.scene;scene.frame_set(1)
    bpy.ops.mesh.primitive_cube_add(size=1,location=(0,0,-.1))
    floor=bpy.context.object;floor.name='RigidFloorVolume';floor.dimensions=(8,8,.2)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    floor.hide_render=True;floor['aged_export']=False
    static=[*[bpy.data.objects[n] for n in ['Frame', 'Feet', 'Rivets']],floor,*[o for o in scene.objects if o.name in CUSHIONS+['Throw','ThrowDetachedPiece'] and o.get('aged_export')]]
    for obj in static:
        activate(obj);bpy.ops.rigidbody.object_add();obj.rigid_body.type='PASSIVE'
        obj.rigid_body.collision_shape='BOX' if obj==floor else 'MESH';obj.rigid_body.friction=.95
        obj.rigid_body.use_margin=True;obj.rigid_body.collision_margin=.0003
    pieces=[];sizes=[];release_cloud=[]
    for cx in [-.67,0,.67]:
        # The release cloud is random, not a row; dense clusters become the powder fraction.
        for i in range(100):
            size=float(np.clip(rng.lognormal(math.log(.010),.72),.0035,.025))
            for attempt in range(10000):
                centre=np.array([cx+.075+rng.normal(0,.035),-.425+rng.normal(0,.020),rng.uniform(.50,.62)])
                if all(np.linalg.norm(centre-p) > (size+s)/2+.002 for p,s in release_cloud):break
            else:raise ValueError('Rigid release cloud cannot be packed without overlapping particles')
            release_cloud.append((centre,size))
            bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=1,location=centre)
            obj=bpy.context.object;obj.name=f'Crumb_{len(pieces):03d}'
            shape=rng.uniform(.65,1.15,(len(obj.data.vertices),1))
            for v,s in zip(obj.data.vertices,shape):v.co*=float(s)*size/2
            obj.data.materials.append(material('Foam',(.16,.065,.022)))
            obj.rotation_euler=rng.uniform(-math.pi,math.pi,3)
            bpy.ops.object.transform_apply(location=False,rotation=True,scale=False)
            points=np.array([v.co[:] for v in obj.data.vertices])
            normalise=size/np.linalg.norm(points[:,None]-points[None,:],axis=2).max()
            for vertex in obj.data.vertices:vertex.co*=normalise
            bpy.ops.rigidbody.object_add();r=obj.rigid_body
            r.collision_shape='CONVEX_HULL';r.mass=max(.00001,size**3*40)
            r.friction=1;r.restitution=0;r.use_margin=True;r.collision_margin=.0005
            r.linear_damping=.8;r.angular_damping=.9
            r.use_deactivation=True;r.deactivate_linear_velocity=.02;r.deactivate_angular_velocity=.05
            pieces.append(obj);sizes.append(size)
    world=scene.rigidbody_world;world.substeps_per_frame=12;world.solver_iterations=30
    world.point_cache.frame_start=1;world.point_cache.frame_end=frames
    matrices={}
    for frame in range(1,frames+1):
        scene.frame_set(frame)
        deps=bpy.context.evaluated_depsgraph_get()
        if frame==frames: matrices={o.name:o.evaluated_get(deps).matrix_world.copy() for o in pieces}
        if frame%20==0:print('rigid crumbs frame',frame,flush=True)
    for obj in pieces:
        transform=matrices[obj.name]
        activate(obj);bpy.ops.rigidbody.object_remove();obj.matrix_world=transform
    for obj in static:
        activate(obj);bpy.ops.rigidbody.object_remove()
    scene.frame_set(1)
    bpy.data.objects.remove(floor,do_unlink=True)
    target=pieces[0];target.name='FoamDebris';target['aged_export']=True
    join(target,pieces[1:])
    return {'method':f'{len(pieces)} irregular convex chunks released in seeded clouds below front splits, Blender rigid-body gravity drop onto a solid floor volume and furniture',
            'linear_damping':.8,'angular_damping':.9,'floor_top_m':0,
            'frames':frames,'substeps_per_frame':12,'solver_iterations':30,'size_distribution':'clipped log-normal','size_parameters_m':[.0035,.025], 'sample_sizes_m':sizes}


def build(seed, frames, parts=None):
    for name in ['Frame', 'Feet', 'Rivets']:
        obj=bpy.data.objects[name]
        collision(obj,.001)
        obj.collision.cloth_friction=.6
    selected=set(CUSHIONS+['Throw','FoamDebris']) if parts is None else set(parts)
    record={} if parts is None else json.loads(bpy.context.scene['aging_record'])['construction']
    for name in CUSHIONS:
        if name not in selected:collision(bpy.data.objects[name],.001)
    covers=[name for name in CUSHIONS if name in selected]
    if covers:
        record.update(cushion_group(covers,seed,frames))
        for name in covers:collision(bpy.data.objects[name],.001)
    if 'Throw' in selected:
        record['Throw']=throw(bpy.data.objects['Throw'],seed+300,frames)
    elif 'ThrowDetachedPiece' in selected:
        collision(bpy.data.objects['Throw'],.001)
        config,result=drop_piece(bpy.data.objects['ThrowDetachedPiece'],seed+300,frames)
        record['Throw']['detached_settings']=config;record['Throw']['detached_simulation']=result
    if 'FoamDebris' in selected:record['crumbs']=rigid_crumbs(seed+400,frames)
    return record
