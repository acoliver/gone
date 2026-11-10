"""Shared formed ceiling-seat source, in glTF metres (+Y up, length +X).

The 36 mm bearing face is preserved. The two manufacturing folds extend
3 mm outside it, yielding a 42 x 18 mm envelope instead of shrinking its seat.
"""
from pathlib import Path
import hashlib
import json
import math
import numpy as np
import trimesh
from shapely.geometry import Polygon
from PIL import Image
from scipy.ndimage import gaussian_filter

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT/'art-source/stasis-wiring/seat-rail'
OUT = ROOT/'assets/props/stasis-wiring/seat-rail'


def profile():
    # Outer perimeter clockwise from the bearing face. Radii 3 mm outside,
    # 0.5 mm inside give a constant 2.5 mm metal gauge at the bends.
    pts = [(0., -.018), (0., .018)]
    def arc(cy, cz, r, a, b, steps=8):
        for t in np.linspace(a,b,steps+1)[1:]:
            pts.append((cy+r*math.cos(t),cz+r*math.sin(t)))
    arc(-.003,.018,.003,0,math.pi/2)
    pts.extend([(-.006,.021),(-.010,.021),(-.015,.021)])
    arc(-.015,.018,.003,math.pi/2,math.pi)
    pts.extend([(-.018,.015),(-.0155,.015),(-.0155,.018)])
    arc(-.015,.018,.0005,math.pi,math.pi/2)
    pts.extend([(-.010,.0185),(-.006,.0185),(-.003,.0185)])
    arc(-.003,.018,.0005,math.pi/2,0)
    pts.extend([(-.0025,-.018)])
    arc(-.003,-.018,.0005,0,-math.pi/2)
    pts.extend([(-.006,-.0185),(-.010,-.0185),(-.015,-.0185)])
    arc(-.015,-.018,.0005,-math.pi/2,-math.pi)
    pts.extend([(-.0155,-.015),(-.018,-.015),(-.018,-.018)])
    arc(-.015,-.018,.003,math.pi,math.pi*1.5)
    pts.extend([(-.010,-.021),(-.006,-.021),(-.003,-.021)])
    arc(-.003,-.018,.003,-math.pi/2,0)
    return np.asarray(pts[:-1])  # final arc endpoint closes onto the first point


def _cut_offset(p, side):
    # One shear contour across the developed sheet, shared by both cut sides.
    arc = np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    teeth = np.interp(arc,np.linspace(0,arc[-1],13),[0,.001,-.001,.002,.0005,-.0015,0,.0015,-.002,.001,0,-.001,0])
    return teeth * (1 if side == 'left' else -1)


def _source():
    p = profile()
    n = len(p)
    stations = np.array([-.6,-.5,-.36,-.342,-.20,0,.20,.342,.36,.5,.6])
    rings = np.zeros((len(stations),n,3))
    rings[:,:,0] = stations[:,None]
    rings[:,:,1:] = p
    rings[1,:,0] += _cut_offset(p,'left')
    rings[-2,:,0] += _cut_offset(p,'right')
    perimeter = np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    uv = np.stack([np.broadcast_to((stations[:,None]+.6)/1.2,(len(stations),n)),np.broadcast_to(perimeter[None,:]/.12,(len(stations),n))],axis=-1)
    uv[:,:,0] = (rings[:,:,0]+.6)/1.2
    faces, segment_ids = [], []
    # Remove matching outer/inner return patches and bridge their boundaries:
    # these are through-punched slots, never black polygons on solid steel.
    slot_edges = []
    for z in [.021,-.021,.0185,-.0185]:
        ids = [i for i in range(n) if abs(p[i,1]-z)<1e-10 and p[i,0] in [-.006,-.010]]
        assert len(ids)==2
        slot_edges.append(tuple(ids))
    skipped = set()
    for ids in slot_edges:
        a,b=ids
        skipped.add(a if (a+1)%n==b else b)
    for j in range(len(stations)-1):
        slot = j in [2,7]
        for k in range(n):
            if slot and k in skipped: continue
            a,b=j*n+k,j*n+(k+1)%n
            faces.extend([[a,b,a+n],[b,b+n,a+n]])
            segment_ids.extend([j,j])
        if slot:
            for outer,inner in [(slot_edges[0],slot_edges[2]),(slot_edges[1],slot_edges[3])]:
                a,b=sorted(outer,key=lambda i:p[i,0]); c,d=sorted(inner,key=lambda i:p[i,0])
                for q in [[j*n+a,j*n+b,j*n+d,j*n+c],[(j+1)*n+a,(j+1)*n+c,(j+1)*n+d,(j+1)*n+b],
                          [j*n+a,j*n+c,(j+1)*n+c,(j+1)*n+a],[j*n+b,(j+1)*n+b,(j+1)*n+d,j*n+d]]:
                    faces.extend([[q[0],q[1],q[2]],[q[0],q[2],q[3]]]); segment_ids.extend([j,j])
    # Earcut indexes the actual concave metal perimeter, leaving the C void empty.
    import mapbox_earcut
    cap = mapbox_earcut.triangulate_float64(p.astype('float64'),np.array([n],dtype='uint32')).reshape(-1,3)
    return rings.reshape(-1,3), uv.reshape(-1,2), np.array(faces), np.array(segment_ids), cap, n


