"""Build and render the fitted pilot dress tunic in Blender's native Z-up frame."""
import math
import hashlib
from pathlib import Path
import sys

import bpy
import bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[4]
SOURCE = Path(__file__).resolve().parent / "tunic-working.blend"
OUT = ROOT / "assets/props/quarters/dress_uniform.glb"
SCRATCH = ROOT / "tmp/fit/tunic"


def material(name, color, metallic=0.0, roughness=0.72):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


FABRIC = (0.025, 0.045, 0.085)
MAT = {}


def make_mesh(name, verts, faces, mat, smooth=True):
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free();mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(mat)
    if smooth:
        for poly in mesh.polygons:
            poly.use_smooth = True
    unwrap(obj)
    return obj


def unwrap(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(island_margin=0.015)
    bpy.ops.object.mode_set(mode="OBJECT")


def loft(name, rings, mat, closed=True):
    """Loft equal-vertex horizontal rings; each ring is ordered around its perimeter."""
    n = len(rings[0])
    verts = [tuple(p) for ring in rings for p in ring]
    faces = []
    for j in range(len(rings) - 1):
        for i in range(n):
            a = j*n+i
            b = j*n+(i+1)%n
            faces.append((a,b,b+n,a+n))
    if closed:
        faces.append(tuple(reversed(range(n))))
        faces.append(tuple((len(rings)-1)*n+i for i in range(n)))
    return make_mesh(name, verts, faces, mat)


def ellipse_ring(z, rx, front, back, n=32, center_y=0.0, shape=1.0):
    pts=[]
    for i in range(n):
        a=2*math.pi*i/n
        c,s=math.cos(a),math.sin(a)
        x=rx*math.copysign(abs(c)**shape,c)
        y=(-front*abs(s)**shape if s<0 else back*abs(s)**shape)+center_y
        pts.append((x,y,z))
    return pts


def body():
    # Cross-sections follow the guide's front outline. Nested lofts form a sealed 4 mm cloth shell.
    levels=[(-.925,.207,.066,.041),(-.875,.218,.067,.042),(-.700,.205,.066,.041),(-.485,.176,.061,.039),(-.280,.190,.060,.040),(-.150,.237,.059,.040),(-.095,.252,.055,.038),(-.075,.186,.052,.038)]
    outer=[ellipse_ring(z,w,f,b,40,shape=.92) for z,w,f,b in levels]
    inner=[ellipse_ring(z,w-.004,f-.004,b-.004,40,shape=.92) for z,w,f,b in levels]
    n=len(outer[0]); verts=[tuple(v) for r in outer for v in r]+[tuple(v) for r in inner for v in r]
    faces=[]; layers=len(levels); inner_base=layers*n
    for k in range(layers-1):
        for i in range(n):
            a=k*n+i;b=k*n+(i+1)%n
            faces.append((a,b,b+n,a+n))
            c=inner_base+k*n+i;d=inner_base+k*n+(i+1)%n
            faces.append((c,c+n,d+n,d))
    # Bridge the hem and shoulder rim so the cloth has a measured thickness and closed topology.
    for i in range(n):
        faces.append(((layers-1)*n+i,(layers-1)*n+(i+1)%n,inner_base+(layers-1)*n+(i+1)%n,inner_base+(layers-1)*n+i))
        faces.append((i,inner_base+i,inner_base+(i+1)%n,(i+1)%n))
    return make_mesh("TunicBody",verts,faces,MAT["NaturalFabric"])


def sleeve(side):
    sign=1 if side=="L" else -1
    rings=[]
    # Armpit begins below the body edge; the open visual gap is maintained along the underside.
    for z,cx,rx,ry in [(-.345,.238,.040,.052),(-.390,.242,.040,.052),(-.540,.246,.038,.050),(-.720,.250,.035,.046),(-.855,.252,.035,.045)]:
        rings.append([(sign*cx+rx*math.cos(2*math.pi*i/28),-.020+ry*math.sin(2*math.pi*i/28),z) for i in range(28)])
    # Closed tube ends have a small cuff return and remain a separate watertight part.
    obj=loft("Sleeve_"+side,rings,MAT["NaturalFabric"])
    return obj


def prism(name, points, depth, mat):
    # Extruded polygon with closed caps, all front surfaces face Blender -Y.
    front=[(x,-depth,z) for x,z in points]
    back=[(x,-depth+0.009,z) for x,z in points]
    n=len(points)
    verts=front+back
    faces=[tuple(range(n)),tuple(reversed(range(n,2*n)))]
    faces.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
    return make_mesh(name,verts,faces,mat,False)


def uv_sphere(name, loc, scale, mat, seg=16, rings=8):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=rings, radius=1, location=loc)
    obj=bpy.context.object
    obj.name=name
    obj.scale=scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    for p in obj.data.polygons:p.use_smooth=True
    unwrap(obj)
    return obj


