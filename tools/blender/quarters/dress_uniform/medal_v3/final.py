"""Check final exported parity and summarize measurements and exact paths."""
from pathlib import Path
import json,struct
import numpy as np
from PIL import Image
SOURCE=Path(__file__).resolve().parent;OUT=SOURCE.parents[4]/'tmp/issue130-v3/fit1'
exec(compile((SOURCE/'surface_gate.py').read_text(),str(SOURCE/'surface_gate.py'),'exec'))

def exported(filename,retain=False):
 blob=(OUT/filename).read_bytes();size=struct.unpack_from('<I',blob,12)[0];doc=json.loads(blob[20:20+size]);binary=blob[28+size:]
 def array(index,n):
  a=doc['accessors'][index];view=doc['bufferViews'][a['bufferView']];dtype=np.dtype({5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}[a['componentType']])
  return np.ndarray((a['count'],n),dtype=dtype,buffer=binary,offset=view.get('byteOffset',0)+a.get('byteOffset',0),strides=(view.get('byteStride',n*dtype.itemsize),dtype.itemsize)).copy()
 result=[];count=0
 for mesh in doc['meshes']:
  for p in mesh['primitives']:
   ids=array(p['indices'],1).reshape(-1,3);position=array(p['attributes']['POSITION'],3);uv=array(p['attributes']['TEXCOORD_0'],2);normal=array(p['attributes']['NORMAL'],3)
   assert all(np.isfinite(a).all() for a in [position,uv,normal]),filename
   if 'TANGENT' in p['attributes']:assert np.isfinite(array(p['attributes']['TANGENT'],4)).all()
   count+=len(ids)
   if retain:result.extend(np.concatenate([position[ids],uv[ids]],axis=2).tolist())
 return count,sorted(tuple(sorted(tuple(v) for v in t)) for t in result)
base=exported('medal-low.glb',True);mapped=exported('medal-low-normalmapped.glb',True);assert base==mapped and base[0]==fit['low_triangles'];assert exported('medal-high.glb')[0]==fit['high_triangles']
import trimesh
dimensions={kind:{name:(mesh.extents*1000).tolist() for name,mesh in trimesh.load(OUT/('medal-'+kind+'.glb'),force='scene').geometry.items()} for kind in ['high','low']}
sector=json.loads((OUT/'sector-diagnostics-after.json').read_text());bake=json.loads((OUT/'bake-check.json').read_text());manifest=json.loads((OUT/'render-manifest.json').read_text())
for mesh in sector['meshes'].values():
 assert len(mesh['sectors'])==5
 assert all(value==0 for value in mesh['field_interior_flags'].values())
for prefix in ['raw','high','low','low-normalmapped']:
 for view in ['front','three-quarter','edge','rear','star-close','ring-bar-close']:assert (OUT/(prefix+'-'+view+'.jpg')).is_file()
images={}
for path in sorted(list(OUT.glob('*.jpg'))+list(OUT.glob('*.png'))):
 with Image.open(path) as im:im.load();images[path.name]=list(im.size)
features=json.loads((OUT/'features.json').read_text());spacing={}
for f in features['features']:
 p=np.array(f['points_mm']);p=np.vstack([p,p[:1]]) if f['closed'] else p;length=np.linalg.norm(np.diff(p,axis=0),axis=1);spacing[f['name']]={'controls':len(f['points_mm']),'min_mm':float(length.min()),'median_mm':float(np.median(length)),'max_mm':float(length.max())}
