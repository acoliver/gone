from pathlib import Path
O=Path(__file__).resolve().parent
s=(O.parent/'finish2/bake.py').read_text()
s=s.replace("render('deck-joint-before',cams['deck-joint'])",'')
s=s.replace("lo=max(.5005,float(q[1]));hi=max(lo+.003,float(q[4]))","lo=max(.50005,float(q[0])+.0001);hi=max(lo+.0015,float(q[2]))")
s=s.replace("noise.inputs['Scale'].default_value=135","noise.inputs['Scale'].default_value=110")
s=s.replace("ramp(noise.outputs['Fac'],.35,.60)","ramp(noise.outputs['Fac'],.28,.55)")
s=s.replace("chip=ramp(chip,.10,.55)","chip=ramp(chip,.065,.42)")
s=s.replace("ramp(noise.outputs['Fac'],.42,.66)","ramp(noise.outputs['Fac'],.43,.67)")
s=s.replace(")),.25,.50)",")),.32,.66)")
start=s.index('# Project deck-joint faces');end=s.index('under=tuple',start)
s=s[:start]+'''# Reuse the finish2 layers without its texture-only joint camouflage.
def linear(c):return np.where(c<=.04045,c/12.92,((c+.055)/1.055)**2.4)
# Long fine broken scuffs follow object coordinates across UV seams.
stretch=node('ShaderNodeVectorMath');stretch.operation='MULTIPLY';link(uv.outputs['Object'],stretch.inputs[0]);stretch.inputs[1].default_value=(35,440,140)
scuffnoise=node('ShaderNodeTexNoise');scuffnoise.inputs['Scale'].default_value=1;scuffnoise.inputs['Detail'].default_value=2;link(stretch.outputs[0],scuffnoise.inputs['Vector'])
scuff=mathnode('MULTIPLY',ramp(scuffnoise.outputs['Fac'],.69,.80),ramp(noise.outputs['Fac'],.45,.63))
paint=mix(paint,tuple(linear(np.array([103,108,73])/255))+(1,),mathnode('MULTIPLY',scuff,.40))
calibration=node('ShaderNodeMixRGB');calibration.blend_type='MULTIPLY';calibration.inputs[0].default_value=1.;link(paint,calibration.inputs[1]);calibration.inputs[2].default_value=(1,1,1,1);paint=calibration.outputs[0]
''' + s[end:]
s=s.replace("grime=mathnode('POWER',mathnode('SUBTRACT',1.,aotex.outputs['Color']),1.25);colour=mix(colour,(.013,.017,.009,1),mathnode('MULTIPLY',grime,.58))", """grime=mathnode('POWER',mathnode('SUBTRACT',1.,aotex.outputs['Color']),1.05)
position=node('ShaderNodeSeparateXYZ');link(uv.outputs['Object'],position.inputs[0]);lower=mathnode('SUBTRACT',1.,ramp(position.outputs['Z'],.03,.43));grime=mathnode('MAXIMUM',grime,mathnode('MULTIPLY',lower,.38));colour=mix(colour,(.008,.011,.004,1),mathnode('MULTIPLY',grime,.78))""")
s=s.replace("[(-.13,.045,.020),(.13,.06,.017),(-.25,.26,.023),(-.40,.59,.018),(.40,.60,.019)]", "[(-.13,.045,.026),(.13,.06,.023),(-.25,.26,.030),(.12,.19,.022),(-.40,.505,.026),(.40,.515,.024),(-.40,.635,.021)]")
s=s.replace("albedo=bake('console-albedo',signal=colour,noncolor=False)",'''paintmasksignal=mathnode('SUBTRACT',1.,mathnode('MAXIMUM',mathnode('MAXIMUM',chip,steel),rust))
paintmask=bake('paint-mask',signal=paintmasksignal)
coverage=bake('uv-coverage',signal=mathnode('ADD',1.,0.))
pm=np.array(paintmask.pixels[:],np.float32).reshape(N,N,4)[:,:,0];cv=np.array(coverage.pixels[:],np.float32).reshape(N,N,4)[:,:,0];av=np.array(ao.pixels[:],np.float32).reshape(N,N,4)[:,:,0]
paint_texels=(pm>.95)&(cv>.99)&(av>.9)
assert np.count_nonzero(paint_texels)>10000
calibrations=[]
for iteration in range(3):
 albedo=bake('console-albedo',signal=colour,noncolor=False)
 pixels=np.array(albedo.pixels[:],np.float32).reshape(N,N,4)[:,:,:3];median=np.median(pixels[paint_texels],axis=0);calibrations.append((median*255).tolist())
 if np.max(np.abs(median*255-np.array([74,80,50])))<=1.5:break
 if iteration<2:
  old=np.array(calibration.inputs[2].default_value[:3]);ratio=linear(np.array([74,80,50])/255)/np.maximum(linear(median),.001);calibration.inputs[2].default_value=tuple(old*ratio)+(1,)
report['paint_albedo_median_srgb_255']=(median*255).tolist();report['paint_texels_measured']=int(np.count_nonzero(paint_texels));report['paint_mask_definition']='UV-covered texels with paint mask >0.95 and self-AO >0.90, excluding chips, steel, rust and deep crevices';report['albedo_calibration_medians_srgb_255']=calibrations''')
s=s.replace("report['incomplete']=['The paint smear and texture seam were repaired, but the generated mesh still has a dark geometric gap at the left deck-to-body joint. That joint was not rebuilt.']", "report['geometry']=json.loads((O/'geometry-report.json').read_text());report['keyboard_deck']=json.loads((O/'deck-report.json').read_text());report['incomplete']=[]")
s=s.replace("'base_detail_multiply':.35", "'base_detail_multiply':.35,'scuffs':'Anisotropic noise, broken by object-space high-frequency noise','lower_area_grime':.38")
s=s.replace('float_buffer=False','float_buffer=name==\'surface-position\'')
s=s.replace("edge=bake('convex-edge-mask',signal=edge_signal)","edge=bake('convex-edge-mask',signal=edge_signal)\nexec((O/'edge_bake.py').read_text())")
s=s.replace("ramp(scuffnoise.outputs['Fac'],.69,.80)","ramp(scuffnoise.outputs['Fac'],.64,.73)")
s=s.replace("paint=mix(paint,tuple(linear(np.array([103,108,73])/255))+(1,),mathnode('MULTIPLY',scuff,.40))", """chip=mathnode('MAXIMUM',chip,scuff)
paint=mix(paint,tuple(linear(np.array([103,108,73])/255))+(1,),mathnode('MULTIPLY',scuff,.40))
mottle=node('ShaderNodeTexNoise');mottle.inputs['Scale'].default_value=11;mottle.inputs['Detail'].default_value=4;link(uv.outputs['Object'],mottle.inputs['Vector']);mottletint=mix((.45,.50,.35,1),(1.3,1.3,1.1,1),mottle.outputs['Fac']);paint=mix(paint,mottletint,1.,'MULTIPLY')""")
s=s.replace("rust=ramp(rust,.12,.5);rustcol=mix((.095,.023,.006,1),(.24,.063,.012,1)","rusthalo=ramp(rust,.015,.15);colour=mix(colour,under,rusthalo);rust=ramp(rust,.12,.5);rustcol=mix((.045,.012,.003,1),(.14,.038,.008,1)")
s=s.replace("'edge_mask':'Cycles Geometry Pointiness through percentile-calibrated ColorRamp'", "'edge_mask':'14 mm object-space distance band at actual convex mesh edges; noise-broken chips and steel'")
(O/'bake.py').write_text(s)
(O/'wear-detail.png').write_bytes((O.parent/'finish2/wear-detail.png').read_bytes())
print('Prepared finish3 bake script')
