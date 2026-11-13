"""Independent pass-two surface, correspondence split, topology and UV checks."""
from pathlib import Path
import json
import struct
import sys
import numpy as np
import trimesh
from shapely.geometry import Polygon
from shapely.strtree import STRtree

SOURCE=Path(__file__).resolve().parent
ROOT=SOURCE.parents[4]
OUT=(Path(sys.argv[sys.argv.index('--output')+1]) if '--output' in sys.argv
     else ROOT/'tmp/issue130-v3/fit1')
fit=json.loads((OUT/'fit-report.json').read_text())
scale=fit['uniform_scale']
origin=np.array(fit['raw_origin'])


def arrays(label):
    if label=='raw':
        return json.loads((OUT/'raw-arrays.json').read_text())
    scene=trimesh.load(OUT/('medal-'+label+'.glb'),force='scene')
    result=[]
    for node in scene.graph.nodes_geometry:
        transform,geometry=scene.graph[node]
        component=scene.geometry[geometry].copy()
        component.apply_transform(transform)
        # Merge glTF's UV/normal splits before checking geometric topology.
        component.merge_vertices(merge_tex=True,merge_norm=True,digits_vertex=10)
        component.vertices=np.column_stack([component.vertices[:,0],
            -component.vertices[:,2],component.vertices[:,1]])
        result.append({'name':node,'vertices':component.vertices.tolist(),
                       'triangles':component.faces.tolist()})
    return result


def mesh(data):
    return trimesh.Trimesh(data['vertices'],data['triangles'],process=False)


def nearest(surface,points):
    chunks=[trimesh.proximity.closest_point(surface,points[i:i+400]) for i in range(0,len(points),400)]
    return tuple(np.concatenate([c[j] for c in chunks]) for j in range(3))


def stats(values):
    return {'samples':len(values),'median_mm':float(np.median(values)*1000),
            'p95_mm':float(np.percentile(values,95)*1000),'max_mm':float(np.max(values)*1000),
            'rms_mm':float(np.sqrt(np.mean(values**2))*1000)}


def regions(points,part,normals):
    if not part.startswith('Body'):
        return np.full(len(points),part.split('_')[0],dtype=object)
    from shapely import contains_xy
    from shapely.geometry import Polygon
    features=json.loads((OUT/'features.json').read_text())['features']
    curves={f['name']:np.array(f['points_mm'])[:,[0,2]]/1000 for f in features}
    star=contains_xy(Polygon(curves['star_outline']),points[:,0],points[:,2])
    rim=contains_xy(Polygon(curves['rim_step_0']),points[:,0],points[:,2])
    result=np.full(len(points),'body_edge',dtype=object)
    result[(normals[:,1]<-.25)&~rim]='rim_steps'
    result[(normals[:,1]<-.25)&rim&~star]='recessed_field'
    result[(normals[:,1]<-.25)&star]='star'
    result[normals[:,1]>.25]='rear'

    return result


def internal_contacts(points,part,normals):
    u=points/scale+origin
    neck=abs(u[:,2]-.455)*scale<.00025
    side=(abs(abs(u[:,0])-.13)*scale<.00025)&(u[:,2]>.80)&(abs(normals[:,0])>.45)
    if part.startswith('Body'):
        return neck&(normals[:,2]>.45)
    if part.startswith('Loop'):
        return (neck&(normals[:,2]<-.45))|side
    return side


def uv_check(label):
    blob=(OUT/('medal-'+label+'.glb')).read_bytes()
    size=struct.unpack_from('<I',blob,12)[0]
    doc=json.loads(blob[20:20+size])
    binary=blob[28+size:]
    def accessor(index,n):
        a=doc['accessors'][index]
        view=doc['bufferViews'][a['bufferView']]
        dtype=np.dtype({5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}[a['componentType']])
        offset=view.get('byteOffset',0)+a.get('byteOffset',0)
        return np.ndarray((a['count'],n),dtype=dtype,buffer=binary,offset=offset,
                          strides=(view.get('byteStride',n*dtype.itemsize),dtype.itemsize)).copy()
    triangles=[]
    signed=[]
    for model in doc['meshes']:
        for p in model['primitives']:
            uv=accessor(p['attributes']['TEXCOORD_0'],2)
            index=accessor(p['indices'],1).reshape(-1,3)
            triangles.append(uv[index])
    uv=np.concatenate(triangles).astype(float)
    a,b=uv[:,1]-uv[:,0],uv[:,2]-uv[:,0]
    area=(a[:,0]*b[:,1]-a[:,1]*b[:,0])/2
    polys=[Polygon(t) for t in uv]
    tree=STRtree(polys)
    conflicts=[]
    for i,p in enumerate(polys):
        for j in tree.query(p):
            if j>i and p.intersection(polys[int(j)]).area>1e-12:
                conflicts.append([i,int(j)])
    return {'triangles':len(uv),'checked_source':'Exported GLB TEXCOORD_0 and indices, all parts together',
            'zero_area_triangles':int(np.sum(abs(area)<=1e-14)),
            'positive_area_overlaps':len(conflicts),'first_overlap_pairs':conflicts[:10],
            'min_triangle_area_uv':float(abs(area).min()),
            'uv_bounds':[uv.min(axis=(0,1)).tolist(),uv.max(axis=(0,1)).tolist()]}