def cylinder_between(name,a,b,r,mat,verts=12):
    mid=(Vector(a)+Vector(b))/2
    d=Vector(b)-Vector(a)
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=d.length, location=mid)
    obj=bpy.context.object; obj.name=name
    obj.rotation_euler=d.to_track_quat('Z','Y').to_euler()
    obj.data.materials.append(mat)
    for p in obj.data.polygons:p.use_smooth=True
    unwrap(obj)
    return obj


def make_hanger():
    pieces=[]
    # Steel shoulder hanger, gently angled into the shoulders.
    coords=[(0,.090,-.040),(-.245,.090,-.125),(-.215,.090,-.145),(0,.090,-.060),(.215,.090,-.145),(.245,.090,-.125),(0,.090,-.040)]
    for a,b in zip(coords,coords[1:]): pieces.append(cylinder_between("Hanger",a,b,.0038,MAT["BareSteel"],10))
    # Continuous curved hook is a polyline of short smooth steel segments.
    hook=[(0,.090,-.040),(0,.090,-.012),(.006,.090,.010),(.024,.090,.022),(.043,.090,.020),(.054,.090,.004),(.052,.090,-.014),(.039,.090,-.030),(.025,.090,-.045),(.020,.090,-.063)]
    for a,b in zip(hook,hook[1:]):pieces.append(cylinder_between("Hanger",a,b,.0032,MAT["BareSteel"],10))
    bpy.ops.object.select_all(action="DESELECT")
    for o in pieces:o.select_set(True)
    bpy.context.view_layer.objects.active=pieces[0]
    bpy.ops.object.join(); obj=bpy.context.object; obj.name="Hanger"
    return obj


def create_asset():
    bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete(use_global=False)
    MAT.update({"NaturalFabric":material("NaturalFabric",FABRIC,0,.86),"Brass":material("Brass",(.62,.43,.16),.78,.27),"RibbonFabric":material("RibbonFabric",(.55,.12,.10),0,.75),"BareSteel":material("BareSteel",(.38,.42,.44),.82,.25)})
    body()
    sleeve("L"); sleeve("R")
    # Standing collar, pair of shoulder boards.
    collar=loft("Collar",[ellipse_ring(-.074,.105,.058,.039,32),ellipse_ring(-.018,.109,.061,.041,32)],MAT["NaturalFabric"])
    for x in (-.156,.156):
        prism("ShoulderBoard_"+("L" if x>0 else "R"),[(x-.018,-.105), (x+.018,-.105),(x+.070,-.177),(x-.070,-.177)],.068,MAT["NaturalFabric"])
    # One row of five domed brass buttons at the front centre line.
    for z in (-.145,-.290,-.435,-.580,-.725):
        uv_sphere("Buttons",(0,-.076,z),(.012,.009,.012),MAT["Brass"])
    # Collar badges and left breast ribbon/medal, located on image-right (wearer's left).
    for x in (-.067,.067):
        uv_sphere("CollarInsignia_"+("L" if x>0 else "R"),(x,-.064,-.066),(.011,.006,.016),MAT["Brass"],12,6)
    # Ribbon strip with alternating coloured bars as one named mesh, plus its lower border.
    ribbon=[]
    for i in range(9):
        c=(.12,.24,.70,.90)[i%4]
        stripe=MAT["RibbonFabric"] if i==0 else material("RibbonStripe_%02d"%i,(c,.08,.07) if i%2==0 else (.82,.68,.34),0,.58)
        prism("RibbonBar",[(.065+i*.010,-.342),(.073+i*.010,-.342),(.073+i*.010,-.315),(.065+i*.010,-.315)],.068,stripe)
    uv_sphere("Medal",(.107,-.066,-.358),(.009,.006,.014),MAT["Brass"],12,6)
    make_hanger()
    # Move the hook's highest point, including its wire radius, to the asset origin.
    for obj in list(bpy.context.scene.objects):
        if obj.type=="MESH":
            obj.location.z-=.0252
            obj.location.y-=.090
    bpy.context.view_layer.update()


