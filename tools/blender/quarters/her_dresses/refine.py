"""Fine tear lips, upward-fold dust and feathered dry-fibre powder deposits."""
import math
from pathlib import Path
import sys

import bmesh
import bpy
import numpy as np

HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE.parent/'her_jacket'),str(HERE.parents[1]/'quarters_aging')]
from cloth_tools import ASSETS,mesh
from arrange import FRONT_OFFSET,RAIL_Y,POSITIONS
from common import recalc
from fringe_cards import cards,fringe_material,image_from_array
from powder_cards import powder_card

TEXTURES=ASSETS/'her_dresses_textures'
SHELF_SURFACE=.1448
POWDER_RADIUS=(.145,.16)
CORE_RADIUS=(.115,.13)
CORE_RELIEF=.026


def deposit_height(x,y,centre):
    u=(x-centre)/CORE_RADIUS[0];v=(y+.11)/CORE_RADIUS[1]
    skew=.22 if centre<0 else -.18
    u+=skew*v;v*=1.08 if centre<0 else .96
    return SHELF_SURFACE+CORE_RELIEF*max(0,1-u*u-v*v)**2*(1+.12*math.sin(u*6+v*4))


def reverse_faces(obj):
    bm=bmesh.new();bm.from_mesh(obj.data)
    result=bmesh.ops.duplicate(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces))
    faces=[f for f in result['geom'] if isinstance(f,bmesh.types.BMFace)]
    bmesh.ops.reverse_faces(bm,faces=faces)
    bm.normal_update();bm.to_mesh(obj.data);bm.free();obj.data.update()


def ragged_edges(obj,index=0):
    bm=bmesh.new();bm.from_mesh(obj.data)
    group=obj.vertex_groups.get('SupportStitches')
    deform=bm.verts.layers.deform.active
    locked={v for v in bm.verts if group is not None and deform is not None and v[deform].get(group.index,0)>.99}
    edges=[e for e in bm.edges if e.is_boundary and ((e.verts[0].co.z+e.verts[1].co.z)/2<.90 or 1.50<(e.verts[0].co.z+e.verts[1].co.z)/2<1.67)]
    selected={v for e in edges for v in e.verts}
    for _ in range(6):
        changes={}
        for vertex in selected-locked:
            neighbours=[e.other_vert(vertex) for e in vertex.link_edges if e.is_boundary]
            if len(neighbours)==2:
                changes[vertex]=vertex.co.lerp((neighbours[0].co+neighbours[1].co)/2,.45)
        for vertex,point in changes.items():vertex.co=point
    edge_count=len(edges)
    bmesh.ops.subdivide_edges(bm,edges=edges,cuts=3,use_grid_fill=False)
    locked={v for v in bm.verts if group is not None and deform is not None and v[deform].get(group.index,0)>.99}
    affected={v for v in bm.verts if any(e.is_boundary for e in v.link_edges) and (v.co.z<.90 or 1.50<v.co.z<1.67)}
    hem=[v.co.z for v in affected-locked if v.co.z<.90]
    hem_height=float(np.median(hem)) if hem else 0
    centre=float(np.median([v.co.x for v in affected if v.co.z<.90])) if hem else 0
    losses=((-.10,.025,.006),(.065,.020,.003)) if index==0 else ((-.06,.020,.004),(.12,.028,.007))
    for vertex in affected-locked:
        p=vertex.co
        amount=1 if p.z<.90 else .60
        if p.z<.90:
            p.z=.10*p.z+.90*hem_height
            p.z+=sum(depth*math.exp(-((p.x-centre-offset)/width)**2) for offset,width,depth in losses)
        else:
            weight=math.exp(-((p.x-centre+.09)/.035)**4-((p.z-1.625)/.05)**4)
            p.z+=(1.625-p.z)*.30*weight
            p.y+=.0015*weight*math.sin((p.z-1.59)*math.pi/.065)
        p.z+=amount*(.0007*math.sin(p.x*137+p.y*37)+.0003*math.sin(p.x*319-p.y*93))
        p.x+=(.0003 if p.z<.90 else .0005)*math.sin(p.z*137+p.x*127)
    shoulder={v for v in bm.verts if 1.50<v.co.z<1.68 and v not in locked and any(e.is_boundary for e in v.link_edges)}
    for _ in range(8):
        changes={}
        for vertex in shoulder:
            neighbours=[e.other_vert(vertex) for e in vertex.link_edges if e.is_boundary]
            if len(neighbours)==2:
                changes[vertex]=vertex.co.lerp((neighbours[0].co+neighbours[1].co)/2,.5)
        for vertex,point in changes.items():vertex.co=point
    bm.normal_update();bm.to_mesh(obj.data);bm.free();obj.data.update()
    recalc(obj)
    return {'refined_boundary_edges':edge_count,'shoulder_post_refinement_passes':8,'boundary_subdivisions':4,
            'hem_vertical_grain_variation_m':.001,'shoulder_variation_scale':.60,
            'shoulder_gap_reduction':.30,'softened_boundary_passes':6,
            'local_grain_losses_m':[list(loss) for loss in losses],
            'locked_support_stitches':len(locked)}


