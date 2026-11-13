"""Embed measured curves in a sparse connected cage and fit suspension parts."""
from pathlib import Path
import json,sys,math
from collections import defaultdict
import bpy,bmesh
import numpy as np
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt
from mathutils.bvhtree import BVHTree
SOURCE=Path(__file__).resolve().parent;ROOT=SOURCE.parents[4];OUT=ROOT/'tmp/issue130-v3/fit1'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
fit=json.loads((OUT/'fit-report.json').read_text());fdata=json.loads((OUT/'features.json').read_text());samples=json.loads((OUT/'cage-samples.json').read_text())
features=fdata['features'];side=np.array(samples['side_mm']);center=np.array(fdata['star_center_mm']);origin=np.array(fit['raw_origin']);scale=fit['uniform_scale']

def obj(name,v,f):
 m=bpy.data.meshes.new(name);m.from_pydata((np.array(v)/1000).tolist(),[],f);m.update();o=bpy.data.objects.new(name,m);bpy.context.scene.collection.objects.link(o);return o

def activate(o):
 bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o

rawdata=json.loads((OUT/'raw-arrays.json').read_text())[0];raw=obj('Raw_Frozen_Uniform32mm',np.array(rawdata['vertices'])*1000,rawdata['triangles'])
vertices=[];lookup={}
def add(p):
 key=tuple(np.round(p,5))
 if key not in lookup:lookup[key]=len(vertices);vertices.append(np.array(p))
 return lookup[key]
side_ids=[[add(p) for p in band] for band in side]
faces=[];fields=[];creases={};paths=[]

def patch(boundary,free,front=True):
 points=[];source=[];local={};edges=[];labels=[]
 def point(i):
  if i not in local:local[i]=len(points);points.append(vertices[i]);source.append(i)
  return local[i]
 def path(ids,name,closed=False):
  seq=[point(i) for i in ids]
  if closed:seq.append(seq[0])
  for a,b in zip(seq,seq[1:]):
   if a!=b:edges.append((a,b));labels.append(name)
  paths.append({'name':name,'vertices':ids})
 path(boundary,'front_transition' if front else 'rear_transition',True)
 if front:
  for f in features:
   if f['name'] in ['outer_silhouette','rear_transition']:continue
   ids=[add(np.array(p)) for p in f['points_mm']];path(ids,f['name'],f['closed'])
 for p in free:point(add(np.array(p)))
 result=delaunay_2d_cdt([Vector(p[[0,2]]/1000) for p in points],edges,[[local[i] for i in boundary]],1,1e-9,True)
 coords,ee,ff,origins,eorig,_=result;mapping=[]
 for p,ids in zip(coords,origins):
  assert ids,('Unmeasured constraint crossing',p[:])
  values=np.array(points)[ids];assert np.ptp(values,axis=0).max()<.00002
  mapping.append(source[ids[0]])
 for f in ff:
  ids=[mapping[i] for i in f];p=np.array(vertices)[ids];normal=np.cross(p[1]-p[0],p[2]-p[0])[1]
  if (front and normal>0) or (not front and normal<0):ids.reverse()
  faces.append(ids);fields.append(0)
 for edge,source_edges in zip(ee,eorig):
  names={labels[i] for i in source_edges if i<len(labels)};key=tuple(sorted(mapping[i] for i in edge))
  if not names:continue
  strength=1. if any(n.startswith('star_') for n in names) else .45
  if front and any(n.startswith(('star_ridge','star_valley')) for n in names):
   r=np.linalg.norm(np.array(vertices)[list(key)][:,[0,2]]-center,axis=1)
   if r.min()<.85:strength=0.
  creases[key]=strength
patch(side_ids[0],samples['front_free_mm'])
front_face_count=len(faces)
patch(side_ids[-1],samples['rear_free_mm'],False)
for a,b in zip(side_ids,side_ids[1:]):
 for j in range(len(a)):
  faces.append([a[j],b[j],b[(j+1)%len(a)],a[(j+1)%len(a)]]);fields.append(0)
for band_index,ids in enumerate(side_ids):
 for a,b in zip(ids,ids[1:]+ids[:1]):creases[tuple(sorted((a,b)))]=.2 if band_index==2 else .35
cage=obj('Body_Cage',vertices,faces);bm=bmesh.new();bm.from_mesh(cage.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));assert all(e.is_manifold for e in bm.edges),'Body cage not closed';bm.to_mesh(cage.data);bm.free();cage.data.update()
weights=cage.data.attributes.new('crease_edge','FLOAT','EDGE')
for e in cage.data.edges:weights.data[e.index].value=creases.get(tuple(sorted(e.vertices)),0.)
for p in cage.data.polygons:p.use_smooth=True
# Polygon membership comes from the inserted graph, never height/radius labels.
# The external fairer floods across uncreased edges to find the enamel annulus.
(OUT/'sparse-cage.json').write_text(json.dumps({'vertices':[p.co[:] for p in cage.data.vertices],'faces':[list(p.vertices) for p in cage.data.polygons],'front_face_count':front_face_count,'creases':[[*e,w] for e,w in creases.items()],'paths':paths},separators=(',',':')))

