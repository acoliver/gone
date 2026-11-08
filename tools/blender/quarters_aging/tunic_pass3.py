"""Cut the fitted tunic, release shared armhole stitches, then simulate weakened wool."""
import json
import math
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

from common import assert_surface_clear, collision, midsurface, recalc, settle, surface_tree
from fabric_mesh import fray, material, new_object, replace
from stress_cut import cut_faces, fractal, release_armhole


def bind_details(body):
    body.data.calc_loop_triangles()
    vertices = [v.co.copy() for v in body.data.vertices]
    faces = [tuple(t.vertices) for t in body.data.loop_triangles]
    from mathutils.bvhtree import BVHTree
    tree = BVHTree.FromPolygons(vertices, faces, all_triangles=True)
    bindings = {}
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH' or obj.name in {'TunicBody', 'Hanger', 'AgingFloorCollider'}:
            continue
        binding = []
        for vertex in obj.data.vertices:
            p = obj.matrix_world @ vertex.co
            q, normal, index, _ = tree.find_nearest(p)
            tri = faces[index]
            a, b, c = [np.asarray(vertices[i]) for i in tri]
            uv = np.linalg.lstsq(np.c_[b-a, c-a], np.asarray(q)-a, rcond=None)[0]
            binding.append((tri, [1-uv.sum(), *uv], float((p-q).dot(normal))))
        bindings[obj.name] = {'entries': binding, 'original': [tuple(obj.matrix_world @ v.co) for v in obj.data.vertices]}
    return bindings


def follow(body, bindings):
    for name, binding in bindings.items():
        obj = bpy.data.objects[name]
        if name.startswith('Collar'):
            for vertex in obj.data.vertices:vertex.co.z+=.010
            continue
        inverse = obj.matrix_world.inverted()
        original = np.asarray(binding['original'])
        transformed = []
        for tri, weights, offset in binding['entries']:
            a, b, c = [body.data.vertices[i].co for i in tri]
            normal = (b-a).cross(c-a).normalized()
            p = sum((body.data.vertices[i].co * w for i, w in zip(tri, weights)), Vector())
            transformed.append(tuple(p + normal * offset))
        transformed = np.asarray(transformed)
        if name in {'Placket','RibbonBar','ShoulderBoard_L','ShoulderBoard_R'}:
            from detail_fit import fit_patch
            obj['support_fit']=json.dumps(fit_patch(obj,body,transformed,upward=name.startswith('ShoulderBoard')))
            continue
        # Metal details follow a rigid best fit instead of folding their thickness.
        bm = bmesh.new(); bm.from_mesh(obj.data); bm.verts.ensure_lookup_table()
        remaining=set(bm.verts)
        while remaining:
            if name=='Medal':
                group=set(remaining);remaining.clear();frontier=set()
            else:
                frontier={remaining.pop()};group=set(frontier)
            while frontier:
                following={e.other_vert(v) for v in frontier for e in v.link_edges}&remaining
                remaining-=following;group|=following;frontier=following
            indices=np.array([v.index for v in group])
            src=original[indices];dst=transformed[indices]
            a=src.mean(0);b=dst.mean(0)
            u,_,vt=np.linalg.svd((src-a).T@(dst-b))
            rotation=u@vt
            if np.linalg.det(rotation)<0:u[:,-1]*=-1;rotation=u@vt
            transformed[indices]=(src-a)@rotation+b
        bm.free()
        if name=='Buttons':transformed[:,1]-=.004
        if name=='Medal':
            transformed[:,2]-=.004
            transformed[:,1]-=.003
        for vertex,p in zip(obj.data.vertices,transformed):vertex.co=inverse @ Vector(p)
        recalc(obj)


