import bpy,numpy as np,math,json
from pathlib import Path
OUT=Path(__file__).resolve().parent
choice=json.loads((OUT/'chosen-shape.json').read_text());stage=json.loads((OUT/f"mesh-{choice['seed']}/stage.json").read_text());R=np.array(stage['raw_to_levelled'])
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);bpy.ops.import_scene.gltf(filepath=str(OUT/'painted-raw.glb'))
objects=[o for o in bpy.context.scene.objects if o.type=='MESH'];bpy.ops.object.select_all(action='DESELECT')
for o in objects:o.select_set(True)
bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join();ob=bpy.context.object;ob.name='Keyboard';bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);m=ob.data
v=np.array([v.co[:] for v in m.vertices])@R.T;lo=v.min(0);hi=v.max(0);v[:,:2]-=(lo[:2]+hi[:2])/2;v[:,:2]*=.8/(hi[0]-lo[0]);v[:,2]=(v[:,2]-lo[2])*.055/(hi[2]-lo[2])
for vertex,co in zip(m.vertices,v):vertex.co=co
m.update()
if m.has_custom_normals:bpy.ops.mesh.customdata_custom_splitnormals_clear()
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.remove_doubles(threshold=.000001);bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT');m.update()
m.uv_layers.active.name='PaintUV'
for mat in m.materials:
 nt=mat.node_tree;coord=nt.nodes.new('ShaderNodeUVMap');coord.uv_map='PaintUV'
 for node in list(nt.nodes):
  if node.type=='TEX_IMAGE':nt.links.new(coord.outputs['UV'],node.inputs['Vector'])
m.uv_layers.new(name='KeyboardAtlas');m.uv_layers.active_index=1;m.uv_layers['KeyboardAtlas'].active_render=True
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.02);bpy.ops.object.mode_set(mode='OBJECT')
uv=m.uv_layers.active.data
for item in uv:item.uv=(.02+item.uv.x*.96,.02+item.uv.y*.52)
z=np.load(OUT/'segmentation.npz');labels=z['labels'];h=z['height'];base=z['base'];threshold=float(z['threshold']);xs=z['xs'];ys=z['ys'];nx=len(xs)-1;ny=len(ys)-1;lo=np.array([xs[0],ys[0]]);span=np.array([xs[-1]-xs[0],ys[-1]-ys[0]]);top_y_scale=.95*span[1]/span[0]
report=json.loads((OUT/'matching.json').read_text());allowed={r['label'] for r in report['regions']};top_count=0
for p in m.polygons:
 c=p.center;ix=int(np.clip(round((c.x-lo[0])/span[0]*nx),0,nx));iy=int(np.clip(round((c.y-lo[1])/span[1]*ny),0,ny))
 is_top=int(labels[iy,ix]) in allowed and p.normal.z>.40 and c.z-base[iy,ix]>threshold*.70 and abs(c.z-h[iy,ix])<.003
 if is_top:
  top_count+=1
  for li in p.loop_indices:
   v=m.vertices[m.loops[li].vertex_index].co;uv[li].uv=(.025+(v.x-xs[0])/span[0]*.95,.60+(v.y-ys[0])/span[1]*top_y_scale)
m.calc_loop_triangles();tri=np.array([[m.vertices[i].co[:] for i in t.vertices] for t in m.loop_triangles],np.float32);triuv=np.array([[uv[i].uv[:] for i in t.loops] for t in m.loop_triangles],np.float32);trin=np.array([[m.vertices[i].normal[:] for i in t.vertices] for t in m.loop_triangles],np.float32);np.savez_compressed(OUT/'atlas_geometry.npz',positions=tri,uvs=triuv,normals=trin)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.device='CPU';scene.render.threads_mode='FIXED';scene.render.threads=8;scene.render.bake.margin=8;scene.render.bake.use_clear=True
# Preserve Hunyuan's paint variation by baking it from PaintUV into the final atlas.
im=bpy.data.images.new('Hunyuan albedo rebake',width=2048,height=2048,alpha=False);im.colorspace_settings.name='sRGB'
for mat in m.materials:
 nt=mat.node_tree;target=nt.nodes.new('ShaderNodeTexImage');target.image=im;target.select=True;nt.nodes.active=target
scene.render.bake.use_pass_direct=False;scene.render.bake.use_pass_indirect=False;scene.render.bake.use_pass_color=True
print('BAKE Hunyuan albedo',flush=True);bpy.ops.object.bake(type='DIFFUSE');im.filepath_raw=str(OUT/'paint_albedo.png');im.file_format='PNG';im.save()
m.materials.clear();mat=bpy.data.materials.new('Bake source');mat.use_nodes=True;m.materials.append(mat);nt=mat.node_tree;bs=nt.nodes.get('Principled BSDF');output=nt.nodes.get('Material Output')
for p in m.polygons:p.material_index=0;p.use_smooth=True
noise=nt.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=1600;noise.inputs['Detail'].default_value=2;bump=nt.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.13;bump.inputs['Distance'].default_value=.000055;nt.links.new(noise.outputs['Fac'],bump.inputs['Height']);nt.links.new(bump.outputs['Normal'],bs.inputs['Normal'])
tex=nt.nodes.new('ShaderNodeTexImage');tex.select=True;nt.nodes.active=tex
for name,kind in [('ao','AO'),('normal','NORMAL'),('pointiness','EMIT')]:
 im=bpy.data.images.new(name,width=2048,height=2048,alpha=False);im.colorspace_settings.name='Non-Color';tex.image=im;nt.nodes.active=tex
 if name=='pointiness':
  geometry=nt.nodes.new('ShaderNodeNewGeometry');emission=nt.nodes.new('ShaderNodeEmission');nt.links.new(geometry.outputs['Pointiness'],emission.inputs['Color']);nt.links.new(emission.outputs[0],output.inputs['Surface'])
 print('BAKE',name,flush=True);bpy.ops.object.bake(type=kind);im.filepath_raw=str(OUT/f'keyboard_{name}.png');im.file_format='PNG';im.save();print('BAKE DONE',name,flush=True)
m.uv_layers.remove(m.uv_layers['PaintUV']);m.uv_layers.active_index=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'uv.blend'));print('UV triangles',len(tri),'top faces',top_count,flush=True)
