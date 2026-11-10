import bpy,numpy as np,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O/'source.blend')); b=bpy.data.objects['ConsoleBody']
def mask(name):
 im=bpy.data.images.load(str(O/name),check_existing=False); w,h=im.size; p=np.array(im.pixels[:]).reshape(h,w,4)[::-1];return p[:,:,3]>.5 if name.startswith('mesh') else p[:,:,0]>.5
src=mask('mesh-silhouette.png'); dst=mask('photo-silhouette.png'); pr=json.loads((O/'projection.json').read_text()); sg=json.loads((O/'screen-segmentation.json').read_text());px,py,pw,ph=sg['photo_bbox'];mx,my,mw,mh=sg['mesh_bbox']; meter=pr['ortho_height']/pr['height']
def rowbounds(m):
 valid=np.flatnonzero(m.any(1));left=np.array([np.flatnonzero(m[y])[0] for y in valid]);right=np.array([np.flatnonzero(m[y])[-1] for y in valid]);return valid,left,right
sr,sl,sright=rowbounds(src);tr,tl,tright=rowbounds(dst)
max_delta=0
for v in b.data.vertices:
 row=pr['height']/2-(v.co.z-pr['centre_z'])/meter
 l=pr['centre_x']+(np.interp(row,sr,sl)-pr['width']/2)*meter; r=pr['centre_x']+(np.interp(row,sr,sright)-pr['width']/2)*meter
 ty=py+(row-my)/(mh-1)*(ph-1); target_l=-.55+(np.interp(ty,tr,tl)-px)/(pw-1)*1.1; target_r=-.55+(np.interp(ty,tr,tright)-px)/(pw-1)*1.1
 t=np.clip((v.co.x-l)/(r-l),0,1); new=target_l+t*(target_r-target_l); max_delta=max(max_delta,abs(new-v.co.x)); v.co.x=float(new)
b.data.update(); (O/'profile-correction.json').write_text(json.dumps({'method':'Horizontal cross-section remap to segmented source-photo silhouette. Existing vertex UVs, z and y preserved.','maximum_x_displacement_m':max_delta},indent=2)); bpy.ops.wm.save_as_mainfile(filepath=str(O/'source.blend'))
s=(O/'prepare.py').read_text();exec(s[s.index('verts=np.array'):],{'bpy':bpy,'np':np,'json':json,'OUT':O,'ROOT':O.parent,'body':b,'scene':bpy.context.scene,'Vector':Vector})