def heap(seed):
    # Forward of the hem, spread toward the same front-right hero camera.
    centre = np.array([.11, -.19])
    vertices = [(centre[0], centre[1], -.936)]
    n = 64
    for j in range(1, 5):
        r = j / 4
        for i in range(n):
            a = math.tau * i / n
            irregular = 1 + .08 * math.sin(7*a) + .04 * math.sin(13*a + seed)
            vertices.append((centre[0]+.15*r*math.cos(a)*irregular, centre[1]+.105*r*math.sin(a)*irregular,
                             -.9497+.0137*(1-r*r)**1.7))
    faces = [(0, 1+i, 1+(i+1)%n) for i in range(n)]
    for j in range(3):
        for i in range(n):
            a=1+j*n+i; b=1+j*n+(i+1)%n
            faces.append((a,b,b+n,a+n))
    bottom=len(vertices); vertices.append((*centre,-.9498))
    faces += [(bottom, 1+3*n+(i+1)%n, 1+3*n+i) for i in range(n)]
    new_object('FibreDust', vertices, faces, material('FibreDust', (.27,.24,.19)))
    return {'method':'Constructed seeded radial fibre/dust heap, not simulated', 'centre_blender_m':centre.tolist(), 'floor_m':-.95}


def build(seed, frames):
    obj=bpy.data.objects['TunicBody']
    midsurface(obj)
    vertices=[np.asarray(v.co[:]) for v in obj.data.vertices]
    faces=[tuple(p.vertices) for p in obj.data.polygons]
    patterns=[[tuple(obj.data.uv_layers.active.data[i].uv) for i in p.loop_indices] for p in obj.data.polygons]
    seam=release_armhole(vertices,faces,1680,1974)
    replace(obj,vertices,faces,material('NaturalFabric',(.025,.043,.080)))
    for face, uv in zip(obj.data.polygons,patterns):
        for i,p in zip(face.loop_indices,uv): obj.data.uv_layers.active.data[i].uv=p
    def cut(p):
        x,y,z=p
        if y < -.018 and .045 < abs(x) < .23:
            for cx,cz,w,h in [(-.14,-.32,.039,.10),(.17,-.27,.043,.065),(-.11,-.65,.032,.11),(.15,-.72,.032,.075)]:
                across=x-cx + .08*(z-cz)
                edge=fractal(z,seed)
                # U-shaped loss retains the top hinge of each hanging flap.
                if abs(across) < w+edge and -h < z-cz < h:
                    if abs(across) > w-.018+edge or z-cz < -h+.024:
                        return True
        return abs(x)<.25 and z < -.868 + .024*(.5+.5*math.sin(81*x+seed))**3 + fractal(x,seed+1,.004)
    tears=cut_faces(obj,cut,seed,noise_region=lambda p:p.z<-.23 and not(.22<p.x<.31 and p.z>-.36))
    # Retain only the non-intersecting collar band from the fitted source.
    collar=bpy.data.objects['Collar']
    bm=bmesh.new(); bm.from_mesh(collar.data)
    remaining=set(bm.verts); groups=[]
    while remaining:
        frontier={remaining.pop()}; group=set(frontier)
        while frontier:
            following={e.other_vert(v) for v in frontier for e in v.link_edges}&remaining
            remaining-=following; group|=following; frontier=following
        groups.append(group)
    band=max(groups,key=lambda g:max(v.co.z for v in g))
    bmesh.ops.delete(bm,geom=[v for g in groups if g is not band for v in g],context='VERTS')
    bm.to_mesh(collar.data); bm.free()
    bm=bmesh.new();bm.from_mesh(obj.data)
    edges=[e for e in bm.edges if all(v.co.z>-.30 and abs(v.co.x)<.285 for v in e.verts) and e.calc_length()>.008]
    bmesh.ops.subdivide_edges(bm,edges=edges,cuts=2,use_grid_fill=True)
    bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
    # Lift the initial contact strip clear of the wire before pinning it. The fitted
    # source's closed wool section hides wire crossings that its midsurface exposes.
    for vertex in obj.data.vertices:
        p=vertex.co
        if .09 < abs(p.x) < .275 and p.z > -.255:
            p.z += .012 * float(np.clip((p.z+.255)/.045,0,1))
    recalc(obj)
    hanger=surface_tree(bpy.data.objects['Hanger'])
    pins={}
    for vertex in obj.data.vertices:
        p=vertex.co
        if .095<abs(p.x)<.245 and p.z>-.22 and abs(p.y)<.002:
            hit,_,_,_=hanger.ray_cast(Vector((p.x,p.y,.1)),Vector((0,0,-1)))
            if hit is None:raise ValueError('Hanger contact strip misses its support')
            p.z=hit.z+.006
            pins[vertex.index]=1
    recalc(obj)
    assert_surface_clear(obj)
    bindings=bind_details(obj)
    wire=bpy.data.objects['Hanger']
    collision(wire,.002)
    wire.collision.use_culling=False
    wire.collision.thickness_inner=.002
    settings={'quality':60,'frames':frames,'time_scale':.12,'mass':.18,'stiffness':40,'max_stiffness':300,'bending':.06,
              'self_collision':True,'self_distance_m':.002,'collision_distance_m':.003,'collision_quality':15,
              'air_damping':10,'structural_damping':25,'bending_damping':8}
    freed={loop.vertex_index for loop in obj.data.loops if 1.0999 <= obj.data.uv_layers.active.data[loop.index].uv.x <= 1.5501}
    strength={v.index:0 if v.index in freed else (.6 if abs(v.co.x)<.25 and v.co.z<-.4 else 1) for v in obj.data.vertices}
    retained={loop.vertex_index for loop in obj.data.loops if 1.6999 <= obj.data.uv_layers.active.data[loop.index].uv.x <= 2.1501}
    settings.update({'max_bending':1.0,'body_bending_weight':.15,'retained_sleeve_bending_weight':1.0})
    bending={v.index:1 if v.index in retained else (0 if v.index in freed else .15) for v in obj.data.vertices}
    result=settle(obj,settings,pins,stiffness_weights=strength,bending_weights=bending)
    state={'bindings':bindings,'seed':seed,'settings':settings,'seam':seam,'tears':tears,'result':result,
           'initial_contact':{'pin_clearance_m':.006,'lift_m':.012,'hanger_outer_m':.002,'hanger_inner_m':.002,'two_sided':True}}
    bpy.context.scene['tunic_simulated_state']=json.dumps(state)
    checkpoint=Path(bpy.context.scene['pass3_trial_dir'])/'simulated.blend'
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(checkpoint))
    return finish(state)