def stiffen_folds(obj,centre,index):
    before=np.asarray([v.co[:] for v in obj.data.vertices])
    for vertex in obj.data.vertices:
        p=vertex.co
        weight=float(np.clip((p.z-.64)/.18,0,1)*np.clip((1.55-p.z)/.18,0,1))
        u=p.x-centre
        shift=.012*(p.z-1.1)
        crease=.005*max(0,1-abs((u-(.035 if index==0 else -.025)-shift)/.025))
        crease-=.0035*max(0,1-abs((u+(.085 if index==0 else -.095)+shift)/.025))
        plane=RAIL_Y-FRONT_OFFSET
        p.y=plane+(p.y-plane)*(1-.15*weight)+crease*weight
    obj.data.update();recalc(obj)
    after=np.asarray([v.co[:] for v in obj.data.vertices])
    return {'method':'Reduce depth slack below the chest by 15 percent and retain two narrow grain-aligned creases; upper support band unchanged',
            'maximum_displacement_m':float(np.linalg.norm(after-before,axis=1).max()),
            'unchanged_above_m':1.55}


def surface(obj,index):
    obj.data.update()
    mat=obj.data.materials[0].copy();mat.name=obj.name+'_DryDustWool'
    obj.data.materials.clear();obj.data.materials.append(mat)
    shader=mat.node_tree.nodes['Principled BSDF']
    shader.inputs['Specular IOR Level'].default_value=.05
    shader.inputs['Sheen Weight'].default_value=0
    shader.inputs['Roughness'].default_value=.99
    normal=next(n for n in mat.node_tree.nodes if n.type=='NORMAL_MAP')
    normal.inputs['Strength'].default_value=.40
    uv=obj.data.uv_layers.active
    weave_uv=obj.data.uv_layers.new(name='WeaveUV')
    for old,new in zip(uv.data,weave_uv.data):new.uv=old.uv
    for loop in uv.data:
        u,v=loop.uv
        loop.uv=((u/8+.26)/.52,(v/8-.35)/1.36)
    obj.data.uv_layers.active=uv
    nodes,links=mat.node_tree.nodes,mat.node_tree.links
    normal_tex=normal.inputs['Color'].links[0].from_node
    coords=nodes.new('ShaderNodeUVMap');coords.uv_map='WeaveUV'
    links.new(coords.outputs['UV'],normal_tex.inputs['Vector'])
    color_tex=shader.inputs['Base Color'].links[0].from_node
    color_uv=nodes.new('ShaderNodeUVMap');color_uv.uv_map=uv.name
    links.new(color_uv.outputs['UV'],color_tex.inputs['Vector'])
    size=1536
    dust=np.zeros((size,size),dtype=np.float32)
    obj.data.calc_loop_triangles()
    weights=np.asarray([max(0.,v.normal.z) for v in obj.data.vertices])
    for triangle in obj.data.loop_triangles:
        q=np.asarray([uv.data[i].uv[:] for i in triangle.loops])*(size-1)
        low=np.maximum(np.floor(q.min(0)).astype(int),0)
        high=np.minimum(np.ceil(q.max(0)).astype(int),size-1)
        if np.any(low>high):continue
        yy,xx=np.mgrid[low[1]:high[1]+1,low[0]:high[0]+1]
        matrix=np.array([q[1]-q[0],q[2]-q[0]]).T
        determinant=np.linalg.det(matrix)
        if abs(determinant)<1e-9:continue
        bary=np.einsum('ij,...j->...i',np.linalg.inv(matrix),np.stack([xx-q[0,0],yy-q[0,1]],axis=-1))
        b,c=bary[:,:,0],bary[:,:,1];a=1-b-c
        inside=(a>=-1e-6)&(b>=-1e-6)&(c>=-1e-6)
        values=weights[np.asarray(triangle.vertices)]
        patch=(a*values[0]+b*values[1]+c*values[2])*inside
        target=dust[low[1]:high[1]+1,low[0]:high[0]+1]
        np.maximum(target,patch,out=target)
    for _ in range(3):dust=(dust*4+np.roll(dust,1,0)+np.roll(dust,-1,0)+np.roll(dust,1,1)+np.roll(dust,-1,1))/8
    z,u=np.mgrid[.35:1.71:complex(size),-.26:.26:complex(size)]
    source=bpy.data.images.load(str(ASSETS/'sofa/weave.png'),check_existing=True)
    pixels=np.asarray(source.pixels[:],dtype=np.float32).reshape(source.size[1],source.size[0],4)
    grain=pixels[:,:,:3].mean(2);grain=np.clip(grain/np.median(grain),.65,1.35)
    woven=grain[(z*8*source.size[1]).astype(int)%source.size[1],(u*8*source.size[0]).astype(int)%source.size[0]]
    fade=.88+.08*np.sin(u*37+z*13)+.05*np.sin(z*51-u*11)
    color=np.array((.46,.33,.29) if index==0 else (.33,.40,.44))
    base=color[None,None,:]*fade[:,:,None]*(.55+.45*woven[:,:,None])
    mask=.95*(1-np.exp(-dust*10))*np.clip(.35+.9*clump_noise(size,95400+index),0,1)
    rgba=np.ones((size,size,4),dtype=np.float32)
    rgba[:,:,:3]=base
    control_name=obj.name+'_NoFoldDust'
    if bpy.data.images.get(control_name):bpy.data.images.remove(bpy.data.images[control_name])
    control=image_from_array(control_name,rgba,TEXTURES/(obj.name.lower()+'_no_fold_dust.png'))
    control.use_fake_user=True
    rgba[:,:,:3]=base*(1-mask[:,:,None])+np.array((.78,.74,.65))*mask[:,:,None]*(.65+.35*woven[:,:,None])
    color_tex.image=image_from_array(obj.name+'_DryDustAtlas',rgba,TEXTURES/(obj.name.lower()+'_dry_dust.png'))
    mat['dust_control_image']=control.name
    return {'atlas_size':size,'upward_dust_pixels':int(np.count_nonzero(mask>.1)),
            'maximum_dust_mix':float(mask.max()),'roughness':.99,'normal_strength':.40,
            'method':'Physical sewn-pattern UV atlas, pigment fade and grain-clustered upward-fold dust; separate repeating weave UV'}


