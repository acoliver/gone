import math,sys
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'tmp/fit/sofa'

def aim(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat('-Z','Y').to_euler()
def main():
 bpy.ops.wm.open_mainfile(filepath=str(Path(__file__).resolve().parent/'sofa-working.blend'))
 scene=bpy.context.scene; scene.render.engine='BLENDER_EEVEE_NEXT'; scene.render.image_settings.file_format='PNG'; scene.render.film_transparent=False; scene.render.resolution_percentage=100; scene.render.resolution_x=900; scene.render.resolution_y=700; scene.view_settings.view_transform='Standard'; scene.view_settings.look='Medium High Contrast'; scene.world.color=(.72,.72,.72); scene.render.resolution_percentage=100
 scene.render.image_settings.color_mode='RGBA'; scene.render.filepath=str(OUT/'render.png'); OUT.mkdir(parents=True,exist_ok=True)
 for name,loc,power,size in [('Key',(-3,4,4),700,3.5),('Fill',(3,2,2),450,3),('Rim',(1,3,-3),600,2.5)]:
  d=bpy.data.lights.new(name,'AREA'); o=bpy.data.objects.new(name,d); scene.collection.objects.link(o); o.location=loc; d.energy=power; d.shape='DISK'; d.size=size; aim(o,(0,.42,0))
 d=bpy.data.cameras.new('StudioCamera'); cam=bpy.data.objects.new('StudioCamera',d); scene.collection.objects.link(cam); d.type='ORTHO'; d.ortho_scale=3.05; scene.camera=cam
 def shot(name,loc,target,scale=None,res=(900,700)):
  cam.location=loc; aim(cam,target); d.ortho_scale=scale or 3.05; scene.render.resolution_x,scene.render.resolution_y=res; scene.render.filepath=str(OUT/name); bpy.ops.render.render(write_still=True)
 shot('hero.png',(-3.1,2.15,3.2),(0,.43,0),3.0)
 for ang in (30,120,210,300):
  r=math.radians(ang); shot(f'turn-{ang}.png',(3.2*math.sin(r),1.65,3.2*math.cos(r)),(0,.42,0),3.05,(600,600))
 shot('detail.png',(2.35,1.15,2.0),(.93,.62,.31),.90,(700,700))
if __name__=='__main__':main()
