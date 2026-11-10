"""Sparse boot lofts fitted to the generated pair silhouette, with leather curl."""
from pathlib import Path
import json
import math
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'photo_frame'))
import small_common as sc


def loft(name, sections, offset, mat, sides=24):
    vertices=[]
    for z,rx,ry,cy in sections:
        exponent=2.5 if name.startswith(('Sole','ForeSole')) else 3.5-1.5*min(1,max(0,(z-.08)/.08))
        for i in range(sides):
            c=math.cos(i*math.tau/sides); s=math.sin(i*math.tau/sides)
            vertices.append((offset+rx*math.copysign(abs(c)**(2/exponent),c),
                             cy+ry*math.copysign(abs(s)**(2/exponent),s),z))
    faces=[tuple(reversed(range(sides)))]
    for band in range(len(sections)-1):
        faces.extend((band*sides+i,band*sides+(i+1)%sides,
                      (band+1)*sides+(i+1)%sides,(band+1)*sides+i) for i in range(sides))
    faces.append(tuple(range((len(sections)-1)*sides,len(sections)*sides)))
    obj=sc.bt.cage(name,vertices,faces,mat,0)
    for p in obj.data.polygons:
        p.use_smooth=len(p.vertices)==4
    return obj


def assemble(m):
    shader=m['Leather'].node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value=(.012,.006,.003,1)
    shader.inputs['Roughness'].default_value=.33
    shader.inputs['Specular IOR Level'].default_value=.28
    import bpy
    nodes=m['Leather'].node_tree.nodes
    grain=nodes.new('ShaderNodeTexImage')
    grain.image=bpy.data.images.load(str(sc.ROOT/'assets/props/quarters/textures/boots/Leather_clean_normal.png'))
    grain.image.colorspace_settings.name='Non-Color'
    grain.image.pack()
    normal=nodes.new('ShaderNodeNormalMap')
    m['Leather'].node_tree.links.new(grain.outputs['Color'],normal.inputs['Color'])
    m['Leather'].node_tree.links.new(normal.outputs['Normal'],shader.inputs['Normal'])
    rubber=m['Rubber'].node_tree.nodes['Principled BSDF']
    rubber.inputs['Base Color'].default_value=(.006,.006,.005,1)
    rubber.inputs['Roughness'].default_value=.82
    rubber.inputs['Specular IOR Level'].default_value=.12
    guide=sc.bt.load_guide(sc.ROOT/'tmp/small/boots/guide.glb',(.30,.41,.32))
    guide['generation']={'model':'hunyuan3d-dit-v2-mv','octree_resolution':320,'seed':0,
                         'remove_bg':True,'min_component_faces':50,
                         'image':'docs/art/quarters/sheets/boots/hero.png'}
    import numpy as np
    guides=[o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith('Guide_')]
    points=np.array([tuple(v.co) for obj in guides for v in obj.data.vertices])
    guide['fitted_sections']={}
    for side,x in [('L',-.082),('R',.082)]:
        loft('Sole_'+side,[(.024,.061,.159,-.002),(.030,.065,.160,-.002),
                          (.036,.062,.155,-.002),(.040,.058,.151,-.002)],x,m['Rubber'])
        loft('ForeSole_'+side,[(0,.057,.086,-.071),(.005,.061,.089,-.071),
                              (.027,.059,.088,-.071)],x,m['Rubber'])
        sc.box('Heel_'+side,(.091,.077,.029),(x,.103,.0145),m['Rubber'],.003)
        # The loft turns over the shaft lip and descends to a closed inner floor.
        sections=[(.024,.056,.148,-.002),(.041,.058,.144,-.003),
                  (.065,.054,.133,.002),(.085,.050,.108,.024),
                  (.110,.047,.077,.052),(.119,.048,.070,.057),
                  (.128,.045,.066,.061),(.136,.047,.062,.064),
                  (.145,.045,.060,.066),(.158,.044,.061,.067),
                  (.195,.051,.062,.068),(.276,.056,.064,.068),
                  (.297,.049,.058,.068),(.300,.047,.056,.068),
                  (.297,.045,.052,.068),(.276,.043,.051,.068),
                  (.195,.040,.049,.068),(.158,.037,.044,.068)]
        samples=[]
        half=(points[:,0]<0) if x<0 else (points[:,0]>0)
        guide_height=float(points[half,2].max())
        for i,(z,rx,ry,cy) in enumerate(sections[:14]):
            guide_z=z*guide_height/.30
            band=points[(np.abs(points[:,2]-guide_z)<.009)&half]
            if len(band)<20:
                raise ValueError(f'Insufficient Hunyuan section at {side} z={z}')
            lo,hi=np.percentile(band[:,:2],[3,97],axis=0)
            measured=((hi[0]-lo[0])/2,(hi[1]-lo[1])/2,(hi[1]+lo[1])/2)
            samples.append({'z':z,'guide_rx_ry_cy':list(measured)})
            sections[i]=(z,.75*rx+.25*measured[0],.75*ry+.25*measured[1],.75*cy+.25*measured[2])
        outer=np.array(sections[:14])
        for i in range(14,len(sections)):
            z=sections[i][0]
            sections[i]=(z,float(np.interp(z,outer[:,0],outer[:,1]))-.006,
                         float(np.interp(z,outer[:,0],outer[:,2]))-.006,
                         float(np.interp(z,outer[:,0],outer[:,3])))
        guide['fitted_sections'][side]=samples
        loft('LeatherUpper_'+side,sections,x,m['Leather'],sides=32)
        rx,ry,cy=[float(np.interp(.278,outer[:,0],outer[:,i])) for i in (1,2,3)]
        sc.box('PullTab_'+side,(.017,.005,.027),(x,cy+ry,.291),m['Leather'],.001)
        centers=[(x+rx*math.cos(i*math.tau/24),cy+ry*math.sin(i*math.tau/24),.278)
                 for i in range(24)]
        sc.tube('ShaftSeam_'+side,centers,.0012,m['Leather'],5,closed=True,frame_axis=(0,0,1))
    bpy.context.view_layer.update()
    for obj in bpy.context.scene.objects:
        if obj.type!='MESH' or obj.name.startswith('Guide_'):
            continue
        inv=obj.matrix_world.inverted()
        for vertex in obj.data.vertices:
            world=obj.matrix_world@vertex.co
            if world.z>.10:
                world.z=.10+(world.z-.10)*1.5
            vertex.co=inv@world
        obj.data.update()
    collection=bpy.data.collections['HunyuanGuide']
    collection.hide_viewport=False
    for obj in guides:
        bpy.context.view_layer.objects.active=obj
        mod=obj.modifiers.new('EditableSilhouetteGuide','DECIMATE')
        mod.ratio=.02
        bpy.ops.object.modifier_apply(modifier=mod.name)
    collection.hide_viewport=True
    guide['retained_guide_triangles']=sum(len(o.data.polygons) for o in guides)
    (Path(__file__).parent/'guide-fit.json').write_text(json.dumps(guide,indent=2)+'\n')


def deform(objects):
    import bpy
    from mathutils import Vector
    bpy.context.view_layer.update()
    for obj in objects:
        if not obj.name.startswith(('LeatherUpper','ShaftSeam','PullTab')):
            continue
        inv=obj.matrix_world.inverted()
        for vertex in obj.data.vertices:
            world=obj.matrix_world@vertex.co
            # Plastic deformation, not cloth: stiff leather lowers and curls at toe and lip.
            z=world.z
            world.z=.024+(z-.024)*.74
            toe=max(0,(-world.y-.065)/.10)
            world.z+=.020*toe**2
            shaft=min(1,max(0,(z-.12)/.29))
            world.y+=.012*shaft**2
            world.x+=math.sin(world.y*61+world.x*37)*.0025*shaft
            if z>.36:
                curl=min(1,(z-.36)/.05)
                center=-.082 if world.x<0 else .082
                world.x=center+(world.x-center)*(1+.14*curl)
                angle=math.atan2(world.y-.068,world.x-center)
                world.z-=.022*max(0,math.sin(angle+1))**2*curl
            vertex.co=inv@world
        obj.data.update()


if __name__=='__main__':
    sc.main(__file__,'boots',assemble,deform)