def _part(source, lo, hi):
    vertices,uv,faces,segments,cap,n=source
    body=faces[(segments>=lo)&(segments<hi)]
    cap_faces=np.concatenate([cap+lo*n,cap+hi*n])
    selected=np.concatenate([body,cap_faces])
    used=np.unique(selected)
    remap=np.full(len(vertices),-1); remap[used]=np.arange(len(used))
    mesh=trimesh.Trimesh(vertices[used],remap[selected],process=False)
    mesh.fix_normals()
    mesh.visual=trimesh.visual.TextureVisuals(uv=uv[used])
    mesh.metadata['source_vertex_ids']=used
    mesh.metadata['source_face_ids']=np.r_[np.flatnonzero((segments>=lo)&(segments<hi)),np.full(len(cap_faces),-1)]
    assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0
    return mesh


def make_rail():
    return _part(_source(),0,10)


def rail_family():
    source=_source()
    vertices,_,_,_,_,n=source
    full=_part(source,0,10)
    # Full source uses every vertex; source ids consequently index its UV field.
    assert np.array_equal(full.metadata['source_vertex_ids'],np.arange(len(vertices)))
    return {'full':full,'left':_part(source,0,1),'middle':_part(source,1,9),'right':_part(source,9,10),
            'cuts':{name:{'retained':vertices[i*n:(i+1)*n].copy(),'fragment':vertices[i*n:(i+1)*n].copy()}
                    for name,i in [('left',1),('right',9)]}}


def floor_pose(mesh):
    # app/rod.gd: Ry(82) * Rx(90) applied to CylinderMesh's local +Y.
    # The bay frame then maps local +X to world -Z, so the WORLD pickup
    # proxy (0.22, 0.10, 1.15) fits the resulting near-Z long axis.
    yaw=math.radians(82)
    long=np.array([math.sin(yaw),0,math.cos(yaw)])
    up=np.array([0,1,0]); cross=np.cross(long,up)
    basis=np.column_stack([long,up,cross])
    roll=trimesh.transformations.rotation_matrix(math.radians(115),[1,0,0])[:3,:3]
    basis=basis@roll
    pose=np.eye(4);pose[:3,:3]=basis
    pose[:3,3]=[-.6,0,-1.4]
    pose[1,3]=-np.min((mesh.vertices@basis.T)[:,1])
    return pose


