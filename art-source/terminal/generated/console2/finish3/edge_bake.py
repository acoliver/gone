import bmesh,subprocess
# Measure distance to actual convex edges instead of interpolating pointiness across large caps.
bm=bmesh.new();bm.from_mesh(body.data);bm.normal_update();features=[];edge_count=0
for e in bm.edges:
 if len(e.link_faces)!=2:continue
 f,g=e.link_faces
 if f.normal.dot(g.normal)>math.cos(math.radians(2)):continue
 if (g.calc_center_median()-f.calc_center_median()).dot(f.normal)>=0:continue
 start=np.array(e.verts[0].co);end=np.array(e.verts[1].co);length=np.linalg.norm(end-start);count=max(2,int(math.ceil(length/.002))+1);features.extend(start[None,:]+np.linspace(0,1,count)[:,None]*(end-start)[None,:]);edge_count+=1
bm.free();assert len(features)>100
position=node('ShaderNodeVectorMath');position.operation='ADD';link(uv.outputs['Object'],position.inputs[0]);position.inputs[1].default_value=(.6,.8,.01);encoded=node('ShaderNodeVectorMath');encoded.operation='SCALE';encoded.inputs['Scale'].default_value=1/1.6;link(position.outputs[0],encoded.inputs[0]);position_image=bake('surface-position',signal=encoded.outputs[0]);coverage_image=bake('uv-coverage',signal=mathnode('ADD',1.,0.))
np.save(O/'surface-positions.npy',np.array(position_image.pixels[:],np.float32).reshape(N,N,4)[:,:,:3]);np.save(O/'surface-coverage.npy',np.array(coverage_image.pixels[:],np.float32).reshape(N,N,4)[:,:,0]);np.save(O/'convex-features.npy',np.array(features,np.float32))
subprocess.run(['/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python',str(O/'edge_field.py')],check=True)
edge=bpy.data.images.load(str(O/'convex-edge-mask.png'),check_existing=False);edge.colorspace_settings.name='Non-Color'
report['convex_edge_wear']={'method':'UV-baked world-position distance to convex mesh edges with dihedral above 2 degrees; avoids pointiness interpolation across large planar faces.','feature_edges':edge_count,'edge_samples':len(features),'sample_interval_m':.002,'band_width_m':.014,'full_strength_distance_m':.004,'coherent_noise_pitch_m':.04,'coherent_noise_gate':[.46,.60]}