# Reuse the generated-part remesher and sparse limit fitting, without symmetry.
def split(name,index):
 bm=bmesh.new();bm.from_mesh(raw.data)
 def cut(axis,value,positive,upper=False):
  plane=Vector((0,0,0));plane[axis]=(value-origin[axis])*scale
  normal=Vector((0,0,0));normal[axis]=1
  fs=[f for f in bm.faces if all(v.co.z>(.80-origin[2])*scale for v in f.verts)] if upper else list(bm.faces)
  es={e for f in fs for e in f.edges};vs={v for f in fs for v in f.verts}
  bmesh.ops.bisect_plane(bm,geom=list(vs)+list(es)+fs,dist=1e-9,plane_co=plane,plane_no=normal,clear_inner=positive,clear_outer=not positive)
 cut(2,.455,True)
 if index==1:
  cut(0,-.13,True,True);cut(0,.13,False,True)
 else:
  cut(2,.80,True)
  for x in [-.13,.13]:
   plane=Vector(((x-origin[0])*scale,0,0));bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-9,plane_co=plane,plane_no=Vector((1,0,0)))
  remove=[f for f in bm.faces if -.13+1e-6<f.calc_center_median().x/scale+origin[0]<.13-1e-6];bmesh.ops.delete(bm,geom=remove,context='FACES')
 fill=bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0)['faces'];bmesh.ops.triangulate(bm,faces=fill);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 assert all(e.is_manifold for e in bm.edges),(name,'split manifold')
 m=bpy.data.meshes.new(name+'_RawGuide');bm.to_mesh(m);bm.free();o=bpy.data.objects.new(name+'_RawGuide',m);bpy.context.scene.collection.objects.link(o);return o
for index,name,target in [(1,'Loop',220),(2,'Bar',180)]:
 guide=split(name,index);o=bpy.data.objects.new(name+'_Cage',guide.data.copy());bpy.context.scene.collection.objects.link(o);activate(o)
 for p in o.data.vertices:p.co/=scale
 dec=o.modifiers.new('Temporary_topology_guide','DECIMATE');dec.ratio=min(1,8000/len(o.data.polygons));dec.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=dec.name)
 print('QUADRIFLOW_START',name,flush=True)
 bpy.ops.object.quadriflow_remesh(use_mesh_symmetry=False,use_preserve_sharp=False,use_preserve_boundary=True,smooth_normals=True,mode='FACES',target_faces=target,seed=130)
 for p in o.data.vertices:p.co*=scale
 guide.data.calc_loop_triangles();tree=BVHTree.FromPolygons([p.co for p in guide.data.vertices],[t.vertices[:] for t in guide.data.loop_triangles],all_triangles=True)
 v=np.array([tree.find_nearest(p.co)[0][:] for p in o.data.vertices]);initial=v.copy();adj=[set() for _ in v]
 for e in o.data.edges:a,b=e.vertices;adj[a].add(b);adj[b].add(a)
 # Sparse Taubin fairing preserves the measured hardware's overall form.
 for k in range(24):
  coefficient=.35 if k%2==0 else -.37
  delta=np.array([v[list(ns)].mean(0)-v[i] for i,ns in enumerate(adj)])*coefficient
  length=np.linalg.norm(delta,axis=1);delta*=np.minimum(1,.00006/np.maximum(length,1e-20))[:,None];v+=delta
 for p,q in zip(o.data.vertices,v):p.co=q
 for p in o.data.polygons:p.use_smooth=True
 fit['parts'][name]={'vertices':len(v),'faces':len(o.data.polygons),'method':'Sparse QuadriFlow topology on split generated guide; nearest raw samples at cage controls only, followed by 24 bounded Taubin steps; no dense projection.','fairing_max_mm':float(np.linalg.norm(v-initial,axis=1).max()*1000),'thinning':'None; generated cross-section retained. Internal junction caps only.'}
 print('HARDWARE_FITTED',name,fit['parts'][name],flush=True)
(OUT/'fit-report.json').write_text(json.dumps(fit,indent=2))
for o in [cage]+[bpy.data.objects[n+'_Cage'] for n in ['Loop','Bar']]:
 s=o.modifiers.new('Clean_surface_from_sparse_controls','SUBSURF');s.levels=s.render_levels=2
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'medal-cage.blend'));print('CAGE_COMPLETE',len(vertices),len(faces),flush=True)