raw_metrics=features['source_metrics'];black=sum(row['black_core_samples'] for part in bake['parts'].values() for row in part.values());misses=sum(row['misses'] for part in bake['parts'].values() for row in part.values())
limitations=['No visual assessment was performed.','Game-camera silhouette measurements use the frozen registration in standalone projection, not mounted runtime captures.','Normal reach checks sample four interior points per low triangle; they do not certify every Cycles texel ray.',('Body side mapped-normal reconstruction error has a %.3f-degree p95 and %.3f-degree maximum against nearest-high normals. Zero ray misses do not establish shading quality.'%(bake['parts']['Body']['side']['mapped_normal_error_degrees']['p95'],bake['parts']['Body']['side']['mapped_normal_error_degrees']['max'])),'Raw contour height threshold and source low-pass decomposition are geometric proxies; they do not identify manufacturing intent.']
if misses:limitations.append(f'Geometric bake-reach diagnostics contain {misses} sampled ray misses; see bake-check.json for regions and normal errors.')
if black:limitations.append(f'Normal-map sampling contains {black} black interior samples; see bake-check.json.')
result={'method':{'source':str(SOURCE),'editable_blend':str(SOURCE/'medal-fitted.blend'),'description':fit['method'],'corrections':fit['corrections'],'parts':fit['parts'],'feature_control_spacing':spacing,'field_solver':{k:v for k,v in field.items() if k in ['method','field_components','field_laplacian_rms_per_mm','field_laplacian_max_per_mm','guidance_fidelity_per_mm2','max_control_shift_mm']},'normal_bake':json.loads((OUT/'normal-bake.json').read_text())},
 'measurements':{'high_triangles':fit['high_triangles'],'low_triangles':fit['low_triangles'],'budget':10500,'exported_per_part_xyz_extents_mm':dimensions,'raw_star':raw_metrics,'local':local,'verification':verification,'silhouette':silhouette,'notch_sector_diagnostics':sector,'bake_check':bake,'exported_geometry_uv_parity':True,'finite_exported_attributes':True,'decoded_images':images},
 'renders':manifest,'limitations':limitations,'visual_assessment':'Not performed.'}
(OUT/'result.json').write_text(json.dumps(result,indent=2))
lines=['# c01 medal fit, v3 fit1','','The generated c01 mesh has been fitted and exported. Visual quality has not been assessed.','',
 f'Editable source: `{SOURCE}/medal-fitted.blend`.',f'Output directory: `{OUT}/`.','','## Method','',fit['method'],'',fit['corrections'],'',
 'The body uses sparse measured front and rear controls with side quad bands. Its raw split guide is retained in the blend. The loop and bar use sparse fitted generated cages, with their original bulk retained. Every visible profile is sampled independently from the generated surface.',
 '', 'At fused star/rim contacts, rim search curves move outside the preceding measured contour and resample the same raw surface. The low reducer preserves projected field orientation, both hardware camera contours, and the loop contour support band. Contour-adjacent body faces receive 300x geometric-error weight; hidden rear regions reduce first.',
 '', 'The enamel has one connected source-bounded cell and zero raw fidelity. Its sparse harmonic residual RMS is %.3g per mm. High/low field interiors have zero crease, sharp or split-normal edges. No field triangles face backwards in the front projection.'%field['field_laplacian_rms_per_mm'],
 '', 'The apex has no full creases at the common central control. Full relief creases begin beyond its inner support neighbourhood. No symmetry or donor-sector replacement was applied.','','## Geometry','',
 f'High: {fit["high_triangles"]:,} triangles. Low and normal-mapped low: {fit["low_triangles"]:,} triangles, within 10,500. All exported high/low parts are watertight and consistently wound. UVs have zero positive-area overlaps and zero collapsed triangles. Exported positions, normals, UVs and mapped tangents are finite. Normal mapping preserves low geometry and TEXCOORD_0 exactly.',
 '', 'The frozen raw normalization uses a nominal 32 mm body diameter and a uniform scale. After sparse fitting, exported high body extents are %.6f by %.6f by %.6f mm in glTF X/Y/Z; low body extents are %.6f by %.6f by %.6f mm. These outside-Blender measurements preserve generated asymmetry, rather than forcing equal axial diameters.'%tuple(next(v for n,v in dimensions['high'].items() if n.startswith('Body'))+next(v for n,v in dimensions['low'].items() if n.startswith('Body'))),'', '| Camera | Maximum silhouette error, px | Conservative upper bound, px |','| --- | ---: | ---: |']
for camera,row in silhouette['cameras'].items():
 e=row['all_parts'];lines.append(f'| {camera} | {e["max_px"]:.6f} | {e["max_px"]+.0253:.6f} |')
lines+=['','Both high and low star boundaries have five detected peaks at 1 mm prominence. Raw notch radius spread is %.6f mm; fitted high/low spreads are %.6f / %.6f mm.'%(raw_metrics['notch_radius_spread_mm'],local['star']['high']['notch_radius_spread_mm'],local['star']['low']['notch_radius_spread_mm']),'',
 '| Notch | High radius, mm | Low radius, mm | High angle, degrees | High included angle, degrees | Low included angle, degrees |','| --- | ---: | ---: | ---: | ---: | ---: |']