def clump_noise(size,seed):
    rng=np.random.default_rng(seed)
    result=np.zeros((size,size),dtype=np.float32)
    for grid,weight in ((17,.6),(43,.3),(109,.1)):
        values=rng.random((grid+1,grid+1),dtype=np.float32)
        coordinate=np.linspace(0,grid,size,endpoint=False)
        cell=coordinate.astype(int);fraction=coordinate-cell
        fraction=fraction*fraction*(3-2*fraction)
        a=values[cell[:,None],cell[None,:]]*(1-fraction[None,:])+values[cell[:,None],cell[None,:]+1]*fraction[None,:]
        b=values[cell[:,None]+1,cell[None,:]]*(1-fraction[None,:])+values[cell[:,None]+1,cell[None,:]+1]*fraction[None,:]
        result+=weight*(a*(1-fraction[:,None])+b*fraction[:,None])
    return result


def powder(name,x,seed):
    obj=powder_card(name,(x,-.11,SHELF_SURFACE),POWDER_RADIUS,TEXTURES,seed,sectors=32)
    obj['aged_export']=True;obj['finish_generated']=True
    mat=obj.data.materials[0]
    shader=mat.node_tree.nodes['Principled BSDF']
    shader.inputs['Roughness'].default_value=.99
    shader.inputs['Specular IOR Level'].default_value=.05
    normal=next(n for n in mat.node_tree.nodes if n.type=='NORMAL_MAP')
    normal.inputs['Strength'].default_value=.18
    texture=shader.inputs['Base Color'].links[0].from_node
    image=texture.image
    rgba=np.asarray(image.pixels[:],dtype=np.float32).reshape(image.size[1],image.size[0],4)
    size=image.size[0]
    rng=np.random.default_rng(seed+17)
    cloud=clump_noise(size,seed+18)
    density=(rgba[:,:,3]>.5)*(.42+.58*cloud)
    grains=rng.random((size,size))
    rgba[:,:,3]=(grains<density).astype(np.float32)
    rgba[:,:,:3]=np.array((.54,.50,.44))*(.62+.38*cloud[:,:,None])
    texture.image=image_from_array(name+'_NeutralPowder',rgba,TEXTURES/(name.lower()+'_neutral.png'))
    height=.003*cloud
    gy,gx=np.gradient(height)
    normals=np.stack([-gx/(2*POWDER_RADIUS[0]/size),-gy/(2*POWDER_RADIUS[1]/size),np.ones_like(gx)],axis=2)
    normals/=np.linalg.norm(normals,axis=2,keepdims=True)
    normal_rgba=np.ones((size,size,4),dtype=np.float32);normal_rgba[:,:,:3]=normals*.5+.5
    normal.inputs['Color'].links[0].from_node.image=image_from_array(name+'_PowderClumpsNormal',normal_rgba,TEXTURES/(name.lower()+'_clumps_normal.png'),True)
    normal.inputs['Strength'].default_value=.40
    return obj


