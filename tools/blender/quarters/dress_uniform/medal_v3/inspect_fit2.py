"""Dump fit1 control geometry and exact camera-ray shading diagnostics."""
from pathlib import Path
import json
import sys
from collections import defaultdict
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
SOURCE=Path(__file__).resolve().parent
ROOT=SOURCE.parents[4]
OUT=ROOT/'tmp/issue130-v3/fit2'
OUT.mkdir(parents=True,exist_ok=True)
BEFORE=OUT.parent/'fit1'
folder=OUT if '--after' in sys.argv else BEFORE
suffix='after' if '--after' in sys.argv else 'before'
bpy.ops.wm.open_mainfile(filepath=str(folder/'medal-fitted.blend'))
controls={}
for part in ['Body','Loop','Bar']:
 m=bpy.data.objects[part+'_Cage'].data
 controls[part]={'vertices':[[*v.co] for v in m.vertices],'faces':[list(p.vertices) for p in m.polygons],'creases':[[*e.vertices,(m.attributes['crease_edge'].data[e.index].value if m.attributes.get('crease_edge') else 0.)] for e in m.edges]}
(OUT/('controls-'+suffix+'.json')).write_text(json.dumps(controls,separators=(',',':')))
# Diagnose the actual exported shading, including UV and split normal fans.
assets={}
for kind in ['high','low']:
 bpy.ops.import_scene.gltf(filepath=str(folder/('medal-'+kind+'.glb')))
 assets[kind]={o.name.split('_')[0]:o for o in bpy.context.selected_objects if o.type=='MESH'}
im=bpy.data.images.load(str(folder/'medal-low-normal.png'));im.colorspace_settings.name='Non-Color'
w,h=im.size;pixels=np.array(im.pixels[:]).reshape(h,w,4)
meshes={}
for kind,parts in assets.items():
 m=parts['Body'].data;m.calc_loop_triangles()
 if kind=='low':m.calc_tangents()
 v=np.array([p.co[:] for p in m.vertices])*1000;t=np.array([p.vertices[:] for p in m.loop_triangles]);ls=np.array([p.loops[:] for p in m.loop_triangles])
 meshes[kind]={'m':m,'v':v,'t':t,'ls':ls,'cn':np.array([p.vector[:] for p in m.corner_normals]),'tree':BVHTree.FromPolygons([Vector(q) for q in v],t.tolist(),all_triangles=True)}
low=meshes['low'];high=meshes['high'];m=low['m']
uv=np.array([p.uv[:] for p in m.uv_layers.active.data]);tan=np.array([p.tangent[:] for p in m.loops]);sign=np.array([p.bitangent_sign for p in m.loops])
def unit(a):return a/np.linalg.norm(a)
def bary(p,v):
 x=np.linalg.lstsq((v[1:]-v[0]).T,np.array(p)-v[0],rcond=None)[0]
 return np.r_[1-x.sum(),x]
def color(uv):
 p=uv*[w,h]-.5;x,y=np.floor(p).astype(int);u,v=p-[x,y];x0,x1=np.clip([x,x+1],0,w-1);y0,y1=np.clip([y,y+1],0,h-1)
 return (1-v)*((1-u)*pixels[y0,x0,:3]+u*pixels[y0,x1,:3])+v*((1-u)*pixels[y1,x0,:3]+u*pixels[y1,x1,:3])
camdata=bpy.data.cameras.new('Fit2Diagnostic');camdata.type='ORTHO';cam=bpy.data.objects.new('Fit2Diagnostic',camdata);bpy.context.scene.collection.objects.link(cam)
views={'front':((0,-90,5),(0,0,5),50.5),'rear':((0,90,5),(0,0,5),50.5),'star-close':((-10,-90,10),(0,-3,0),23.)}
result={'views':{},'visual_assessment':'Not performed.'}
for view,(pos,target,scale) in views.items():
 cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update()
 rows=[];direction=cam.matrix_world.to_quaternion()@Vector((0,0,-1))
 box=(110,110,790,790) if view=='star-close' else (140,220,760,860)
 for py in range(box[1],box[3],3):
  for px in range(box[0],box[2],3):
   origin=cam.matrix_world@Vector(((px/900-.5)*scale,(.5-py/900)*scale,0))
   hc,hn,hi,_=high['tree'].ray_cast(origin,direction);lc,ln,li,_=low['tree'].ray_cast(origin,direction)
   if hc is None or lc is None:continue
   ht=high['t'][hi];lt=low['t'][li];hls=high['ls'][hi];lls=low['ls'][li]
   hw=bary(hc,high['v'][ht]);lw=bary(lc,low['v'][lt]);normal=unit(lw@low['cn'][lls]);reference=unit(hw@high['cn'][hls]);tangent=unit(lw@tan[lls]);tangent=unit(tangent-normal*(tangent@normal));b=np.cross(normal,tangent)*np.sign(lw@sign[lls]);tex=color(lw@uv[lls])*2-1;mapped=unit(tex[0]*tangent+tex[1]*b+tex[2]*normal)
   angle=float(np.degrees(np.arccos(np.clip(mapped@reference,-1,1))))
   rows.append([px,py,*hc,*hn,*reference,*lc,angle,li,*(lw@uv[lls])])
 result['views'][view]={'camera_matrix':np.array(cam.matrix_world).tolist(),'scale_mm':scale,'rows':rows}
 print('PROJECTED',suffix,view,len(rows),'normal-error-p95/max',np.percentile(np.array(rows)[:,-4],[95,100]).tolist(),flush=True)
# Local UV-island and sliver data at the reported notch.
center=np.array(json.loads((BEFORE/'features.json').read_text())['star_center_mm']);angle=np.radians(338.9333);axis=np.array([np.cos(angle),np.sin(angle)]);tangent=np.array([-axis[1],axis[0]])
cent=low['v'][low['t']].mean(1);q=cent[:,[0,2]]-center;sel=(abs(q@axis-5.994663)<1.5)&(abs(q@tangent)<1.5)&(cent[:,1]<0)
records=[]
for i in np.flatnonzero(sel):
 p=low['v'][low['t'][i]];u=uv[low['ls'][i]];cross=np.linalg.norm(np.cross(p[1]-p[0],p[2]-p[0]));lens=np.linalg.norm(p-np.roll(p,1,axis=0),axis=1)
 records.append({'triangle':int(i),'vertices_mm':p.tolist(),'uv':u.tolist(),'area_mm2':float(cross/2),'aspect':float(lens.max()**2/cross),'uv_area_texels':float(abs(np.cross(u[1]-u[0],u[2]-u[0]))*w*h/2)})
result['notch_338_93_triangles']=records
(OUT/('projection-'+suffix+'.json')).write_text(json.dumps(result,separators=(',',':')))
print('INSPECT_FIT2_COMPLETE',suffix,flush=True)
