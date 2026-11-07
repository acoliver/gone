import argparse, math, sys
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[4]
SOURCE=Path(__file__).resolve().parent/'sofa-working.blend'
OUT=ROOT/'assets/props/quarters/sofa.glb'

def mat(n,c,metal=0,rough=.7):
 m=bpy.data.materials.new(n); m.diffuse_color=(*c,1); m.use_nodes=True; p=next(x for x in m.node_tree.nodes if x.type=='BSDF_PRINCIPLED'); p.inputs['Base Color'].default_value=(*c,1); p.inputs['Metallic'].default_value=metal; p.inputs['Roughness'].default_value=rough; return m

def cube(name,dims,loc,material,bev=0):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc); o=bpy.context.object; o.name=name; o.dimensions=dims; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); o.data.materials.append(material)
 if bev:
  b=o.modifiers.new('Rounded upholstery and manufactured edges','BEVEL'); b.width=min(bev,min(dims)*.45); b.segments=4; bpy.context.view_layer.objects.active=o; bpy.ops.object.modifier_apply(modifier=b.name)
 for p in o.data.polygons:p.use_smooth=True
 return o

def join(name,objs):
 bpy.ops.object.select_all(action='DESELECT')
 for o in objs:o.select_set(True)
 bpy.context.view_layer.objects.active=objs[0]; bpy.ops.object.join(); o=bpy.context.object; o.name=name; return o

def uv(o):
 bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active=o; bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.uv.smart_project(island_margin=.02); bpy.ops.object.mode_set(mode='OBJECT')

def sphere(name,loc,scale,material):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=8,radius=1,location=loc); o=bpy.context.object; o.name=name; o.scale=scale; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); o.data.materials.append(material); return o

def cushion(name,center,dims,material,piping,seat):
 x,y,z=center; dx,dy,dz=dims; body=cube(name,(dx,dy,dz-.02),(x,y,z-.01),material,.03)
 # The rounded crown rises 20 mm within the cushion's stated overall height.
 bpy.ops.mesh.primitive_uv_sphere_add(segments=10,ring_count=6,radius=1,location=(x,y,z+dz/2-.02)); crown=bpy.context.object; crown.name=name+' crown'; crown.scale=(dx/2-.025,dy/2-.025,.02); bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); crown.data.materials.append(material)
 if seat:
  coords=[(x-dx*.44,y-dy*.44,z+dz*.44),(x+dx*.44,y-dy*.44,z+dz*.44),(x+dx*.44,y+dy*.44,z+dz*.44),(x-dx*.44,y+dy*.44,z+dz*.44)]
 else:
  coords=[(x-dx*.44,y-dy*.44,z+dz*.44),(x+dx*.44,y-dy*.44,z+dz*.44),(x+dx*.44,y+dy*.44,z+dz*.44),(x-dx*.44,y+dy*.44,z+dz*.44)]
 cu=bpy.data.curves.new(name+' welt','CURVE'); cu.dimensions='3D'; cu.resolution_u=1; cu.bevel_depth=.004; cu.bevel_resolution=3; sp=cu.splines.new('POLY'); sp.points.add(3)
 for p,c in zip(sp.points,coords):p.co=(*c,1)
 sp.use_cyclic_u=True; w=bpy.data.objects.new(name+' welt',cu); bpy.context.collection.objects.link(w); w.data.materials.append(material); bpy.ops.object.select_all(action='DESELECT'); w.select_set(True); bpy.context.view_layer.objects.active=w; bpy.ops.object.convert(target='MESH'); w=bpy.context.object
 out=join(name,[body,crown,w]); uv(out); return out

def throw_mesh(material):
 nu,nv=24,16; verts=[]; faces=[]; layer_n=(nu+1)*(nv+1); y0=-.18
 # Image-right arm: sheet rests over the rounded cap and hangs down the outer side.
 for layer in (0,1):
  for j in range(nv+1):
   v=j/nv
   for i in range(nu+1):
    u=i/nu; y=y0+u*.42
    if v<.32: x=.94+.145*(v/.32); z=.785
    else: x=1.085+.010*((v-.32)/.68); z=.785-.45*((v-.32)/.68)
    z+=.004*math.sin(u*math.pi*4+v*4)+.002*math.sin(u*math.pi*9-v*5)
    verts.append((x+(layer*.007 if v>=.32 else 0),y,z-(layer*.007 if v<.32 else 0)))
 for layer in range(2):
  off=layer*layer_n
  for j in range(nv):
   for i in range(nu):
    a=off+j*(nu+1)+i; faces.append((a,a+1,a+nu+2,a+nu+1))
 for j in range(nv):
  for i in (0,nu):
   a=j*(nu+1)+i; b=(j+1)*(nu+1)+i; faces.append((a,b,layer_n+b,layer_n+a))
 for i in range(nu):
  for j in (0,nv):
   a=j*(nu+1)+i; b=a+1; faces.append((a,layer_n+a,layer_n+b,b))
 me=bpy.data.meshes.new('Wool throw shell'); me.from_pydata(verts,[],faces); me.materials.append(material); o=bpy.data.objects.new('Throw',me); bpy.context.collection.objects.link(o)
 bpy.context.view_layer.objects.active=o; o.select_set(True); bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.normals_make_consistent(inside=False); bpy.ops.object.mode_set(mode='OBJECT'); uv(o); return o