def fringe_material_for_dresses():
    material=fringe_material(TEXTURES,95321,wool=True)
    shader=material.node_tree.nodes['Principled BSDF']
    texture=shader.inputs['Base Color'].links[0].from_node
    image=texture.image
    rgba=np.asarray(image.pixels[:],dtype=np.float32).reshape(image.size[1],image.size[0],4)
    alpha=rgba[:,:,3].copy()
    for offset in range(-2,3):rgba[:,:,3]=np.maximum(rgba[:,:,3],np.roll(alpha,offset,axis=1))
    grain=np.clip(rgba[:,:,:3].mean(2)/.34,.8,1.15)
    rgba[:,:,:3]=np.array((.56,.51,.43))*grain[:,:,None]
    texture.image=image_from_array('DressFringeFibres',rgba,TEXTURES/'dress_fringe_fibres.png')
    return material


def mound(name,card,x):
    count=24
    vertices=[(x,-.11,deposit_height(x,-.11,x))];uvs=[(.5,.5)];faces=[]
    for ring in range(1,5):
        r=ring/4
        for j in range(count):
            a=2*math.pi*j/count
            u=r*math.cos(a);v=r*math.sin(a)
            px=x+CORE_RADIUS[0]*u;py=-.11+CORE_RADIUS[1]*v
            vertices.append((px,py,deposit_height(px,py,x)))
            uvs.append((.5+.5*u*CORE_RADIUS[0]/POWDER_RADIUS[0],.5+.5*v*CORE_RADIUS[1]/POWDER_RADIUS[1]))
        start=1+(ring-1)*count
        if ring==1:faces.extend((0,start+j,start+(j+1)%count) for j in range(count))
        else:
            lower=start-count
            faces.extend((lower+j,lower+(j+1)%count,start+(j+1)%count,start+j) for j in range(count))
    obj=mesh(name,vertices,faces,uv=uvs)
    obj.data.materials.append(card.data.materials[0]);obj['finish_generated']=True
    return obj


def interrupt_fringe(obj,centre,index,record):
    bm=bmesh.new();bm.from_mesh(obj.data)
    intervals=((-.12,-.09),(.055,.08)) if index==0 else ((-.075,-.05),(.10,.13))
    removed=[];width=0.
    for face in bm.faces:
        root=(face.verts[0].co+face.verts[1].co)/2
        if root.z<.9 and any(lo<root.x-centre<hi for lo,hi in intervals):
            removed.append(face);width+=(face.verts[1].co-face.verts[0].co).length
    bmesh.ops.delete(bm,geom=removed,context='FACES')
    bm.to_mesh(obj.data);bm.free();obj.data.update()
    coverage=(record['authored_coverage']*record['boundary_length_m']-width)/record['boundary_length_m']
    record.update(cards=len(obj.data.polygons),triangles=len(obj.data.polygons)*2,
                  authored_coverage=coverage,coverage_pass=coverage>=.5,
                  intact_hem_intervals_m=[list(interval) for interval in intervals])
    if not record['coverage_pass']:raise ValueError('Interrupted fringe fell below the original half-boundary coverage gate')


