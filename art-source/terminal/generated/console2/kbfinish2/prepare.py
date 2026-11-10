import bpy,numpy as np,math,json
from pathlib import Path
OUT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(OUT/'source.blend'))
ob=bpy.data.objects['Keyboard'];bpy.context.view_layer.objects.active=ob
bpy.ops.object.select_all(action='DESELECT');ob.select_set(True)
# All imported placeholders are discarded, including their overlapping UVs.
mesh=ob.data
# The imported atlas splits adjacent triangles into disconnected vertices.
# Weld coincident seams so outward winding and Smart UV islands are coherent.
print('input vertices',len(mesh.vertices),flush=True)
if mesh.has_custom_normals:bpy.ops.mesh.customdata_custom_splitnormals_clear()
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.remove_doubles(threshold=.000001);bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT')
mesh.update()
print('welded vertices',len(mesh.vertices),flush=True)
while mesh.uv_layers:mesh.uv_layers.remove(mesh.uv_layers[0])
mesh.uv_layers.new(name='KeyboardAtlas')
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.02);bpy.ops.object.mode_set(mode='OBJECT')
uv=mesh.uv_layers.active.data
for item in uv:item.uv=(.02+item.uv.x*.96,.02+item.uv.y*.52)
z=np.load(OUT/'segmentation.npz');labels=z['labels'];h=z['height'];base=z['base'];threshold=float(z['threshold']);xs=z['xs'];ys=z['ys']
lo=np.array([xs[0],ys[0]]);span=np.array([xs[-1]-xs[0],ys[-1]-ys[0]])
report=json.loads((OUT/'matching.json').read_text());allowed={r['label'] for r in report['regions']}
top_count=0
for p in mesh.polygons:
 c=p.center;ix=int(np.clip(round((c.x-lo[0])/span[0]*800),0,800));iy=int(np.clip(round((c.y-lo[1])/span[1]*308),0,308))
 is_top=int(labels[iy,ix]) in allowed and p.normal.z>.40 and c.z-base[iy,ix]>threshold*.90 and abs(c.z-h[iy,ix])<.003
 if is_top:
  top_count+=1
  for li in p.loop_indices:
   v=mesh.vertices[mesh.loops[li].vertex_index].co
   uv[li].uv=(.025+(xs[-1]-v.x)/span[0]*.95,.59+(ys[-1]-v.y)/span[1]*.365)
mesh.calc_loop_triangles()
tri=np.array([[mesh.vertices[i].co[:] for i in t.vertices] for t in mesh.loop_triangles],np.float32)
triuv=np.array([[uv[i].uv[:] for i in t.loops] for t in mesh.loop_triangles],np.float32)
trin=np.array([[mesh.vertices[i].normal[:] for i in t.vertices] for t in mesh.loop_triangles],np.float32)
np.savez(OUT/'atlas_geometry.npz',positions=tri,uvs=triuv,normals=trin)
print('UV triangles',len(tri),'top faces',top_count,flush=True)
mesh.materials.clear();mat=bpy.data.materials.new('Bake source');mat.use_nodes=True;mesh.materials.append(mat);nt=mat.node_tree;bs=nt.nodes.get('Principled BSDF');output=nt.nodes.get('Material Output')
for p in mesh.polygons:p.material_index=0
noise=nt.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=1600;noise.inputs['Detail'].default_value=2
bump=nt.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.13;bump.inputs['Distance'].default_value=.000055;nt.links.new(noise.outputs['Fac'],bump.inputs['Height']);nt.links.new(bump.outputs['Normal'],bs.inputs['Normal'])
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.device='CPU';scene.render.threads_mode='FIXED';scene.render.threads=8;scene.render.bake.margin=8;scene.render.bake.use_clear=True
tex=nt.nodes.new('ShaderNodeTexImage');tex.select=True;nt.nodes.active=tex
for name,kind in [('ao','AO'),('normal','NORMAL'),('pointiness','EMIT')]:
 im=bpy.data.images.new(name,width=2048,height=2048,alpha=False);im.colorspace_settings.name='Non-Color';tex.image=im;nt.nodes.active=tex
 if name=='pointiness':
  geometry=nt.nodes.new('ShaderNodeNewGeometry');emission=nt.nodes.new('ShaderNodeEmission');nt.links.new(geometry.outputs['Pointiness'],emission.inputs['Color']);nt.links.new(emission.outputs[0],output.inputs['Surface'])
 print('BAKE',name,flush=True);bpy.ops.object.bake(type=kind)
 im.filepath_raw=str(OUT/('keyboard_'+name+'.png'));im.file_format='PNG';im.save()
 print('BAKE DONE',name,flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'uv.blend'))
