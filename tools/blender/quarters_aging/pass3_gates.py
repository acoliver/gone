"""Exported GLB displacement and exact-resolution first-hit hero-camera masks."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import binary_dilation, binary_erosion
from scipy.optimize import least_squares
from scipy.spatial import ConvexHull, cKDTree
import trimesh

from verify import clean, geometry_buffers, pivots
from visible_gates import boundaries, heights, load, primitive

ROOT=Path(__file__).resolve().parents[3]


def area_centroid(mesh):
    return np.average(mesh.triangles_center,axis=0,weights=mesh.area_faces)


def basis(eye,target):
    forward=np.asarray(target,dtype=float)-eye;forward/=np.linalg.norm(forward)
    right=np.cross(forward,[0,1,0]);right/=np.linalg.norm(right)
    up=np.cross(right,forward)
    return np.array([right,up,forward])


def project(points,eye,target,scale,width,height):
    p=(points-np.asarray(target))@basis(eye,target).T
    return np.c_[width/2+p[:,0]*width/scale,height/2-p[:,1]*width/scale,p[:,2]]


def raster(meshes,eye,target,scale,width=1600,height=1422):
    ids=np.zeros((height,width),dtype=np.int32)
    depth=np.full((height,width),np.inf)
    for mesh,label in meshes:
        pixels=project(mesh.vertices,eye,target,scale,width,height)
        for tri in pixels[mesh.faces]:
            left,top=np.maximum(0,np.floor(tri[:,:2].min(0)).astype(int))
            right,bottom=np.minimum([width-1,height-1],np.ceil(tri[:,:2].max(0)).astype(int))
            if right<left or bottom<top:continue
            a,b,c=tri
            determinant=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
            if abs(determinant)<1e-12:continue
            x,y=np.meshgrid(np.arange(left,right+1)+.5,np.arange(top,bottom+1)+.5)
            u=((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/determinant
            v=((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/determinant
            w=1-u-v;z=u*a[2]+v*b[2]+w*c[2]
            tile=depth[top:bottom+1,left:right+1]
            hit=(u>=-1e-9)&(v>=-1e-9)&(w>=-1e-9)&(z<tile)
            tile[hit]=z[hit];ids[top:bottom+1,left:right+1][hit]=label
    return ids


def rectangle_rms(points):
    points=np.asarray(points)
    centre=points.mean(0);dims=np.ptp(points,axis=0)/2
    def errors(p):
        c,s=np.cos(p[2]),np.sin(p[2]);q=(points-p[:2])@np.array([[c,-s],[s,c]])
        return np.minimum(abs(abs(q[:,0])-abs(p[3])),abs(abs(q[:,1])-abs(p[4])))
    fit=least_squares(errors,[*centre,0,*dims])
    return float(np.sqrt(np.mean(errors(fit.x)**2)))


def sleeve_pose(mesh,lo,hi,reference_uv=None):
    uv=mesh.visual.uv if reference_uv is None else reference_uv
    cuff=(uv[:,0]>lo)&(uv[:,0]<hi)&(uv[:,1]>.97)
    cap=(uv[:,0]>lo)&(uv[:,0]<hi)&(uv[:,1]<.025)
    if reference_uv is None:
        cuff_points=mesh.vertices[cuff];cap_points=mesh.vertices[cap]
    else:
        tree=cKDTree(mesh.visual.uv)
        cuff_points=mesh.vertices[tree.query(uv[cuff])[1]]
        cap_points=mesh.vertices[tree.query(uv[cap])[1]]
    centre=cuff_points.mean(0)
    axis=centre-cap_points.mean(0);axis/=np.linalg.norm(axis)
    return centre,axis


def gate(value,threshold,passed,method=None):
    result={'value':value,'threshold':threshold,'pass':bool(passed)}
    if method:result['method']=method
    return result


def masks(parts,eye,target,scale,labels,out,state):
    meshes=[]
    for name,part in parts.items():
        for mat,mesh in part.metadata['raw_primitives'].items():
            label=labels.setdefault(name+'/'+mat,len(labels)+1)
            meshes.append((mesh,label))
    floor=0. if target[1]>0 else -.95
    ground=trimesh.Trimesh([[-100,floor-.0005,-100],[100,floor-.0005,-100],[100,floor-.0005,100],[-100,floor-.0005,100]],[[0,1,2],[0,2,3]],process=False)
    floor_label=labels.setdefault('StudioFloor/Studio',len(labels)+1)
    meshes.append((ground,floor_label))
    ids=raster(meshes,eye,target,scale)
    # Integer IDs are encoded losslessly as RGB, with a separate readable palette.
    rgb=np.stack([ids%256,(ids//256)%256,ids//65536],axis=2).astype('uint8')
    Image.fromarray(rgb).save(out/f'{state}-hero-ids.png')
    palette=np.array([[0,0,0]]+[[int(55+(i*97)%200),int(55+(i*61)%200),int(55+(i*151)%200)] for i in range(1,len(labels)+1)],dtype='uint8')
    Image.fromarray(palette[ids]).save(out/f'{state}-hero-mask.png')
    return ids


def select(ids,labels,name,mat=None):
    return np.isin(ids,[value for key,value in labels.items() if key.split('/')[0]==name and (mat is None or key.split('/')[1]==mat)])


def save_mask(mask,path):Image.fromarray((mask*255).astype('uint8')).save(path)


def measure(prop,path,out,reexport=None,collisions=None):
    out.mkdir(parents=True,exist_ok=True)
    if prop == 'sofa':
        from sofa_gates import measure as measure_sofa
        result = measure_sofa(path, collisions, reexport)
        (out/'gates.json').write_text(json.dumps(result, indent=2)+'\n')
        return result
    original=ROOT/f'assets/props/quarters/{prop}.glb'
    before,old_doc=load(original);after,new_doc=load(path)
    angle=np.radians(35);sofa=prop=='sofa'
    eye=np.array([3*np.sin(angle),1.8 if sofa else .08,3*np.cos(angle)])
    target=np.array([0,.4 if sofa else -.44,0]);scale=2.85 if sofa else 1.30
    labels={};old_ids=masks(before,eye,target,scale,labels,out,'before');ids=masks(after,eye,target,scale,labels,out,'after')
    (out/'hero-labels.json').write_text(json.dumps({'labels':labels,'eye_gltf_m':eye.tolist(),'target_gltf_m':target.tolist(),'ortho_width_m':scale,'image_size':[1600,1422]},indent=2)+'\n')
    gates={}
    old_n=sum(len(m.faces) for m in before.values());new_n=sum(len(m.faces) for m in after.values())
    gates['triangle_ratio']=gate(new_n/old_n,'<= 1.5',new_n<=1.5*old_n)
    gates['triangles']={'unaged':old_n,'aged':new_n}
    old_pivots,new_pivots=pivots(old_doc),pivots(new_doc)
    same=all(new_pivots.get(n)==v for n,v in old_pivots.items())
    gates['origins_and_pivots']=gate(same,'unchanged',same)
    fixed=['Frame','Feet','Rivets'] if sofa else ['Hanger']
    a,b=geometry_buffers(original),geometry_buffers(path)
    unchanged=all(a[n]==b[n] for n in fixed)
    gates['fixed_geometry_bytes']=gate(unchanged,'identical',unchanged)
    identical=reexport is not None and reexport.exists() and reexport.read_bytes()==path.read_bytes()
    gates['byte_identical_reexport']=gate(identical,'identical',identical)
    if collisions:
        collision=json.loads(collisions.read_text())
        for key in ['self_intersections','part_intersections']:
            gates[key]=gate(collision[key],'0 by triangle SAT',collision[key]==0)
        valid=all(v['pass'] for v in collision['topology'].values())
        gates['export_topology']=gate(valid,'closed crust and unbranched bounded cloth; no nonmanifold or degenerate edges',valid)
    if not sofa:
        outer=primitive(after['TunicBody'],'NaturalFabric');source=before['TunicBody']
        components=int(clean(after['TunicBody']).body_count)
        gates['cloth_connected_components']=gate(components,'1; tear flaps remain attached',components==1)
        for name,lo,hi,band in [('freed',1.1,1.55,(.08,float('inf'))),('retained',1.7,2.15,(.01,.06))]:
            c,a=sleeve_pose(source,lo-1e-4,hi+1e-4);d,b=sleeve_pose(outer,lo-1e-4,hi+1e-4,reference_uv=source.visual.uv)
            shift=float(np.linalg.norm(d-c));angle=float(np.degrees(np.arccos(np.clip(a@b,-1,1))))
            gates[name+'_cuff_displacement_m']=gate(shift,f'{band[0]} to {band[1]}',band[0]<=shift<=band[1])
            gates[name+'_axis_rotation_deg']=gate(angle,'>= 12' if name=='freed' else 'reported',angle>=12 if name=='freed' else True)
        # Surface distance is measured in world coordinates on the actual export.
        distances=[]
        for chunk in np.array_split(outer.vertices,24):distances.extend(trimesh.proximity.closest_point(source,chunk)[1])
        p90=float(np.quantile(distances,.9));gates['cloth_displacement_p90_m']=gate(p90,'>= .040',p90>=.040)
        heap_mask=select(ids,labels,'FibreDust');save_mask(heap_mask,out/'fibre-visible.png')
        gates['fibre_pixels']=gate(int(heap_mask.sum()),'>= 1500',heap_mask.sum()>=1500)
        gates['fibre_floor_drop_m']=gate(float(-after['FibreDust'].bounds[0,1]),'.95 floor with <= .001 gap',abs(after['FibreDust'].bounds[0,1]+.95)<=.001)
        uv=source.visual.uv;cap=(uv[:,0]>=1.0999)&(uv[:,0]<=1.5501)&(uv[:,1]<.025)
        pixels=project(source.vertices[cap],eye,target,scale,1600,1422)[:,:2]
        hull=ConvexHull(pixels);roi_image=Image.new('1',(1600,1422));ImageDraw.Draw(roi_image).polygon([tuple(p) for p in pixels[hull.vertices]],fill=1)
        roi=binary_dilation(np.asarray(roi_image),iterations=6)
        gap=roi&~select(ids,labels,'TunicBody')&select(old_ids,labels,'TunicBody')
        save_mask(roi,out/'armhole-region.png');save_mask(gap,out/'armhole-gap-visible.png')
        gates['armhole_gap_pixels']=gate(int(gap.sum()),'>= 400',gap.sum()>=400,'First-hit pixels lost by cloth inside original near-side armhole projected hull, expanded 6 pixels')
    def passed(value):
        if isinstance(value,dict):return value['pass'] if 'pass' in value else all(passed(v) for v in value.values())
        return True
    result={'prop':prop,'input':str(path),'gates':gates,'pass':passed(gates)}
    (out/'gates.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prop',required=True);p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--reexport',type=Path);p.add_argument('--collisions',type=Path)
    a=p.parse_args()
    result=measure(a.prop,a.input,a.out,a.reexport,a.collisions)
    if not result['pass']:raise SystemExit(1)