def finish(state):
    obj=bpy.data.objects['TunicBody']
    bindings=state['bindings'];seed=state['seed'];settings=state['settings'];seam=state['seam'];tears=state['tears'];result=state['result']
    collar=bpy.data.objects['Collar']
    midsurface(collar)
    follow(obj,bindings)
    from detail_fit import trim_fold_contacts
    collar_trim=trim_fold_contacts(collar,obj)
    collar.data.materials[0].use_backface_culling=False
    collar['bounded_cloth']=True
    recalc(collar)
    detail_fits={name:json.loads(bpy.data.objects[name]['support_fit']) for name in ['ShoulderBoard_L','ShoulderBoard_R','RibbonBar','Placket']}
    detail_fits['Collar']={'method':'Source neck band lifted 10 mm; midsurface trimmed against simulated neck folds; not simulated','fold_trim':collar_trim}
    fibres=fray(obj,seed+1,probability=.32,length=(.002,.013),max_edge=.022,region=lambda p:p.z < -.22)
    from section_contacts import prune_surface_fibres
    prune_surface_fibres(obj)
    obj.data.materials[0].use_backface_culling=False
    obj['bounded_cloth']=True
    recalc(obj)
    return {'method':'Blender cloth simulation after armhole stitch release and stress cuts; no post-simulation body deformation',
            'settings':settings,'initial_contact':state.get('initial_contact'),
            'armhole':seam,'tears':tears,'simulation':result,'frays':fibres,'detail_fits':detail_fits,'heap':heap(seed+2)}
