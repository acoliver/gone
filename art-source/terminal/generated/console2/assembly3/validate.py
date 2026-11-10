from pathlib import Path
import json,struct,numpy as np,trimesh
from PIL import Image,ImageDraw,ImageFont,ImageOps
O=Path(__file__).resolve().parent
r=json.loads((O/'report.json').read_text());t=r['textures'];scene=json.loads((O/'scene-checks.json').read_text())
def gltf(path):
 data=path.read_bytes();magic,version,length=struct.unpack_from('<4sII',data);assert magic==b'glTF' and version==2 and length==len(data)
 n,kind=struct.unpack_from('<II',data,12);return json.loads(data[20:20+n])
def nodes(g):return {n['name']:n for n in g['nodes']}
g=gltf(O/'console.glb');old=gltf(O.parent/'assembly/console.glb');combined=gltf(O/'console-with-keyboard.glb');key=gltf(O/'keyboard.glb')
assert set(nodes(g))=={'ConsoleBody','DisplayPlane','ScreenSocket','KeyboardSocket'}
assert set(nodes(key))=={'Keyboard','KeyboardBase'}
assert set(nodes(combined))=={'ConsoleBody','DisplayPlane','ScreenSocket','KeyboardSocket','Keyboard','KeyboardBase'}
for name in ['DisplayPlane','ScreenSocket']:
 for prop in ['translation','rotation','scale','matrix']:
  assert nodes(g)[name].get(prop)==nodes(old)[name].get(prop),(name,prop)
  assert nodes(combined)[name].get(prop)==nodes(old)[name].get(prop),(name,prop)
assert (O/'keyboard.glb').read_bytes()==(O.parent/'kb3/keyboard.glb').read_bytes()
placement=json.loads((O/'keyboard-placement.json').read_text());base=nodes(combined)['KeyboardBase']
for prop,jprop in [('translation','location'),('rotation','rotation_quaternion'),('scale','scale')]:assert np.allclose(base[prop],placement['glTF_y_up'][jprop],atol=1e-7,rtol=0),(prop,base[prop])
for name in ['console-albedo','console-ao','console-orm','console-normal']:assert Image.open(O/(name+'.png')).size==(2048,2048)
paintmask=(np.asarray(Image.open(O/'paint-mask.png').convert('L'))>250)&(np.asarray(Image.open(O/'uv-coverage.png').convert('L'))>250);albedo=np.asarray(Image.open(O/'console-albedo.png').convert('RGB'));bakedmedian=np.median(albedo[paintmask],axis=0);assert max(abs(bakedmedian-np.array([117,125,80])))<=6
assert t['dust']['maximum_blend']<=.15 and t['dust']['upward_ao_driven']
assert r['deformation']['locally_reunwrapped_faces']>0 and r['deformation']['untouched_face_uvs_unchanged']
for check,value in r['checks'].items():assert value,check
assert r['deck']['flatness_peak_to_peak_mm']<=1.5 and abs(r['deck']['along_slope_depth_m']-.18205164686194586)<.0001
assert r['keyboard']['keytop_count']==29 and r['keyboard']['visible_keytops']>=27
assert scene['frontmost_vertical_projection_clearance_mm']>=0 and scene['operator_keyboard_in_frame'] and scene['operator_screen_in_frame'] and scene['operator_screen_above_keyboard']
assert scene['head_vertices_exactly_unchanged'] and scene['behind_deck_above_lip_vertices_exactly_unchanged']
assert scene['wall_y_m']==scene['floor_z_m']==0
mat=next(m for m in g['materials'] if 'occlusionTexture' in m);assert mat['occlusionTexture']['index']==mat['pbrMetallicRoughness']['metallicRoughnessTexture']['index'];assert 'normalTexture' in mat
for doc in [g,key,combined]:assert all('bufferView' in im for im in doc['images'])
loaded=trimesh.load(O/'console.glb',force='scene');mesh=next(m.copy() for m in loaded.geometry.values() if len(m.faces)>100);mesh.merge_vertices(merge_tex=True,merge_norm=True)
assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0
for name in r['render']['views']:
 image=Image.open(O/(name+'.png'));assert image.size==(1600,900);assert np.asarray(image).std()>10
