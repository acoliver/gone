from pathlib import Path
from PIL import Image,ImageOps,ImageFont,ImageDraw
import numpy as np,json,struct,trimesh
O=Path(__file__).resolve().parent
r=json.loads((O/'report.json').read_text());t=json.loads((O/'texture-report.json').read_text());before=json.loads((O/'diagnosis-rays.json').read_text())
def gltf(path):
 data=path.read_bytes();magic,version,length=struct.unpack_from('<4sII',data);assert magic==b'glTF' and version==2 and length==len(data)
 size,kind=struct.unpack_from('<II',data,12);return json.loads(data[20:20+size])
g=gltf(O/'console.glb');old=gltf(O.parent/'finish3/console.glb')
assert {n.get('name') for n in g['nodes']}=={'ConsoleBody','DisplayPlane','ScreenSocket','KeyboardSocket'}
for name in ['ScreenSocket','KeyboardSocket']:
 a=next(n for n in g['nodes'] if n.get('name')==name);b=next(n for n in old['nodes'] if n.get('name')==name)
 for prop in ['translation','rotation','scale','matrix']:assert a.get(prop)==b.get(prop),(name,prop,a,b)
assert r['sockets_before']==r['sockets_after']
loaded=trimesh.load(O/'console.glb',force='scene');mesh=next(m.copy() for m in loaded.geometry.values() if len(m.faces)>100);mesh.merge_vertices(merge_tex=True,merge_norm=True)
assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0
assert np.min(mesh.area_faces)>1e-12,float(np.min(mesh.area_faces))
measure=[]
for original,finished in zip(before['rays'],r['junction_after_profiles']):
 x=original['x'];a=np.array([[v[0],v[1]] for v in original['front']]);z,y=a.T;reference=y[np.argmin(abs(z-.68))]
 region=(z>=.61)&(z<=.70);depth=y-(reference+.13*(z-.68));selected=region&(depth>.001)
 b=np.array(finished['front']);post=b[:,1]-(reference+.13*(b[:,0]-.68));postregion=(b[:,0]>=.61)&(b[:,0]<=.69)
 ob=np.array(original['above_front']);ob=ob[(ob[:,3]>=.61)&(ob[:,3]<=.69)];obdepth=ob[:,2]-(reference+.13*(ob[:,3]-.68))
 newob=np.array(finished['above_front']);newob=newob[(newob[:,2]>=.61)&(newob[:,2]<=.69)];newobdepth=newob[:,1]-(reference+.13*(newob[:,2]-.68))
 measure.append({'x':x,'before_front_depth_mm':float(depth[region].max()*1000),'before_front_opening_z_mm':float((z[selected].max()-z[selected].min()+.001)*1000),'before_front_opening_z_m':[float(z[selected].min()),float(z[selected].max())],'before_above_front_depth_mm':float(max(0,obdepth.max())*1000),'after_front_residual_undercut_mm':float(max(0,post[postregion].max())*1000),'after_above_front_residual_undercut_mm':float(max(0,newobdepth.max())*1000)})
assert max(q['after_front_residual_undercut_mm'] for q in measure)<1,measure
assert max(q['after_above_front_residual_undercut_mm'] for q in measure)<1,measure
r['junction_diagnosis']={'definition':'Depth relative to the local lower head face extrapolated down at dy/dz=0.13. Opening measured where depth exceeds 1 mm, restricted to the connected deck joint below z=0.70 m. Front rays use 1 mm vertical pitch. Above-front rays point (0,1,-0.8).','samples':measure,'source_boundary_edges':before['boundary_edges'],'source_nonmanifold_edges':before['nonmanifold_edges']}
(O/'diagnosis-summary.json').write_text(json.dumps(r['junction_diagnosis'],indent=2))
for name in ['console-albedo','console-ao','console-orm','console-normal']:assert Image.open(O/(name+'.png')).size==(2048,2048)
for name in ['front','three-quarter','side','deck-joint','albedo-shelf']:assert Image.open(O/(name+'.png')).size==(1600,900)
material=next(m for m in g['materials'] if m['name']=='Console worn olive paint finish4');p=material['pbrMetallicRoughness'];assert material['occlusionTexture']['index']==p['metallicRoughnessTexture']['index'];assert 'normalTexture' in material
assert all('bufferView' in i for i in g['images'])
assert .15<t['object_space_wear']['edge_chip_coverage']<.25
assert abs(t['object_space_wear']['steel_fraction_of_chips']-.1)<.001
assert t['object_space_wear']['flat_face_chips']==0
assert t['contact_shadow']['max_combined_texture_darkening']<=.25
r['textures']=t
r['validation']={'objects_exact':True,'socket_export_transforms_exact':True,'body_watertight':bool(mesh.is_watertight),'body_winding_consistent':bool(mesh.is_winding_consistent),'body_volume_m3':float(mesh.volume),'minimum_triangle_area_m2':float(mesh.area_faces.min()),'triangles_total':sum(g['accessors'][q['indices']]['count']//3 for m in g['meshes'] for q in m['primitives']),'maps_2048':True,'render_size':[1600,900],'cycles_samples':64,'denoised':True,'embedded_images':len(g['images']),'specular_extension':material.get('extensions',{})}
fontfile='/System/Library/Fonts/Supplemental/Arial.ttf'
def font(size):return ImageFont.truetype(fontfile,size)
contact=Image.new('RGB',(2400,1220),'#141b21');draw=ImageDraw.Draw(contact);draw.text((22,15),'Console finish4: filled contact, small edge wear, consistent olive paint',font=font(30),fill='#e7ebde')
panels=[(O.parent.parent/'room9/ref-console-design.png','Concept'),(O/'front.png','Front'),(O/'three-quarter.png','Higher front-left, roof visible'),(O/'side.png','Side'),(O/'deck-joint.png','Filled deck contact'),(O/'albedo-shelf.png','Albedo only: shelf and lip')]
for i,(path,label) in enumerate(panels):
 x=(i%3)*800;y=(i//3)*570+65;draw.text((x+18,y+5),label,font=font(25),fill='#e7ebde');im=ImageOps.contain(Image.open(path).convert('RGB'),(780,490),Image.Resampling.LANCZOS);contact.paste(im,(x+(800-im.width)//2,y+45+(490-im.height)//2))
contact.save(O/'contact.png')
r['files']=['console.blend','console.glb','console-albedo.png','console-ao.png','console-orm.png','console-normal.png','front.png','three-quarter.png','side.png','deck-joint.png','albedo-shelf.png','contact.png','report.json'];r['incomplete']=[]
(O/'report.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({'junction':measure,'geometry':r['geometry_fill'],'right_smoothing':r['right_deck_smoothing'],'textures':t,'validation':r['validation']},indent=2))