def aim(obj,target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()


def camera(name, loc, target, scale, res):
    data=bpy.data.cameras.new(name); obj=bpy.data.objects.new(name,data); bpy.context.scene.collection.objects.link(obj)
    obj.location=loc; aim(obj,target); data.type='ORTHO'; data.ortho_scale=scale
    bpy.context.scene.camera=obj
    s=bpy.context.scene;s.render.resolution_x=res;s.render.resolution_y=res;s.render.resolution_percentage=100
    return obj


def light_setup():
    scene=bpy.context.scene; scene.render.engine='BLENDER_EEVEE_NEXT'; scene.render.image_settings.file_format='PNG'; scene.render.film_transparent=False
    scene.world.color=(.72,.72,.72); scene.view_settings.view_transform='Standard'; scene.view_settings.look='Medium High Contrast'
    for name,loc,energy,size in [('Key',(-2,-3,2.7),520,3.2),('Fill',(2,2,1.5),360,3.4),('Top',(0,-.4,3.2),210,2.2)]:
        d=bpy.data.lights.new(name,'AREA');o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=loc;d.energy=energy;d.shape='DISK';d.size=size


def render_all():
    SCRATCH.mkdir(parents=True,exist_ok=True); light_setup(); scene=bpy.context.scene
    camera('Hero',(.10,-3.5,.32),(0,-.01,-.46),1.22,768)
    scene.render.filepath=str(SCRATCH/'hero-render.png');bpy.ops.render.render(write_still=True)
    for angle in (30,120,210,300):
        rad=math.radians(angle);camera('Turntable',(3.4*math.sin(rad),-3.4*math.cos(rad),.35),(0,0,-.46),1.22,400)
        scene.render.filepath=str(SCRATCH/f'turn-{angle}.png');bpy.ops.render.render(write_still=True)
    camera('Detail',(0,-2,-.25),(0,-.04,-.25),.46,600);scene.render.filepath=str(SCRATCH/'detail-render.png');bpy.ops.render.render(write_still=True)
    # Compose sheets with Blender's image datablocks only.
    compose(SCRATCH/'compare-hero.png',[ROOT/'docs/art/quarters/sheets/dress_uniform/hero.png',SCRATCH/'hero-render.png'])
    compose(SCRATCH/'turntable.png',[SCRATCH/f'turn-{a}.png' for a in (30,120,210,300)])
    design=ROOT/'docs/art/quarters/sheets/dress_uniform/hero.png'
    crop_design(design,SCRATCH/'design-detail-crop.png',(270,510,750,920))
    compose(SCRATCH/'compare-detail.png',[SCRATCH/'design-detail-crop.png',SCRATCH/'detail-render.png'])


def crop_design(source,destination,box):
    image=bpy.data.images.load(str(source),check_existing=True)
    x0,y0,x1,y1=box;w=image.size[0];h=image.size[1];rows=list(image.pixels[:])
    out_w=x1-x0;out_h=y1-y0
    cropped=bpy.data.images.new(destination.stem,width=out_w,height=out_h,alpha=True)
    pix=[0.72,0.72,0.72,1.0]*(out_w*out_h)
    for y in range(out_h):
        source_start=((y0+y)*w+x0)*4;dest_start=y*out_w*4
        pix[dest_start:dest_start+out_w*4]=rows[source_start:source_start+out_w*4]
    cropped.pixels[:]=pix;cropped.filepath_raw=str(destination);cropped.file_format='PNG';cropped.save()


def compose(path, inputs):
    imgs=[bpy.data.images.load(str(p),check_existing=True) for p in inputs]
    widths=[im.size[0] for im in imgs]; heights=[im.size[1] for im in imgs]
    h=max(heights); total=sum(widths)
    out=bpy.data.images.new(path.stem,width=total,height=h,alpha=True)
    pix=[.72,.72,.72,1.0]*(total*h)
    for im,x0 in zip(imgs,[sum(widths[:i]) for i in range(len(widths))]):
        # Blender pixel rows are bottom-up; center each input vertically.
        pad=(h-im.size[1])//2
        src=list(im.pixels[:]); w=im.size[0]; ih=im.size[1]
        for y in range(ih):
            dst=((y+pad)*total+x0)*4; src0=y*w*4
            pix[dst:dst+w*4]=src[src0:src0+w*4]
    out.pixels[:]=pix;out.filepath_raw=str(path);out.file_format='PNG';out.save()


def export(path):
    bpy.ops.object.select_all(action='DESELECT')
    for o in bpy.data.objects:
        if o.type=='MESH':o.select_set(True)
    bpy.context.view_layer.objects.active=next(o for o in bpy.data.objects if o.name=='TunicBody')
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_yup=True,export_apply=False,export_materials='EXPORT',export_cameras=False,export_lights=False)


def main():
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    save='--save-source' in args
    output=Path(args[args.index('--output')+1]) if '--output' in args else OUT
    if not output.is_absolute():output=ROOT/output
    if save or not SOURCE.exists():
        create_asset()
        bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE))
    else:bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    output.parent.mkdir(parents=True,exist_ok=True);export(str(output))
    if '--render' in args:render_all()
    if output==OUT:
        tmp=SCRATCH/'reexport.glb';export(str(tmp))
        if hashlib.sha256(OUT.read_bytes()).digest()!=hashlib.sha256(tmp.read_bytes()).digest():raise RuntimeError('GLB re-export is not byte-identical')
        tmp.unlink()

if __name__=='__main__':main()
