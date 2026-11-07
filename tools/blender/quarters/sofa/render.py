import math
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[4]

def aim(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat('-Z','Y').to_euler()
def compose(paths,out,cols):
 imgs=[]
 for path in paths:
  im=bpy.data.images.load(str(path),check_existing=False); im.scale(512,512); imgs.append(list(im.pixels[:]))
 rows=(len(paths)+cols-1)//cols; sheet=bpy.data.images.new(out.stem,width=cols*512,height=rows*512,alpha=True)
 data=[0.0]*(cols*512*rows*512*4)
 for k,pix in enumerate(imgs):
  ox=(k%cols)*512; oy=(rows-1-k//cols)*512
  for y in range(512):
   dst=((oy+y)*cols*512+ox)*4; src=y*512*4; data[dst:dst+512*4]=pix[src:src+512*4]
 sheet.pixels[:]=data; sheet.filepath_raw=str(out); sheet.file_format='PNG'; sheet.save()
def render(out):
 out=Path(out); out.mkdir(parents=True,exist_ok=True); bpy.ops.wm.open_mainfile(filepath=str(Path(__file__).with_name('sofa-working.blend')))
 scene=bpy.context.scene; scene.render.engine='BLENDER_EEVEE_NEXT'; scene.render.image_settings.file_format='PNG'; scene.render.image_settings.color_mode='RGBA'; scene.render.film_transparent=False; scene.render.resolution_percentage=100; scene.render.resolution_x=900; scene.render.resolution_y=700; scene.view_settings.view_transform='Standard'; scene.view_settings.look='Medium High Contrast'; scene.world.color=(.72,.72,.72)
 for name,loc,power,size in [('Key',(-3,-4,4),850,3.5),('Fill',(3,-2,2),600,3),('Rim',(1,3,3),700,2.5)]:
  d=bpy.data.lights.new(name,'AREA'); o=bpy.data.objects.new(name,d); scene.collection.objects.link(o); o.location=loc; d.energy=power; d.shape='DISK'; d.size=size; aim(o,(0,0,.43))
 d=bpy.data.cameras.new('StudioCamera'); cam=bpy.data.objects.new('StudioCamera',d); scene.collection.objects.link(cam); d.type='ORTHO'; scene.camera=cam
 def shot(name,loc,target,scale=3.05,res=(900,700)):
  cam.location=loc; aim(cam,target); d.ortho_scale=scale; scene.render.resolution_x,scene.render.resolution_y=res; scene.render.filepath=str(out/name); bpy.ops.render.render(write_still=True)
 hero=out/'fit-hero.png'; shot(hero.name,(3.1,-3.5,2.2),(0,0,.43),3.15)
 design=ROOT/'docs/art/quarters/sheets/sofa/hero.png'; compose([design,hero],out/'compare-hero.png',2)
 for ang in (30,120,210,300):
  r=math.radians(ang); shot(f'turn-{ang}.png',(3.2*math.sin(r),-3.2*math.cos(r),1.65),(0,0,.42),3.1,(512,512))
 compose([out/f'turn-{a}.png' for a in (30,120,210,300)],out/'turntable.png',2)
 detail=out/'fit-detail.png'; shot(detail.name,(2.25,-2.5,1.15),(1.02,-.02,.48),.90,(700,700)); compose([detail],out/'compare-detail.png',1)
if __name__=='__main__':render(ROOT/'tmp/fit/sofa/pass2')
