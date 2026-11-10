from pathlib import Path
from PIL import Image, ImageOps, ImageFont, ImageDraw
import json,struct,numpy as np
O=Path(__file__).resolve().parent
r=json.loads((O/'report.json').read_text());data=(O/'console.glb').read_bytes();magic,version,length=struct.unpack_from('<4sII',data);assert magic==b'glTF' and version==2 and length==len(data)
jslen,jstype=struct.unpack_from('<II',data,12);g=json.loads(data[20:20+jslen]);names={n.get('name') for n in g['nodes']};assert names=={'ConsoleBody','DisplayPlane','ScreenSocket','KeyboardSocket'},names
triangles={}
for mesh in g['meshes']:
 triangles[mesh['name']]=sum(g['accessors'][p['indices']]['count']//3 for p in mesh['primitives'])
assert sum(triangles.values())<=48000,triangles
import trimesh
loaded=trimesh.load(O/'console.glb',force='scene');bodymesh=next(mesh.copy() for mesh in loaded.geometry.values() if len(mesh.faces)>100);bodymesh.merge_vertices(merge_tex=True,merge_norm=True)
assert bodymesh.is_watertight and bodymesh.is_winding_consistent and bodymesh.volume>0
r['exported_body_watertight']=bool(bodymesh.is_watertight);r['exported_body_volume_m3']=float(bodymesh.volume)
r.pop('silhouette_iou',None);r['silhouette_iou_front_raw_fitted']=r['geometry']['silhouette_iou']['front'];r['silhouette_iou_side_raw_fitted']=r['geometry']['silhouette_iou']['side']
m=next(m for m in g['materials'] if m.get('name')=='Console worn olive paint');p=m['pbrMetallicRoughness'];assert 'baseColorTexture' in p and 'metallicRoughnessTexture' in p and 'normalTexture' in m and 'occlusionTexture' in m;assert m['occlusionTexture']['index']==p['metallicRoughnessTexture']['index'];assert all('bufferView' in i for i in g['images'])
for name in ['console-albedo','console-orm','console-normal','paint-mask','uv-coverage']:
 assert Image.open(O/(name+'.png')).size==(2048,2048)
for name in ['front','three-quarter','side','deck-joint','red','clay-three-quarter','clay-side','clay-underside']:
 assert Image.open(O/(name+'.png')).size==(1600,900)
a=np.asarray(Image.open(O/'console-albedo.png').convert('RGB'));pm=np.asarray(Image.open(O/'paint-mask.png'))[:,:,0];cv=np.asarray(Image.open(O/'uv-coverage.png'))[:,:,0];ao=np.asarray(Image.open(O/'console-ao.png'))[:,:,0];mask=(pm/255>.95)&(cv/255>.99)&(ao/255>.90);assert mask.sum()>10000
median=np.median(a[mask],axis=0);assert np.max(np.abs(median-[74,80,50]))<=3,median
orm=np.asarray(Image.open(O/'console-orm.png').convert('RGB'));covered=cv>250;steel=covered&(orm[:,:,2]>=245);assert steel.sum()>100
r['paint_albedo_median_srgb_255']=median.tolist();r['paint_texels_measured']=int(mask.sum());r['exposed_steel_texels']=int(steel.sum());r['paint_albedo_p10_p90_srgb_255']=np.percentile(a[mask],[10,90],axis=0).tolist()
r['validation']={'glb_bytes':len(data),'embedded_images':len(g['images']),'embedded_materials':len(g['materials']),'objects_exact':True,'triangles_by_mesh':triangles,'triangles_exported_total':sum(triangles.values()),'orm_shared_occlusion_and_metallic_roughness':True,'maps_2048':True,'renders_1600x900':True,'cycles_samples':64,'denoised':True,'uv_unwrap':{'method':'Smart UV Project','angle_degrees':66,'margin':.02},'hunyuan_paint':{'reference':'inputs/console-s510-rgba.png','texture_size':2048,'delight':True,'atlas_transfer':'Generated paint transferred onto the retained Smart UV atlas with selected-to-active emission baking.'}}
assert r['geometry']['final_geometry']['boundary_edges']==0 and r['geometry']['final_geometry']['nonmanifold_edges']==0
assert min(r['geometry']['silhouette_iou'].values())>=.97
assert len(r['screen_raycast_samples'])==25
assert r['keyboard_deck']['flatness_peak_to_peak_m']<.002
assert len(r['rust_patches'])==7
fontfile='/System/Library/Fonts/Supplemental/Arial.ttf'
def font(n):return ImageFont.truetype(fontfile,n)
contact=Image.new('RGB',(2400,1740),'#141b21');draw=ImageDraw.Draw(contact);draw.text((22,16),'Rebuilt console: solid shell, dark olive paint, baked wear',font=font(30),fill='#e7ebde')
panels=[(O.parent.parent/'room9/ref-console-design.png','Concept'),(O/'front.png','Front'),(O/'three-quarter.png','Three-quarter front-left'),(O/'side.png','Side'),(O/'deck-joint.png','Rebuilt deck joint'),(O/'red.png','Dim red'),(O/'clay-three-quarter.png','Clay before texturing'),(O/'clay-side.png','Clay side'),(O/'clay-underside.png','Clay underside of joint')]
for i,(path,label) in enumerate(panels):
 x=(i%3)*800;y=(i//3)*560+60;draw.text((x+18,y+5),label,font=font(25),fill='#e7ebde');im=ImageOps.contain(Image.open(path).convert('RGB'),(780,490),Image.Resampling.LANCZOS);contact.paste(im,(x+(800-im.width)//2,y+45+(490-im.height)//2))
contact.save(O/'contact.png')
r['files']=['console.glb','console.blend','console-albedo.png','console-orm.png','console-normal.png','front.png','three-quarter.png','side.png','deck-joint.png','red.png','clay-three-quarter.png','clay-side.png','clay-underside.png','contact.png','geometry-report.json','deck-report.json','report.json'];r['incomplete']=[]
(O/'report.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({'geometry':r['geometry'],'median_srgb':median.tolist(),'paint_texels':int(mask.sum()),'exposed_steel_texels':int(steel.sum()),'keyboard_deck':r['keyboard_deck'],'screen':r['screen_rectangle_m'],'validation':r['validation']},indent=2))
