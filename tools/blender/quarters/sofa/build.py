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
 bpy.ops.mesh.primitive_cube_add(size=1, location=loc); o=bpy.context.object; o.name=name; o.dimensions=dims; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); o.data.materials.append(material)
 if bev:
  b=o.modifiers.new('Soft manufactured edges','BEVEL'); b.width=min(bev,min(dims)*.45); b.segments=3; bpy.context.view_layer.objects.active=o; bpy.ops.object.modifier_apply(modifier=b.name)
 return o

def join(name,objs):
 bpy.ops.object.select_all(action='DESELECT')
 for o in objs:o.select_set(True)
 bpy.context.view_layer.objects.active=objs[0]; bpy.ops.object.join(); o=bpy.context.object; o.name=name; return o

def uv(o):
 bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active=o; bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.uv.smart_project(island_margin=.02); bpy.ops.object.mode_set(mode='OBJECT')

def sphere(name,loc,scale,material):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=8,radius=1,location=loc); o=bpy.context.object; o.name=name; o.scale=scale; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); o.data.materials.append(material); return o

def cushion(name,loc,dims,up_axis,upholstery,piping):
 o=cube(name,dims,loc,upholstery,min(dims)*.20)
 # Light crown from subdivision of a sparse rounded box, retained within the requested envelope.
 s=o.modifiers.new('Cushion crown','SUBSURF'); s.levels=1; bpy.context.view_layer.objects.active=o; bpy.ops.object.modifier_apply(modifier=s.name)
 # Fine piping loop on the outward face, as a closed tube joined into this named mesh.
 x,y,z=loc; dx,dy,dz=dims
 if up_axis=='seat':
  # outline in X/Z on front face
  coords=[(x-dx*.39,y+dy*.28,z+dz*.495),(x+dx*.39,y+dy*.28,z+dz*.495),(x+dx*.39,y+dy*.28,z-dz*.495),(x-dx*.39,y+dy*.28,z-dz*.495)]
 else:
  coords=[(x-dx*.39,y-dy*.39,z+dz*.495),(x+dx*.39,y-dy*.39,z+dz*.495),(x+dx*.39,y+dy*.39,z+dz*.495),(x-dx*.39,y+dy*.39,z+dz*.495)]
 cu=bpy.data.curves.new(name+' welt','CURVE'); cu.dimensions='3D'; cu.resolution_u=1; cu.bevel_depth=.003; cu.bevel_resolution=2; sp=cu.splines.new('POLY'); sp.points.add(3)
 for p,c in zip(sp.points,coords):p.co=(*c,1)
 sp.use_cyclic_u=True; w=bpy.data.objects.new(name+' piping',cu); bpy.context.collection.objects.link(w); w.data.materials.append(piping); bpy.context.view_layer.objects.active=w; w.select_set(True); bpy.ops.object.convert(target='MESH'); w=bpy.context.object
 o=join(name,[o,w]); uv(o); return o

def throw_mesh(material):
 # The folded sheet crosses the arm top, turns over its outside edge, and hangs along the arm.
 nu,nv=20,16; verts=[]; faces=[]; row=nu+1; layer_n=(nu+1)*(nv+1)
 for layer in (0,1):
  for j in range(nv+1):
   v=j/nv
   for i in range(nu+1):
    u=i/nu; z=.33-.66*u
    if v<.35: x=1.008+.032*(v/.35); y=.649
    else: x=1.040+.107*((v-.35)/.65); y=.649-.49*((v-.35)/.65)
    fold=.00025*math.sin(u*math.pi*6)+.0002*math.sin(u*math.pi*10+v*5)
    verts.append((x+(layer*.007 if v>=.35 else 0),y+fold-(layer*.007 if v<.35 else 0),z))
 for layer in range(2):
  off=layer*layer_n
  for j in range(nv):
   for i in range(nu):
    a=off+j*row+i; faces.append((a,a+1,a+row+1,a+row))
 for j in range(nv):
  for i in (0,nu):
   a=j*row+i; b=(j+1)*row+i; faces.append((a,b,layer_n+b,layer_n+a))
 for i in range(nu):
  for j in (0,nv):
   a=j*row+i; b=a+1; faces.append((a,layer_n+a,layer_n+b,b))
 me=bpy.data.meshes.new('Wool throw folded shell'); me.from_pydata(verts,[],faces); me.materials.append(material); ob=bpy.data.objects.new('Throw',me); bpy.context.collection.objects.link(ob)
 bpy.context.view_layer.objects.active=ob; ob.select_set(True); bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.normals_make_consistent(inside=False); bpy.ops.object.mode_set(mode='OBJECT'); uv(ob); return ob