def settled_fibres(name,x,material,seed):
    rng=np.random.default_rng(seed)
    vertices=[];faces=[];uv=[]
    for i in range(18):
        angle=rng.uniform(0,2*math.pi);radius=rng.uniform(.35,1.22)
        cx=x+CORE_RADIUS[0]*radius*math.cos(angle);cy=-.11+CORE_RADIUS[1]*radius*math.sin(angle)
        heading=rng.uniform(0,2*math.pi)
        along=np.array((math.cos(heading),math.sin(heading)))*rng.uniform(.003,.007)
        across=np.array((-math.sin(heading),math.cos(heading)))*rng.uniform(.0008,.0018)
        corners=[np.array((cx,cy))+a*along+b*across for a,b in ((-1,-1),(-1,1),(1,1),(1,-1))]
        heights=[deposit_height(p[0],p[1],x) for p in corners]
        z=max(heights)+.0008
        base=len(vertices)
        vertices.extend((p[0],p[1],z+(.0006 if j>1 else 0)) for j,p in enumerate(corners))
        variant=int(rng.integers(8));uv.extend(((0,variant/8),(1,variant/8),(1,(variant+1)/8),(0,(variant+1)/8)))
        faces.append(tuple(range(base,base+4)))
    obj=mesh(name,vertices,faces,uv=uv)
    obj.data.materials.append(material);obj['finish_generated']=True
    reverse_faces(obj)
    return obj


def blockers():
    for obj in list(bpy.context.scene.objects):
        if obj.get('finish_blocker'):bpy.data.objects.remove(obj,do_unlink=True)
    before=set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(ASSETS/'dress_uniform_aged.glb'))
    imported=[o for o in bpy.context.scene.objects if o not in before]
    for obj in imported:
        obj['finish_blocker']=True;obj['aged_export']=False;obj.hide_render=True
        if obj.parent is None:obj.scale.x=-1;obj.location=(0,-.003038027,1.82)
    for obj in imported:
        if obj.type=='MESH' and obj.name.startswith(('FallenHem','FibreDust','HeapFibres')):
            obj.location.z+=.1445+.95002-1.82
    bpy.context.view_layer.update()
    return [o for o in bpy.context.scene.objects if o.type=='MESH' and (o.get('support') or o.get('finish_blocker') or o.name.endswith('_Hanger'))]


def apply():
    contacts=blockers()
    yarn=fringe_material_for_dresses()
    record={}
    for index,(name,(_,x)) in enumerate(POSITIONS.items()):
        for suffix in ('_FrayedYarns','_FibreHeap','_FibreHeap_Base'):
            obj=bpy.data.objects[name+suffix];bpy.data.objects.remove(obj,do_unlink=True)
        obj=bpy.data.objects[name]
        edge=ragged_edges(obj,index)
        folds=stiffen_folds(obj,x,index)
        finish=surface(obj,index)
        group=obj.vertex_groups.new(name='DryFrayBoundary')
        indices=[v.index for v in obj.data.vertices if v.co.z<.90 or (1.58<v.co.z<1.67 and -.12<v.co.x-x<-.06)]
        group.add(indices,1.,'REPLACE')
        fringe,fringe_record=cards(obj,yarn,95324+index,wool=True,spacing=.014,
                                  boundary_group=group.name,blockers=contacts+[obj])
        fringe.name=name+'_FrayedYarns';fringe['finish_generated']=True
        rng=np.random.default_rng(95341+index)
        for start in range(0,len(fringe.data.vertices),4):
            factor=.50 if rng.random()<.10 else rng.uniform(.15,.30)
            for root,tip in ((start,start+3),(start+1,start+2)):
                fringe.data.vertices[tip].co=fringe.data.vertices[root].co.lerp(fringe.data.vertices[tip].co,factor)
        interrupt_fringe(fringe,x,index,fringe_record)
        reverse_faces(fringe)
        fringe_record['explicit_front_back_triangles']=len(fringe.data.polygons)*2
        deposit_x=(-.29,.29)[index]
        card=powder(name+'_FibreHeap',deposit_x,95328+index)
        mound(name+'_FibreHeap_Base',card,deposit_x)
        settled_fibres(name+'_FibreHeap_Yarns',deposit_x,yarn,95350+index)
        record[name]={'tear_lips':edge,'stiff_folds':folds,'fabric':finish,'fringe':fringe_record,
                      'deposit':'Alpha-scissor granular powder, asymmetric 26 mm core, 18 fine settled fibre cards per dress, 0.800 mm shelf gap'}
    return record


def disable_dust():
    for name in ('RoseDress','BlueDress'):
        mat=bpy.data.objects[name].data.materials[0]
        shader=mat.node_tree.nodes['Principled BSDF']
        shader.inputs['Base Color'].links[0].from_node.image=bpy.data.images[mat['dust_control_image']]