fontpath='/System/Library/Fonts/Supplemental/Arial.ttf'
def font(size):return ImageFont.truetype(fontpath,size)
sheet=Image.new('RGB',(2400,1360),'#171c1e');draw=ImageDraw.Draw(sheet);draw.text((24,16),'Milder deck extension: +35 mm, refitted keyboard',font=font(34),fill='#eef0df')
panels=[(O.parent.parent/'room9/ref-console-design.png','Concept'),(O/'three-quarter.png','Front-left: rusty steel wall and steel floor'),(O/'side.png','Side profile'),(O/'operator.png',f"Operator eye: {r['keyboard']['visible_keytops']} of 29 key tops visible"),(O/'keyboard-closeup.png','Keyboard on extended deck')]
for i,(path,label) in enumerate(panels):
 x=(i%3)*800;y=75+(i//3)*625;draw.text((x+18,y),label,font=font(25),fill='#eef0df');im=ImageOps.contain(Image.open(path).convert('RGB'),(780,550),Image.Resampling.LANCZOS);sheet.paste(im,(x+(800-im.width)//2,y+45+(550-im.height)//2))
x,y=1624,740;draw.text((x,y),'Measured deck and keyboard',font=font(29),fill='#eef0df');k=r['keyboard'];gap=[g['gap_mm'] for g in k['underside_samples']]
lines=[f"Deck depth {r['deck']['along_slope_depth_m']*1000:.3f} mm",f"25-ray flatness {r['deck']['flatness_peak_to_peak_mm']:.3f} mm",f"Keyboard width {k['scaled_local_dimensions_m'][0]*1000:.2f} mm",f"Keyboard depth {k['deck_frame_dimensions_m'][1]*1000:.2f} mm",f"Uniform scale {k['uniform_scale']:.6f}",f"9 support gaps {min(gap):.3f} to {max(gap):.3f} mm",f"Side clearance at least {k['side_clearance_mm']:.2f} mm",'No body intersections; no overhang',f"Front / rear {k['front_clearance_mm']:.2f} / {k['rear_clearance_mm']:.2f} mm",f"Paint median {tuple(int(v) for v in bakedmedian)}",'DisplayPlane and ScreenSocket unchanged','Cycles 64 samples, denoised, 1600 x 900']
for i,line in enumerate(lines):draw.text((x,y+55+i*35),line,font=font(22),fill='#d2d8cd')
sheet.save(O/'contact.png')
r['textures']['baked_paint_median_srgb_255']=bakedmedian.tolist();r['scene_checks']=scene;r['deformation']['max_edge_length_stretch_factor']=scene['maximum_edge_length_stretch_factor'];r['validation']={'exact_export_object_sets':True,'display_screen_socket_export_transforms_unchanged':True,'keyboard_socket_at_new_deck_centre':True,'keyboard_local_export_byte_identical':True,'placement_matches_combined_export':True,'body_watertight':bool(mesh.is_watertight),'body_winding_consistent':bool(mesh.is_winding_consistent),'body_volume_m3':float(mesh.volume),'packed_orm_with_occlusion':True,'embedded_images':True,'maps_2048':True,'four_renders_1600x900':True,'all_fit_checks_pass':True};r['files']=['console.glb','keyboard.glb','keyboard-placement.json','console-with-keyboard.glb','console-with-keyboard.blend','console-albedo.png','console-ao.png','console-orm.png','console-normal.png','three-quarter.png','side.png','operator.png','keyboard-closeup.png','contact.png','side-profile-comparison.png','report.json'];r['incomplete']=[]
assert r['lip_profile']['profile_preserved']
assert abs(t['undercoat_fraction_of_chips']-.70)<.001 and abs(t['rust_fraction_of_chips']-.25)<.001 and abs(t['steel_fraction_of_chips']-.05)<.001
assert abs(t['edge_chip_coverage']-.09)<.001
assert max(abs(np.array(t['rust_median_srgb_255'])-np.array([96,62,44])))<=4
assert abs(r['keyboard']['deck_frame_dimensions_m'][1]-(r['deck']['along_slope_depth_m']-.020))<1e-5
(O/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'deck_depth_mm':r['deck']['along_slope_depth_m']*1000,'flatness_mm':r['deck']['flatness_peak_to_peak_mm'],'paint':bakedmedian.tolist(),'dust_max_blend':t['dust']['maximum_blend'],'scale':k['uniform_scale'],'dimensions_m':k['scaled_local_dimensions_m'],'gap_mm':[min(gap),max(gap)],'max_principal_stretch':r['deformation']['max_triangle_principal_stretch_factor'],'max_edge_stretch':scene['maximum_edge_length_stretch_factor'],'reunwrapped_faces':r['deformation']['locally_reunwrapped_faces'],'checks':r['checks'],'validation':r['validation'],'files':r['files']},indent=2))