def create():
 bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
 steel=mat('PaintedSteel',(.27,.36,.33),.62,.48); bare=mat('BareSteel',(.55,.58,.55),.72,.32); uphol=mat('CharcoalUpholstery',(.105,.115,.12),0,.88); welt=mat('UpholsteryWelt',(.20,.21,.20),0,.8); wool=mat('OatmealWool',(.57,.48,.35),0,.95)
 frame=[]
 # Side cheeks and rounded caps follow the broad framed-arm silhouette in the hero.
 for x in (-1.015,1.015):
  frame.append(cube('Arm side',(.15,.95,.62),(x,0,.43),steel,.045))
  frame.append(cube('Arm cap',( .16,.95,.085),(x,0,.765),steel,.04))
 # Rear and front rails support the cushions while leaving the upholstered parts distinct.
 frame += [cube('Back top rail',(2.0,.06,.05),(0,.405,.825),steel,.012),cube('Back lower rail',(2.0,.06,.05),(0,.405,.435),steel,.01),cube('Front seat rail',(1.90,.07,.05),(0,-.405,.38),steel,.012),cube('Seat support',(1.9,.035,.05),(0,0,.35),steel,.008)]
 for x in (-.97,.97):frame.append(cube('Back upright',(.045,.05,.42),(x,.395,.62),steel,.008))
 # Plates and fasteners are embedded into the outer arm face, within 0.5 mm.
 plates=[]; rivets=[]
 for x in (-1.094,1.094):
  for y in (-.34,.34):
   plates.append(cube('Corner plate',(.008,.16,.10),(x,y,.42),steel,.012))
   for yy in (y-.055,y+.055):
    for zz in (.385,.455):rivets.append(sphere('Rivet',(x,yy,zz),(.006,.009,.009),steel))
 feet=[]
 for x in (-.94,.94):
  for y in (-.34,.34):feet.append(cube('Foot',(.07,.08,.075),(x,y,.0375),steel,.012))
 join('Frame',frame); join('Feet',feet); join('Rivets',rivets); join('CornerPlates',plates)
 # All required hardware is part of the named frame node.
 ob=bpy.data.objects['CornerPlates']; frame_obj=bpy.data.objects['Frame']; bpy.ops.object.select_all(action='DESELECT'); frame_obj.select_set(True); ob.select_set(True); bpy.context.view_layer.objects.active=frame_obj; bpy.ops.object.join(); frame_obj.name='Frame'
 centers=(-.67,0,.67)
 for tag,x in zip('LCR',centers):cushion('SeatCushion_'+tag,(x,-.035,.465),(.66,.70,.15),uphol,welt,True)
 for tag,x in zip('LCR',centers):cushion('BackCushion_'+tag,(x,.285,.625),(.66,.20,.42),uphol,welt,False)
 throw_mesh(wool)
 bpy.context.view_layer.update()

def export(path):
 bpy.ops.object.select_all(action='DESELECT')
 for o in bpy.data.objects:
  if o.type=='MESH':o.select_set(True)
 bpy.context.view_layer.objects.active=bpy.data.objects['Frame']; bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_yup=True,export_apply=False,export_materials='EXPORT',export_cameras=False,export_lights=False)

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--output',type=Path,default=OUT); ap.add_argument('--save-source',action='store_true'); ap.add_argument('--render-dir',type=Path); a=ap.parse_args(sys.argv[sys.argv.index('--')+1:]); out=a.output if a.output.is_absolute() else ROOT/a.output; out.parent.mkdir(parents=True,exist_ok=True)
 if a.save_source or not SOURCE.exists():
  create()
  if a.save_source:bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE))
 else:
  bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
 export(str(out.resolve()))
 if a.render_dir:
  import runpy; ns=runpy.run_path(str(Path(__file__).with_name('render.py'))); ns['render'](a.render_dir if a.render_dir.is_absolute() else ROOT/a.render_dir)
if __name__=='__main__':main()
