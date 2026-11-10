from pathlib import Path
import json,struct,numpy as np,trimesh
from scipy.ndimage import map_coordinates
from PIL import Image,ImageDraw,ImageFont,ImageOps
O=Path(__file__).resolve().parent;r=json.loads((O/'report.json').read_text())
def gltf(path):
 data=path.read_bytes();magic,version,length=struct.unpack_from('<4sII',data);assert magic==b'glTF' and version==2 and length==len(data);n,kind=struct.unpack_from('<II',data,12);return json.loads(data[20:20+n])
def nodes(doc):return {n['name']:n for n in doc['nodes']}
g=gltf(O/'console.glb');k=gltf(O/'keyboard.glb');c=gltf(O/'console-with-keyboard.glb');assert set(nodes(g))=={'ConsoleBody','DisplayPlane','ScreenSocket','KeyboardSocket'};assert set(nodes(k))=={'Keyboard','KeyboardBase'};assert set(nodes(c))==set(nodes(g))|set(nodes(k));assert (O/'keyboard.glb').read_bytes()==(O.parent/'assembly3/keyboard.glb').read_bytes()
p=json.loads((O/'keyboard-placement.json').read_text());base=nodes(c)['KeyboardBase']
for prop,key in [('translation','location'),('rotation','rotation_quaternion'),('scale','scale')]:assert np.allclose(base[prop],p['glTF_y_up'][key],atol=1e-7,rtol=0)
for name in ['console-albedo','console-ao','console-orm','console-normal']:assert Image.open(O/(name+'.png')).size==(2048,2048)
paintmask=(np.asarray(Image.open(O/'paint-mask.png').convert('L'))>250)&(np.asarray(Image.open(O/'uv-coverage.png').convert('L'))>250);albedo=np.asarray(Image.open(O/'console-albedo.png').convert('RGB'));median=np.median(albedo[paintmask],axis=0);assert max(abs(median-[117,125,80]))<=6
textures=r['textures'];assert abs(textures['edge_chip_coverage']-.09)<.001
for name,want in [('undercoat',.70),('rust',.25),('steel',.05)]:assert abs(textures[name+'_fraction_of_chips']-want)<.001
assert textures['dust']['maximum_blend']<=.15;assert textures['streak_affected_texels']>0
assert all(r['checks'].values());assert r['standing']['deck_new_z_m']==1.0
loaded=trimesh.load(O/'console.glb',force='scene');mesh=next(m.copy() for m in loaded.geometry.values() if len(m.faces)>100);mesh.merge_vertices(merge_tex=True,merge_norm=True);assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0
for doc in [g,k,c]:assert all('bufferView' in im for im in doc['images'])
mat=next(m for m in g['materials'] if 'occlusionTexture' in m);assert mat['occlusionTexture']['index']==mat['pbrMetallicRoughness']['metallicRoughnessTexture']['index'];assert 'normalTexture' in mat
for name in r['render']['views']+['albedo-z-cut']:
 im=Image.open(O/(name+'.png'));assert im.size==(1600,900);assert np.asarray(im).std()>10
# Compare both UV sides at identical positions along the shared cut ring.
z=np.load(O/'seam-samples.npz');uv=z['uvs'];xy=np.stack((2047.5-uv[:,:,1]*2048,uv[:,:,0]*2048-.5));colors=np.stack([map_coordinates(albedo[:,:,i].astype(float),xy,order=1,mode='nearest') for i in range(3)],axis=-1);diff=np.abs(colors[:,0]-colors[:,1]);seam={'sample_count':len(diff),'median_channel_difference_srgb_255':np.median(diff,axis=0).tolist(),'p95_max_channel_difference_srgb_255':float(np.percentile(diff.max(1),95)),'max_channel_difference_srgb_255':float(diff.max()),'closeup':'albedo-z-cut.png'}
r['textures']['baked_paint_median_srgb_255']=median.tolist();r['seam']=seam;r['validation']={'exact_export_node_sets':True,'keyboard_local_glb_byte_identical':True,'placement_matches_combined_glb':True,'embedded_images':True,'packed_orm_and_normal_map':True,'body_watertight':True,'body_winding_consistent':True,'body_volume_m3':float(mesh.volume),'all_maps_2048':True,'five_renders_1600x900':True}
fontpath='/System/Library/Fonts/Supplemental/Arial.ttf'
def font(size):return ImageFont.truetype(fontpath,size)
sheet=Image.new('RGB',(2400,1570),'#171c1e');draw=ImageDraw.Draw(sheet);draw.text((24,14),'Standing console: 1.00 m deck, stretched lower housing',font=font(34),fill='#eef0df')
panels=[(O.parents[1]/'room9/ref-console-design.png','Console concept'),(O.parents[1]/'for-andrew-v8/03-west.png','Approved room'),(O/'front.png','Front'),(O/'three-quarter.png','Front-left, camera height 1.65 m'),(O/'side.png','Side'),(O/'operator.png','Operator, eye 1.65 m'),(O/'albedo-z-cut.png','Albedo only, across stretch boundary')]
for i,(path,label) in enumerate(panels):
 x=(i%3)*800;y=70+(i//3)*490;draw.text((x+18,y),label,font=font(24),fill='#eef0df');im=ImageOps.contain(Image.open(path).convert('RGB'),(780,435),Image.Resampling.LANCZOS);sheet.paste(im,(x+(800-im.width)//2,y+38+(435-im.height)//2))
s=r['standing'];k=r['keyboard'];gaps=[g['gap_mm'] for g in k['support_samples']];x,y=825,1100
lines=[f"Deck centre: {s['deck_new_z_m']:.6f} m",f"Lip underside: {s['lip_underside_lowest_m'][2]:.6f} m",f"Cut: {s['z_cut_m']:.6f} m; lift: {s['delta_m']:.6f} m",f"Lower vertical scale: {s['lower_body_vertical_scale']:.6f}",f"Height: {s['height_m']:.6f} m; screen: {s['screen_centre_m'][2]:.6f} m",f"9 support gaps: {min(gaps):.3f} to {max(gaps):.3f} mm",f"{k['visible_keytops']} of 29 key tops visible; DisplayPlane hit first",'No intersection or overhang; keyboard local unchanged',f"Paint median: {tuple(int(i) for i in median)}",'Cycles 64 samples, denoised, 1600 x 900']
for i,line in enumerate(lines):draw.text((x,y+i*33),line,font=font(22),fill='#d2d8cd')
sheet.save(O/'contact.png');(O/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'standing':r['standing'],'keyboard':{n:v for n,v in k.items() if n not in ['keytops','support_samples']},'paint':median.tolist(),'seam':seam,'validation':r['validation']},indent=2));print('VALIDATE_DONE')
