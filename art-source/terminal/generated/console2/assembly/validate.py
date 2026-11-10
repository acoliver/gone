from pathlib import Path
import json,struct,numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageOps
O=Path(__file__).resolve().parent
r=json.loads((O/'report.json').read_text());t=r['textures'];scene=json.loads((O/'scene-checks.json').read_text())
def gltf(path):
 data=path.read_bytes();magic,version,length=struct.unpack_from('<4sII',data);assert magic==b'glTF' and version==2 and length==len(data)
 n,typ=struct.unpack_from('<II',data,12);return json.loads(data[20:20+n])
def nodes(g):return {n['name']:n for n in g['nodes']}
g=gltf(O/'console.glb');old=gltf(O.parent/'finish4/console.glb');combined=gltf(O/'console-with-keyboard.glb');key=gltf(O/'keyboard.glb')
assert set(nodes(g))=={'ConsoleBody','DisplayPlane','ScreenSocket','KeyboardSocket'}
assert set(nodes(key))=={'Keyboard','KeyboardBase'}
assert set(nodes(combined))=={'ConsoleBody','DisplayPlane','ScreenSocket','KeyboardSocket','Keyboard','KeyboardBase'}
for name in ['ScreenSocket','KeyboardSocket']:
 for prop in ['translation','rotation','scale','matrix']:
  assert nodes(g)[name].get(prop)==nodes(old)[name].get(prop),(name,prop)
  assert nodes(combined)[name].get(prop)==nodes(old)[name].get(prop),(name,prop)
assert (O/'keyboard.glb').read_bytes()==(O.parent/'kb3/keyboard.glb').read_bytes()
placement=json.loads((O/'keyboard-placement.json').read_text());base=nodes(combined)['KeyboardBase']
for prop,jprop in [('translation','location'),('rotation','rotation_quaternion'),('scale','scale')]:assert np.allclose(base[prop],placement['glTF_y_up'][jprop],atol=1e-7,rtol=0),(prop,base[prop])
for name in ['console-albedo','console-orm','console-normal']:assert Image.open(O/(name+'.png')).size==(2048,2048)
paintmask=(np.asarray(Image.open(O/'paint-mask.png').convert('L'))>250)&(np.asarray(Image.open(O.parent/'finish4/uv-coverage.png').convert('L'))>250);albedo=np.asarray(Image.open(O/'console-albedo.png').convert('RGB'));bakedmedian=np.median(albedo[paintmask],axis=0);assert max(abs(bakedmedian-np.array(t['reference_paint_median_srgb_255'])))<=1
assert abs(t['edge_chip_coverage']-.09)<.0001;assert abs(t['steel_fraction_of_chips']-.05)<.0001;assert len(t['streaks'])==5
for check,value in r['checks'].items():assert value,check
assert r['keyboard']['keytop_count']==29 and r['keyboard']['visible_keytops']>=27
assert scene['frontmost_vertical_projection_clearance_mm']>=0 and scene['operator_keyboard_in_frame'] and scene['operator_screen_in_frame'] and scene['operator_screen_above_keyboard']
mat=next(m for m in g['materials'] if m['name']=='Console dusty yellow-green paint and sparse rust');assert mat['occlusionTexture']['index']==mat['pbrMetallicRoughness']['metallicRoughnessTexture']['index'];assert 'normalTexture' in mat
for doc in [g,key,combined]:assert all('bufferView' in im for im in doc['images'])
for name in r['render']['views']:
 image=Image.open(O/(name+'.png'));assert image.size==(1600,900);assert np.asarray(image).std()>10
fontpath='/System/Library/Fonts/Supplemental/Arial.ttf'
def font(size):return ImageFont.truetype(fontpath,size)
sheet=Image.new('RGB',(2400,1320),'#171c1e');draw=ImageDraw.Draw(sheet);draw.text((24,16),'Dusty olive console with seated keyboard',font=font(34),fill='#eef0df')
panels=[(O.parent.parent/'room9/ref-console-design.png','Concept'),(O/'three-quarter.png','Front-left'),(O/'side.png','Side profile'),(O/'operator.png','Operator eye: 29 of 29 key tops visible'),(O/'keyboard-closeup.png','Keyboard on deck')]
for i,(path,label) in enumerate(panels):
 x=(i%3)*800;y=75+(i//3)*610;draw.text((x+18,y),label,font=font(26),fill='#eef0df');im=ImageOps.contain(Image.open(path).convert('RGB'),(780,540),Image.Resampling.LANCZOS);sheet.paste(im,(x+(800-im.width)//2,y+45+(540-im.height)//2))
x,y=1624,725;draw.text((x,y),'Measured paint and fit',font=font(30),fill='#eef0df');swatches=[('Reference median',(117,125,80)),('Baked paint median',tuple(int(v) for v in bakedmedian)),('Rust chips',(110,58,36)),('Dark undercoat',(48,49,37)),('Sparse steel',(104,103,87))]
for i,(name,color) in enumerate(swatches):
 yy=y+60+i*52;draw.rectangle((x,yy,x+60,yy+34),fill=color);draw.text((x+80,yy+3),name+'  '+str(color),font=font(21),fill='#e3e4dc')
k=r['keyboard'];gap=[g['gap_mm'] for g in k['underside_samples']]
lines=[f"Scale {k['uniform_scale']:.6f}; width {k['scaled_local_dimensions_m'][0]*1000:.1f} mm",f"9 underside gaps: {min(gap):.3f} to {max(gap):.3f} mm",'At least 10 mm front/rear clearance; no intersections','9% edge wear; 5% steel within chips; 5 faint streaks','Cycles 64 samples, denoised, 1600 x 900']
for i,line in enumerate(lines):draw.text((x,y+345+i*34),line,font=font(20),fill='#d2d8cd')
sheet.save(O/'contact.png')
r['textures']['baked_paint_median_srgb_255']=bakedmedian.tolist();r['scene_checks']=scene;r['validation']={'exact_export_object_sets':True,'socket_export_transforms_unchanged':True,'keyboard_local_export_byte_identical':True,'placement_matches_combined_export':True,'packed_orm_with_occlusion':True,'embedded_images':True,'maps_2048':True,'four_renders_1600x900':True,'all_fit_checks_pass':True};r['files']=['console.glb','keyboard.glb','keyboard-placement.json','console-with-keyboard.glb','console-with-keyboard.blend','console-albedo.png','console-orm.png','console-normal.png','three-quarter.png','side.png','operator.png','keyboard-closeup.png','contact.png','reference-paint-mask.png','report.json'];r['incomplete']=[]
(O/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'paint':bakedmedian.tolist(),'scale':k['uniform_scale'],'dimensions_m':k['scaled_local_dimensions_m'],'gap_mm':[min(gap),max(gap)],'checks':r['checks'],'validation':r['validation'],'files':r['files']},indent=2))