def create():
 bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
 steel=mat('PaintedSteel',(.19,.29,.27),.7,.42); bare=mat('BareSteel',(.42,.46,.44),.82,.3); uphol=mat('Upholstery',(.105,.115,.11),0,.88); welt=mat('UpholsteryWelt',(.20,.21,.19),0,.8); wool=mat('WoolThrow',(.57,.48,.35),0,.95)
 f=[]
 # Four light-gauge side-arm panels, back rails and seat support, plus front rail.
 f += [cube('Arm panel',(.026,.47,.95),(-1.02,.405,0),steel,.012),cube('Arm panel',(.026,.47,.95),(1.02,.405,0),steel,.012)]
 f += [cube('Back top rail',(2.02,.04,.035),(0,.83,-.455),steel,.009),cube('Back lower rail',(2.02,.05,.035),(0,.445,-.455),steel,.008)]
 f += [cube('Front seat rail',(1.96,.10,.045),(0,.355,.455),steel,.009),cube('Seat cross rail',(1.95,.035,.045),(0,.36,-.40),steel,.006)]
 f += [cube('Seat support rail',(1.95,.035,.045),(0,.34,-.28),steel,.006),cube('Seat support rail',(1.95,.035,.045),(0,.34,.28),steel,.006)]
 for x in (-1.02,1.02): f.append(cube('Back upright',(.035,.39,.04),(x,.615,-.455),steel,.006))
 # Corner plates mounted on arm faces, rivets parented as own child meshes.
 riv=[]
 for x,sgn in ((-1.037,-1),(1.037,1)):
  for y in (.56,.76):
   p=cube('Corner plate',(.004,.16,.06),(x,y,.42),bare,.008); f.append(p)
   for yy in (y-.055,y+.055):
    for zz in (.395,.445): riv.append(sphere('Rivet',(x+sgn*.003,yy,zz),(.006,.009,.009),bare))
 feet=[]
 for x in (-.94,.94):
  for z in (-.36,.36): feet.append(cube('Foot',(.055,.08,.055),(x,.04,z),bare,.009))
 frame=join('Frame',f); foot=join('Feet',feet); rv=join('Rivets',riv); rv.parent=frame; rv.matrix_parent_inverse=frame.matrix_world.inverted()
 for o in (frame,foot,rv):uv(o)
 # Seat top at 0.455 m, neighbors spaced 10 mm.
 centers=(-.67,0,.67)
 for tag,x in zip('LCR',centers): cushion('SeatCushion_'+tag,(x,.414,.015),(.66,.11,.70),'seat',uphol,welt)
 # Back cushions lean 8 degrees toward the rear, each is an independent closed shell.
 for tag,x in zip('LCR',centers):
  o=cushion('BackCushion_'+tag,(x,.625,-.35),(.66,.31,.17),'back',uphol,welt); o.rotation_euler[0]=math.radians(-8)
 throw_mesh(wool)
 bpy.context.view_layer.update()

def export(path):
 bpy.ops.object.select_all(action='DESELECT')
 for o in bpy.data.objects:o.select_set(True)
 bpy.context.view_layer.objects.active=bpy.data.objects['Frame']; bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_yup=True,export_apply=False,export_materials='EXPORT',export_cameras=False,export_lights=False)

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--output',type=Path,default=OUT); ap.add_argument('--save-source',action='store_true'); ap.add_argument('--render-dir',type=Path); a=ap.parse_args(sys.argv[sys.argv.index('--')+1:]); out=a.output if a.output.is_absolute() else ROOT/a.output; out.parent.mkdir(parents=True,exist_ok=True)
 if a.save_source or not SOURCE.exists():
  create()
  if a.save_source:bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE))
 else:bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
 export(str(out.resolve()))
 if a.render_dir:render_previews(a.render_dir if a.render_dir.is_absolute() else ROOT/a.render_dir)
if __name__=='__main__':main()