def prepare_material():
    OUT.mkdir(parents=True,exist_ok=True)
    # Real CC0 steel scan supplies fine grain. Broad source illumination and
    # orange dominance are removed; corrosion is confined by functional wear masks.
    src=Image.open(ROOT/'art-source/steel/rusty_metal_04_albedo.jpg').convert('RGB').resize((2048,256))
    rgb=np.asarray(src,dtype=float)/255
    lum=rgb@np.array([.2126,.7152,.0722])
    grain=np.clip(lum/np.maximum(gaussian_filter(lum,5),.02),.78,1.22)
    steel=np.clip(.39*grain[...,None]*np.array([.97,1.,1.025]),0,1)
    x=np.linspace(-.6,.6,2048)[None,:]
    p=profile(); developed=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    v=np.arange(256)[:,None]/255*.12
    edge=np.zeros_like(v)
    # Sparse oxidation at lip edges and two clamp footprints, measured in metres.
    for at in developed[[10,20,35,45]]:
        edge=np.maximum(edge,np.exp(-((v-at)/.0007)**2))
    clip=sum(np.exp(-((x-at)/.006)**2) for at in [-.351,.351])
    source_rust=np.clip((rgb[:,:,0]-rgb[:,:,2])/.20,0,1)
    mask=np.clip((edge*.32*(.35+.65*source_rust)+clip*.65*source_rust),0,.8)
    rust=np.clip(rgb*np.array([.65,.53,.43]),0,1)
    color=steel*(1-mask[:,:,None])+rust*mask[:,:,None]
    albedo=np.rint(color*255).astype('uint8')
    Image.fromarray(albedo).save(OUT/'steel-albedo.png')
    rough=np.clip(.76+.10*mask+.04*(grain-1),0,1)
    metal=.87*(1-mask)+.24*mask
    orm=np.stack([np.ones_like(rough),rough,metal],axis=-1)
    Image.fromarray(np.rint(orm*255).astype('uint8')).save(OUT/'steel-orm.png')
    height=(grain-1)*.000025
    dv,du=np.gradient(height,.12/255,1.2/2047)
    normal=np.stack([-du,-dv,np.ones_like(du)],axis=-1)
    normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    Image.fromarray(np.rint((normal*.5+.5)*255).astype('uint8')).save(OUT/'steel-normal.png')
    from scipy.ndimage import label, find_objects
    labels,_=label(mask>.25)
    patches=find_objects(labels)
    largest_patch=max(((region[1].stop-region[1].start)*1.2/2048 for region in patches),default=0.)
    metrics={'source_scan':'art-source/steel/rusty_metal_04_albedo.jpg','image_derived_not_noise':True,
        'largest_connected_rust_patch_axial_m':float(largest_patch),
        'rust_edge_band_sigma_m':.0007,'clip_scar_axial_sigma_m':.006,
        'atlas_physical_size_m':[1.2,.12],'pixel_size_m':[1.2/2048,.12/256],
        'rust_mask_over_0_25_fraction':float(np.mean(mask>.25)),
        'gray_body_fraction':float(np.mean(mask<.1)), 'albedo_std':float(np.std(color)),
        'normal_convention':'OpenGL +Y; 25 micrometre image-derived grain height',
        'roughness_range':[float(rough.min()),float(rough.max())]}
    (OUT/'material.json').write_text(json.dumps(metrics,indent=2)+'\n')
    return metrics


def material():
    images=[]
    for name in ['steel-albedo.png','steel-orm.png','steel-normal.png']:
        with Image.open(OUT/name) as source:
            images.append(source.copy())
    return trimesh.visual.material.PBRMaterial(name='seat_rail_gray_steel',baseColorTexture=images[0],
        metallicRoughnessTexture=images[1],normalTexture=images[2],metallicFactor=1,roughnessFactor=1)


def apply_material(mesh):
    mesh.visual=trimesh.visual.TextureVisuals(uv=mesh.visual.uv,material=material())
    return mesh


def build():
    prepare_material()
    family=rail_family()
    for name in ['full','left','middle','right']:
        mesh=apply_material(family[name])
        scene=trimesh.Scene();scene.add_geometry(mesh,node_name='seat_rail_'+name)
        (OUT/(name+'.glb')).write_bytes(scene.export(file_type='glb'))
    study=family['full'].copy()
    study.vertices[:,0]*=.32/1.2
    # Keep real 18 mm punched slots when shortening the representative study.
    for old,new in [(-.36,-.1026),(-.342,-.0846),(.342,.0846),(.36,.1026)]:
        mask=np.isclose(family['full'].vertices[:,0],old,atol=1e-10)
        study.vertices[mask,0]=new
    uv=study.visual.uv.copy();uv[:,0]=(study.vertices[:,0]+.6)/1.2
    study.visual=trimesh.visual.TextureVisuals(uv=uv,material=material())
    scene=trimesh.Scene();scene.add_geometry(study,node_name='seat_rail_short_study')
    (OUT/'study.glb').write_bytes(scene.export(file_type='glb'))
    source=_source()
    np.savez(ART/'source-cage.npz',**{k:v for k,v in zip(['vertices','uv','faces','segments','cap','profile_count'],source)})
    return family


if __name__=='__main__':
    build()