for i,(a,b) in enumerate(zip(local['star']['high']['notches'],local['star']['low']['notches'])):lines.append(f'| {i} | {a["radius_mm"]:.6f} | {b["radius_mm"]:.6f} | {a["angle_degrees"]:.4f} | {a["included_angle_degrees"]:.4f} | {b["included_angle_degrees"]:.4f} |')
lines+=['','| Field statistic | High, mm | Low, mm |','| --- | ---: | ---: |']
for title,key in [('Boundary membrane residual RMS','residual_to_boundary_membrane_mm'),('Broad plane residual RMS','plane_residual_mm')]:lines.append(f'| {title} | {local["field"]["high"][key]["rms_mm"]:.6f} | {local["field"]["low"][key]["rms_mm"]:.6f} |')
lines+=['','The field retains the curvature imposed by its generated boundaries. The broad-plane residual measures that curvature; it is not a claim that the field is an ideal plane.','','### Two-way source deviation','',
 'The verifier samples actual exported triangles by area and measures closest raw triangle points. At each correspondence, clean-minus-raw equals lowpass-minus-raw plus clean-minus-lowpass. `verification.json` records both RMS components and their cross term for every region. The filter uses 240 topology-based Taubin iterations.','',
 '| Region | High clean-to-raw RMS, mm | High p95, mm | Low RMS, mm | Low p95, mm |','| --- | ---: | ---: | ---: | ---: |']
for region,a in verification['high']['clean_to_raw'].items():
 b=verification['low']['clean_to_raw'].get(region)
 if b:lines.append(f'| {region} | {a["rms_mm"]:.6f} | {a["p95_mm"]:.6f} | {b["rms_mm"]:.6f} | {b["p95_mm"]:.6f} |')
lines+=['','## Bake and five-notch diagnostics','',f'2048 tangent normal map. Front body: 0.1 mm cage / 0.25 mm rays. Rear-only pass: 0.6 mm / 1.2 mm. Non-rear core texels remain unchanged by the rear composite. The geometric reach check records {misses} sampled ray misses and {black} black interior normal-map samples. Regional mapped-normal errors are in `bake-check.json`.','',
 'Each notch diagnostic uses the same 3 mm by 3 mm tangent/radial neighbourhood. All five report cage/high/low density, triangle counts, smooth/flat flags, crease weights, actual split-normal edges, corner-to-face normal deviations and full UV-raster baked-normal deviations. The raster excludes padding and records represented area.','',
 '| Sector angle, degrees | Cage triangles | High triangles | Low triangles | Low baked normal mean, degrees |','| --- | ---: | ---: | ---: | ---: |']
for i in range(5):
 c=sector['meshes']['Cage']['sectors'][i];h=sector['meshes']['High']['sectors'][i];l=sector['meshes']['Low']['sectors'][i];lines.append(f'| {h["angle_degrees"]:.4f} | {c["triangles"]} | {h["triangles"]} | {l["triangles"]} | {l["baked_normal_raster"]["area_weighted_mean_degrees"]:.6f} |')
lines+=['','## Captures','', 'The six-view sheets use front, input-matched oblique, edge, rear, star close and ring/bar close cameras. Raw, high, low and normal-mapped low use identical clay, lights and camera settings. The input camera is an approximate orthographic blue-field ellipse fit.',
 '', 'The five-rotation sheets use fixed lights and one fixed face-on camera. The whole medal rotates by offset + k*72 degrees. Identical bottom pixel crops are extracted without image rotation. The source notch angles are not forced to 72-degree spacing.','']
for path in manifest['sheets']+manifest['rotation_sheets']:lines.append(f'- `{path}`')
lines+=['','Individual views, rotation frames and settings are listed in `render-manifest.json`. Geometry and normal assets are `medal-high.glb`, `medal-low.glb`, `medal-low-normalmapped.glb` and `medal-low-normal.png`. All are in the output directory above.','','## Limitations','']+['- '+s for s in limitations]
(OUT/'fit-notes.md').write_text('\n'.join(lines)+'\n');fit['v3_verified']=True;fit['limitations']=limitations;(OUT/'fit-report.json').write_text(json.dumps(fit,indent=2));print('FINAL_COMPLETE',fit['low_triangles'],'triangles;',len(images),'decoded images;',misses,'sampled reach misses;',black,'black interior samples',flush=True)
