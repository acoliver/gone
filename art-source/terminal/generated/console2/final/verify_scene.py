import bpy,bmesh,json,numpy as np
from pathlib import Path
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O/'console-with-keyboard.blend'))
r=json.loads((O/'report.json').read_text());body=bpy.data.objects['ConsoleBody'];m=body.data;cut=r['standing']['cut_new_z_m'];before=np.load(O/'source-vertices.npy');after=np.array([v.co[:] for v in m.vertices]);uvbefore=np.load(O/'source-uv.npy');affected=np.load(O/'affected-faces.npy');uv=np.array([l.uv[:] for l in m.uv_layers.active.data]);fixed=np.concatenate([np.arange(p.loop_start,p.loop_start+p.loop_total) for p in m.polygons if not affected[p.index]])
assert np.array_equal(uv[fixed],uvbefore[fixed]);expected=before.copy();zcut=r['standing']['z_cut_m'];delta=r['standing']['delta_m'];s=r['standing']['lower_body_vertical_scale'];expected[:,2]=np.where(before[:,2]<zcut,before[:,2]*s,before[:,2]+delta);assert np.allclose(expected,after,atol=1e-7,rtol=0)
bm=bmesh.new();bm.from_mesh(m);layer=bm.loops.layers.uv.active;uvpairs=[];edgepoints=[]
for e in bm.edges:
 if not all(abs(v.co.z-cut)<2e-7 for v in e.verts):continue
 if len(e.link_faces)!=2:raise AssertionError('Open cut ring')
 f,g=e.link_faces
 if f.calc_center_median().z>g.calc_center_median().z:f,g=g,f
 if not f.calc_center_median().z<cut<g.calc_center_median().z:continue
 a,b=e.verts
 def loop_uv(face,v):return next(l[layer].uv.copy() for l in face.loops if l.vert==v)
 for t in [.2,.5,.8]:
  uvpairs.append([list(loop_uv(f,a).lerp(loop_uv(f,b),t)),list(loop_uv(g,a).lerp(loop_uv(g,b),t))]);edgepoints.append(list(a.co.lerp(b.co,t)))
assert uvpairs;np.savez(O/'seam-samples.npz',uvs=np.array(uvpairs),points=np.array(edgepoints));assert all(e.is_manifold for e in bm.edges);bm.free()
newkey=np.array([v.co[:] for v in bpy.data.objects['Keyboard'].data.vertices]);newdisplay=np.array([v.co[:] for v in bpy.data.objects['DisplayPlane'].data.vertices]);names=['DisplayPlane','ScreenSocket','KeyboardSocket','KeyboardBase'];newmat={n:np.array(bpy.data.objects[n].matrix_world) for n in names}
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'assembly3/console-with-keyboard.blend'))
assert np.array_equal(newkey,np.array([v.co[:] for v in bpy.data.objects['Keyboard'].data.vertices]));assert np.array_equal(newdisplay,np.array([v.co[:] for v in bpy.data.objects['DisplayPlane'].data.vertices]))
for n in names:
 want=np.array(bpy.data.objects[n].matrix_world);want[2,3]+=delta;assert np.allclose(want,newmat[n],atol=1e-7,rtol=0),n
r['scene_validation']={'piecewise_vertex_map_verified':True,'upper_uv_loops_exactly_preserved':True,'keyboard_local_geometry_unchanged':True,'display_local_geometry_unchanged':True,'upper_object_matrices_only_z_translated':True,'manifold':True,'seam_edge_samples':len(uvpairs)}
(O/'report.json').write_text(json.dumps(r,indent=2));print('SCENE_DONE',flush=True)