raw=mesh(arrays('raw')[0])
lowpass=np.load(OUT/'raw-lowpass.npz')['vertices']
report={'method':'Seeded area-weighted samples and exact nearest triangle points. Millimetres. Front regions use newly detected star and inner-rim polygons; rear uses the raw normal. Contact caps are separated.',
        'split_method':'For each clean sample P, find its closest raw point R and interpolate the low-passed raw position L at the SAME raw triangle barycentric coordinates. P-R = (L-R) + (P-L). The first vector estimates removed high-frequency structure; the second measures departure from the low-passed source. RMS components need not add because their cross term may be negative. This is a scale-dependent geometric decomposition, not proof of which irregularities were intended manufacturing features.',
        'lowpass':'240 alternating topology Taubin iterations, lambda .5 / nu .53; frozen source connectivity.',
        'high':{},'low':{}}
for label in ['high','low']:
    values={}
    noise={}
    shape={}
    covariance={}
    topology={}
    parts=[]
    for data in arrays(label):
        component=mesh(data)
        parts.append(component)
        points,faces=trimesh.sample.sample_surface(component,30000 if data['name'].startswith('Body') else 10000,seed=130)
        closest,distance,raw_faces=nearest(raw,points)
        bary=trimesh.triangles.points_to_barycentric(raw.triangles[raw_faces],closest)
        low= np.einsum('ij,ijk->ik',bary,lowpass[raw.faces[raw_faces]])
        lump=low-closest
        remainder=points-low
        assert np.allclose(lump+remainder,points-closest,atol=1e-12)
        tags=regions(closest,data['name'],raw.face_normals[raw_faces])
        tags[internal_contacts(points,data['name'],component.face_normals[faces])]='internal_contact_caps'
        for tag in np.unique(tags):
            mask=tags==tag
            values.setdefault(tag,[]).extend(distance[mask])
            noise.setdefault(tag,[]).extend(np.linalg.norm(lump[mask],axis=1))
            shape.setdefault(tag,[]).extend(np.linalg.norm(remainder[mask],axis=1))
            covariance.setdefault(tag,[]).extend(2*np.sum(lump[mask]*remainder[mask],axis=1))
        topology[data['name']]={'triangles':len(component.faces),'watertight':bool(component.is_watertight),
            'consistent_winding':bool(component.is_winding_consistent),
            'min_triangle_area_m2':float(component.area_faces.min())}
    report[label]['clean_to_raw']={k:stats(np.array(v)) for k,v in sorted(values.items())}
    report[label]['lump_vs_shape']={k:{'raw_lowpass_difference':stats(np.array(noise[k])),
        'clean_lowpass_residual':stats(np.array(shape[k])),
        'cross_term_mean_mm2':float(np.mean(covariance[k])*1e6)} for k in sorted(values)}
    report[label]['topology']=topology
    all_parts=trimesh.util.concatenate(parts)
    p,f=trimesh.sample.sample_surface(raw,40000,seed=131)
    _,distance,_=nearest(all_parts,p)
    raw_z=p[:,2]/scale+origin[2]
    names=np.where(raw_z<.455,'Body',np.where((raw_z>.80)&(abs(p[:,0]/scale)>.13),'Bar','Loop'))
    back={}
    for name in ['Body','Loop','Bar']:
        mask=names==name
        tags=regions(p[mask],name,raw.face_normals[f[mask]])
        for tag in np.unique(tags):
            back[tag]=stats(distance[mask][tags==tag])
    report[label]['raw_to_clean']=back
    report[label]['uv']=uv_check(label)
    exported=trimesh.load(OUT/('medal-'+label+'.glb'),force='mesh')
    report[label]['exported_gltf_bounds_m']=exported.bounds.tolist()
    report[label]['exported_triangles']=len(exported.faces)
    assert exported.extents[1]>.04 and exported.extents[2]<.015
    print('MEASURED',label,flush=True)
(OUT/'verification.json').write_text(json.dumps(report,indent=2))
for label in ['high','low']:
    uv=report[label]['uv']
    assert uv['zero_area_triangles']==0, (label,uv)
    assert uv['positive_area_overlaps']==0, (label,uv)
    assert np.min(uv['uv_bounds'])>=0 and np.max(uv['uv_bounds'])<=1
    assert all(x['watertight'] and x['consistent_winding'] and x['min_triangle_area_m2']>1e-17 for x in report[label]['topology'].values())
assert report['low']['exported_triangles']<=fit['budget']
print(json.dumps(report,indent=2),flush=True)
