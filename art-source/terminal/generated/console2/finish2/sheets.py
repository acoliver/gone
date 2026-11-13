from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
import json,struct,numpy as np
O=Path(__file__).resolve().parent;ROOT=O.parent
r=json.loads((O/'report.json').read_text());s=json.loads((O/'screen-segmentation.json').read_text())
def font(size):return ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',size)
def label(im,xy,text,size=24,fill='#e7ebde'):ImageDraw.Draw(im).text(xy,text,font=font(size),fill=fill)
# Photo outline is the world-fitted rectangle after the 8 mm inset.
photo=Image.open(ROOT/'outputs/console-s510.png').convert('RGB');d=ImageDraw.Draw(photo);x0,y0,x1,y1=s['screen_photo_pixels'];rect=r['screen_rectangle_m'];dx=.008/(rect['width']+.016)*(x1-x0);dy=.008/(rect['height']+.016)*(y1-y0);d.rectangle((x0+dx,y0+dy,x1-dx,y1-dy),outline='#40ff8c',width=4)
front=Image.open(O/'front.png').convert('RGB');d=ImageDraw.Draw(front);corners=[tuple(p) for p in r['front_render_screen_corners_px']];d.line(corners+[corners[0]],fill='#40ff8c',width=4)
fit=Image.new('RGB',(1600,1144),'#192028');fit.paste(photo,(16,70));crop=front.crop((350,0,1250,900));crop=ImageOps.contain(crop,(780,1024),Image.Resampling.LANCZOS);fit.paste(crop,(800+(780-crop.width)//2,70+(1024-crop.height)//2));label(fit,(20,18),'Photo: silhouette alignment and 8 mm inset',24);label(fit,(815,18),'Front render: fitted DisplayPlane outline',24);label(fit,(20,1100),f'Silhouette IoU {s["silhouette_iou"]:.4f}   |   Screen {rect["width"]:.4f} x {rect["height"]:.4f} m   |   y {rect["y"]:.4f} m',23);fit.save(O/'screen-fit.png')
# Identical camera and lighting for the two joint renders.
comparison=Image.new('RGB',(2400,740),'#192028')
for i,name in enumerate(['deck-joint-before','deck-joint']):
 tile=Image.open(O/(name+'.png')).convert('RGB').resize((1200,675),Image.Resampling.LANCZOS);comparison.paste(tile,(i*1200,60));label(comparison,(i*1200+20,15),'Hunyuan paint before repair' if i==0 else 'Baked worn paint after joint repair',28)
comparison.save(O/'deck-joint-before-after.png')
# Material swatches retain the supplied paint grain, actual baked convex mask and self-AO.
maps=Image.new('RGB',(1200,750),'#192028')
for i,(file,title) in enumerate([('console-albedo.png','ALBEDO'),('console-orm.png','ORM: AO / roughness / metal'),('console-normal.png','TANGENT NORMAL'),('convex-edge-mask.png','CONVEX EDGE MASK'),('console-ao.png','CYCLES AO, 16 SAMPLES'),('wear-detail.png','PERIODIC BOX DETAIL')]):
 x=(i%3)*400;y=(i//3)*375;im=Image.open(O/file).convert('RGB');im=ImageOps.contain(im,(380,335),Image.Resampling.LANCZOS);maps.paste(im,(x+(400-im.width)//2,y+35));label(maps,(x+12,y+8),title,17)
maps.save(O/'maps.png')
contact=Image.new('RGB',(2400,1740),'#141b21')
panels=[('art-source/terminal/generated/room9/ref-console-design.png','Concept reference'),(str(O/'front.png'),'Front'),(str(O/'three-quarter.png'),'Three-quarter front-left'),(str(O/'side.png'),'Side'),(str(O/'deck-joint-before.png'),'Joint before repair'),(str(O/'deck-joint.png'),'Joint after repair'),(str(O/'red.png'),'Dim red light'),(str(O/'screen-fit.png'),'Screen fit and silhouette check'),(str(O/'maps.png'),'Baked material maps')]
for i,(file,title) in enumerate(panels):
 x=i%3*800;y=i//3*560+55;label(contact,(x+18,y+8),title,25);im=Image.open(file).convert('RGB');im=ImageOps.contain(im,(780,495),Image.Resampling.LANCZOS);contact.paste(im,(x+(800-im.width)//2,y+45+(495-im.height)//2))
label(contact,(18,14),'Console finish: photo-fitted glass, worn olive paint, baked 2048 maps',30);contact.save(O/'contact.png')
# Validate the exported GLB, including actual embedded texture and material bindings.
data=(O/'console.glb').read_bytes();magic,version,length=struct.unpack_from('<4sII',data);assert magic==b'glTF' and version==2 and length==len(data);jslen,jstype=struct.unpack_from('<II',data,12);g=json.loads(data[20:20+jslen]);names={n.get('name') for n in g['nodes']};assert names=={'ConsoleBody','DisplayPlane','ScreenSocket','KeyboardSocket'},names
bodymat=next(m for m in g['materials'] if m.get('name')=='Console worn olive paint');pbr=bodymat['pbrMetallicRoughness'];assert 'baseColorTexture' in pbr and 'metallicRoughnessTexture' in pbr;assert 'normalTexture' in bodymat and 'occlusionTexture' in bodymat;assert bodymat['occlusionTexture']['index']==pbr['metallicRoughnessTexture']['index'];assert all('bufferView' in im for im in g['images'])
for name in ['console-albedo','console-orm','console-normal','console-ao','convex-edge-mask']:
 assert Image.open(O/(name+'.png')).size==(2048,2048)
for name in ['front','three-quarter','side','deck-joint','red','deck-joint-before']:
 assert Image.open(O/(name+'.png')).size==(1600,900)
orm=np.array(Image.open(O/'console-orm.png').convert('RGB'));normal=np.array(Image.open(O/'console-normal.png').convert('RGB'));coverage=np.array(Image.open(O/'console-ao.png').convert('RGB'))[:,:,0]>2
assert int(orm[:,:,2][coverage].max())>=245, 'Strongest edge chips do not reach exposed-metal values'
r['exposed_steel_texels']=int(np.count_nonzero(coverage&(orm[:,:,2]>=245)))
r['validation']={'glb_bytes':len(data),'embedded_images':len(g['images']),'embedded_materials':len(g['materials']),'objects_exact':True,'orm_occlusion_and_metallic_roughness_share_texture':True,'orm_rgb_range':[ [int(orm[:,:,c][coverage].min()),int(orm[:,:,c][coverage].max())] for c in range(3)],'tangent_normal_rgb_range':[[int(normal[:,:,c].min()),int(normal[:,:,c].max())] for c in range(3)],'all_requested_renders_1600x900':True,'all_requested_maps_2048':True}
r['cleanup']=json.loads((O/'cleanup.json').read_text());r['silhouette_correction']=json.loads((O/'profile-correction.json').read_text());r['files']=['console.glb','console.blend','console-albedo.png','console-orm.png','console-normal.png','console-ao.png','convex-edge-mask.png','screen-fit.png','front.png','three-quarter.png','side.png','deck-joint.png','red.png','deck-joint-before.png','deck-joint-before-after.png','contact.png'];r['remaining_geometry_note']='Generated geometry retains irregular side surfaces and a recessed deck joint. Albedo repair does not rebuild those surfaces.'
(O/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r['validation'],indent=2))
