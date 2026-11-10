import bpy, json, numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).resolve().parent;ROOT=O.parent;N=2048
bpy.ops.wm.open_mainfile(filepath=str(O/'geometry.blend'));scene=bpy.context.scene;body=bpy.data.objects['ConsoleBody']
a=np.array([body.matrix_world@v.co for v in body.data.vertices]);centroid=(a.min(0)+a.max(0))/2;scale=float(np.max(np.abs(a-centroid)))
old=set(scene.objects);bpy.ops.import_scene.gltf(filepath=str(O/'console-painted-normalized.glb'));painted=next(o for o in scene.objects if o not in old and o.type=='MESH')
for v in painted.data.vertices:v.co=Vector(np.array(v.co)*scale+centroid)
painted.data.update();bpy.context.view_layer.update()
pa=np.array([painted.matrix_world@v.co for v in painted.data.vertices]);assert np.max(np.abs(pa.min(0)-a.min(0)))<.0001,(pa.min(0),a.min(0));assert np.max(np.abs(pa.max(0)-a.max(0)))<.0001
source=painted.data.materials[0];nt=source.node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED');out=next(n for n in nt.nodes if n.type=='OUTPUT_MATERIAL');em=nt.nodes.new('ShaderNodeEmission');nt.links.new(bs.inputs['Base Color'].links[0].from_socket,em.inputs[0]);nt.links.new(em.outputs[0],out.inputs[0])
base=next(n.image for n in nt.nodes if n.type=='TEX_IMAGE' and n.image);base.filepath_raw=str(O/'hunyuan-original-atlas.png');base.file_format='PNG';base.save()
mat=bpy.data.materials.new('Hunyuan paint on Smart UV atlas');mat.use_nodes=True;body.data.materials.clear();body.data.materials.append(mat);nt=mat.node_tree
im=bpy.data.images.new('HunyuanSmartUV',N,N,alpha=False);im.colorspace_settings.name='sRGB';t=nt.nodes.new('ShaderNodeTexImage');t.image=im;nt.nodes.active=t
scene.render.engine='CYCLES';scene.cycles.samples=1;scene.render.bake.use_selected_to_active=True;scene.render.bake.cage_extrusion=.004;scene.render.bake.max_ray_distance=.008;scene.render.bake.margin=16
bpy.ops.object.select_all(action='DESELECT');painted.select_set(True);body.select_set(True);bpy.context.view_layer.objects.active=body;bpy.ops.object.bake(type='EMIT');im.filepath_raw=str(O/'hunyuan-albedo.png');im.file_format='PNG';im.save();nt.links.new(t.outputs['Color'],nt.nodes.get('Principled BSDF').inputs['Base Color'])
bpy.data.objects.remove(painted,do_unlink=True);scene.render.bake.use_selected_to_active=False
# Generated lighting and screen pigment are reduced to bounded paint variation before wear.
pix=np.array(im.pixels[:],np.float32).reshape(N,N,4);lum=pix[:,:,0]*.2126+pix[:,:,1]*.7152+pix[:,:,2]*.0722;assert np.isfinite(lum).all();valid=lum>.015;med=float(np.median(lum[valid]));ratio=np.clip(lum/max(med,.01),.65,1.35);pix[:,:,:3]=ratio[:,:,None]*np.array([78,84,53])/255;im.pixels.foreach_set(pix.reshape(-1));im.save();im.pack()
bpy.ops.object.empty_add(type='PLAIN_AXES');screen=bpy.context.object;screen.name='ScreenSocket'
bpy.ops.mesh.primitive_plane_add(size=1);display=bpy.context.object;display.name='DisplayPlane'
bvh=BVHTree.FromPolygons([v.co for v in body.data.vertices],[p.vertices[:] for p in body.data.polygons]);samples=[]
for y in np.linspace(-.655,-.545,5):
 for x in np.linspace(-.39,.39,5):
  hit,n,f,d=bvh.ray_cast(Vector((x,y,.64)),Vector((0,0,-1)));assert hit is not None,(x,y);samples.append(list(hit))
samples=np.array(samples);A=np.column_stack([samples[:,:2],np.ones(len(samples))]);coeff=np.linalg.lstsq(A,samples[:,2],rcond=None)[0];res=samples[:,2]-A@coeff
# Find the extent of the planar top, excluding its rounded perimeter and the head.
normal=Vector((-coeff[0],-coeff[1],1)).normalized();top_points=[]
for face in body.data.polygons:
 c=face.center
 if -.675<c.y<-.535 and .54<c.z<.64 and face.normal.dot(normal)>.995 and abs(c.z-(coeff[0]*c.x+coeff[1]*c.y+coeff[2]))<.0015:
  top_points.extend([list(body.data.vertices[i].co) for i in face.vertices])
top_points=np.array(top_points);assert len(top_points)>10;extent_lo=top_points.min(0);extent_hi=top_points.max(0);cx,cy=(extent_lo[:2]+extent_hi[:2])/2;centre=np.array([cx,cy,coeff[0]*cx+coeff[1]*cy+coeff[2]])
bpy.ops.object.empty_add(type='PLAIN_AXES',location=centre);key=bpy.context.object;key.name='KeyboardSocket';key.rotation_euler=normal.to_track_quat('Z','Y').to_euler()
deck={'plane_z_equals_ax_plus_by_plus_c':coeff.tolist(),'height_at_centre_m':float(centre[2]),'centre_m':centre.tolist(),'extent_x_m':[float(extent_lo[0]),float(extent_hi[0])],'extent_y_m':[float(extent_lo[1]),float(extent_hi[1])],'sample_extent_x_m':[-.39,.39],'sample_extent_y_m':[-.655,-.545],'height_range_m':[float(samples[:,2].min()),float(samples[:,2].max())],'flatness_peak_to_peak_m':float(np.ptp(res)),'flatness_rms_m':float(np.sqrt(np.mean(res**2))),'ray_samples':samples.tolist(),'note':'Usable sloped deck top sampled downward from z=0.640 m; flatness is residual from its best-fit plane, not its intentional slope.'}
(O/'deck-report.json').write_text(json.dumps(deck,indent=2));(O/'screen-segmentation.json').write_text((ROOT/'finish2/screen-segmentation.json').read_text())
for ob in list(scene.objects):
 if ob.type in ('LIGHT','CAMERA'):bpy.data.objects.remove(ob,do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'source.blend'));print('TRANSFER_COMPLETE',json.dumps(deck),flush=True)
