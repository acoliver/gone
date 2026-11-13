"""Retain image-derived fine grain, remove cloudy projection, localize dry oxide."""
import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, distance_transform_edt, map_coordinates
from scipy.spatial import cKDTree
import trimesh
from shapely.geometry import Polygon
from shapely import contains_xy, distance, points

SOURCE=Path(__file__).resolve().parent
ROOT=SOURCE.parents[5]
BEFORE=ROOT/'tmp/issue130-v3/tex1'
OUT=ROOT/'tmp/issue130-v3/tex2'
FIT=OUT/'geom'
SIZE=2048

def read(path):
    return np.asarray(Image.open(path).convert('RGB'),np.float32)/255

def linear(x):
    return np.where(x<=.04045,x/12.92,((x+.055)/1.055)**2.4)

def srgb(x):
    return np.where(x<=.0031308,x*12.92,1.055*np.maximum(x,0)**(1/2.4)-.055)

def save(path,x):
    Image.fromarray(np.uint8(np.clip(x,0,1)*255+.5)).save(path)

def pad(x,occupied):
    indices=distance_transform_edt(~occupied,return_distances=False,return_indices=True)
    return x[tuple(indices)]

def main():
    # Rasterize the rebuilt atlas and find each texel's corrected surface point.
    sys.path.insert(0,'/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d')
    from mlx_hunyuan3d.rasterizer import rasterize
    vertices=[];faces=[];uv=[];part_ids=[];offset=0
    for pi,p in enumerate(json.loads((FIT/'low-arrays.json').read_text())):
        vertices.extend(p['vertices']);faces.extend((np.array(p['triangles'])+offset).tolist())
        uv.extend(p['triangle_uv']);part_ids.extend([pi]*len(p['triangles']));offset+=len(p['vertices'])
    vertices=np.array(vertices);faces=np.array(faces);uv=np.array(uv)
    screen=np.c_[uv.reshape(-1,2)*[SIZE,-SIZE]+[0,SIZE],np.zeros(len(faces)*3)]
    fi,weights=rasterize(screen,np.arange(len(faces)*3).reshape(-1,3),(SIZE,SIZE))
    occupied=fi>0;face=fi[occupied]-1;bary=weights[occupied];part=np.array(part_ids)[face]
    position=np.einsum('ni,nij->nj',bary,vertices[faces[face]])
    normal=np.cross(vertices[faces[:,1]]-vertices[faces[:,0]],vertices[faces[:,2]]-vertices[faces[:,0]])
    normal/=np.linalg.norm(normal,axis=1)[:,None];normal=normal[face]
    old_parts=json.loads((ROOT/'tmp/issue130-v3/fit2/low-arrays.json').read_text())
    source_uv=np.empty((len(position),2))
    transfer_distances=np.empty(len(position))
    for pi,old in enumerate(old_parts):
        ov=np.array(old['vertices']);ot=np.array(old['triangles']);ou=np.array(old['triangle_uv'])
        triangles=ov[ot];tree=cKDTree(triangles.mean(axis=1))
        ids=np.flatnonzero(part==pi)
        for start in range(0,len(ids),6000):
            selected=ids[start:start+6000];p=position[selected]
            candidates=tree.query(p,k=32)[1]
            closest=trimesh.triangles.closest_point(triangles[candidates.reshape(-1)],np.repeat(p,32,axis=0)).reshape(-1,32,3)
            squared=np.sum((closest-p[:,None])**2,axis=2)
            choice=np.argmin(squared,axis=1)
            fi=candidates[np.arange(len(p)),choice]
            co=closest[np.arange(len(p)),choice]
            weights=trimesh.triangles.points_to_barycentric(triangles[fi],co)
            source_uv[selected]=np.einsum('ni,nij->nj',weights,ou[fi])
            transfer_distances[selected]=np.sqrt(squared[np.arange(len(p)),choice])
        print('SOURCE_UV_TRANSFER',pi,len(ids),flush=True)
    np.savez_compressed(OUT/'bakes/uv-surface.npz',occupied=occupied,face=face,bary=bary,position=position,normal=normal,part=part,source_uv=source_uv)
    def source_sample(image):
        coords=[(1-source_uv[:,1])*SIZE-.5,source_uv[:,0]*SIZE-.5]
        return np.stack([map_coordinates(image[...,i],coords,order=1,mode='nearest') for i in range(3)],axis=-1)
    rear=np.zeros((SIZE,SIZE),bool);rear[occupied]=(part==0)&(normal[:,1]>.25)
    rear_support=distance_transform_edt(~rear)<=8
    for name in ['geometry-masks','ao']:
        image=read(OUT/'bakes'/f'{name}.png');wide=read(OUT/'bakes'/f'{name}-rear.png')
        image[rear_support]=wide[rear_support];save(OUT/'bakes'/f'{name}.png',image)
    geometry=read(OUT/'bakes/geometry-masks.png')
    ao=read(OUT/'bakes/ao.png')[...,0]
    settings=json.loads((FIT/'shape-decisions.json').read_text())
    star=Polygon(np.array(settings['star_outline_xz_mm'])/1000)
    xy=position[:,[0,2]]
    sd=distance(points(xy),star.boundary)*np.where(contains_xy(star,xy[:,0],xy[:,1]),-1,1)
    cd=settings['enamel_border_radius_mm']/1000-np.linalg.norm(xy-np.array(settings['circle_center_xz_mm'])/1000,axis=1)
    enamel=np.clip(sd/.000045+.5,0,1)*np.clip(cd/.000045+.5,0,1)*(part==0)*(position[:,1]<-.0007)
    brass=1-enamel
    geometry[...,0][occupied]=enamel
    save(OUT/'bakes/geometry-masks.png',pad(geometry,occupied))
    for label,value in [('enamel-id',enamel),('brass-id',brass),('curvature-convex',geometry[...,1][occupied]),('curvature-concave',geometry[...,2][occupied])]:
        image=np.zeros((SIZE,SIZE));image[occupied]=value;save(OUT/'bakes'/f'{label}.png',pad(image,occupied))
    convex=geometry[...,1][occupied];concave=geometry[...,2][occupied]
    ao_values=ao[occupied]
    # Both terms are measured on the new high; there is no blanket oxide term.
    recess=np.maximum(np.clip((concave-.10)/.65,0,1),np.clip((1-ao_values-.10)/.45,0,1))
    exposed=np.clip(convex/.65,0,1)
    old_enamel=read(BEFORE/'bakes/enamel-id.png')[...,0]>.5
    old_occupied=np.load(BEFORE/'bakes/uv-surface.npz')['occupied']
    outputs={'tex2':{}}
    report={}
    for state,route,sigma,strength in [('remembered','A',10.,.40),('present','B',9.,.52)]:
        source_path=BEFORE/route/state/'basecolor.png'
        source=linear(read(source_path))
        colour=np.zeros((occupied.sum(),3),np.float32)
        detail=np.zeros(occupied.sum())
        material_stats={}
        for material,mask,new_weight in [('brass',~old_enamel,brass),('enamel',old_enamel,enamel)]:
            support=mask&old_occupied
            smooth=np.stack([gaussian_filter(source[...,i]*support,sigma)/np.maximum(gaussian_filter(support.astype(float),sigma),1e-8) for i in range(3)],axis=-1)
            median=np.median(source[support],axis=0)
            highpass=np.clip((source-smooth)/np.maximum(median,.008),-.24,.24)
            nearest=distance_transform_edt(~support,return_distances=False,return_indices=True)
            highpass=highpass[tuple(nearest)]
            fine=source_sample(highpass)*(strength if material=='brass' else .035)
            base=median
            col=base*(1+fine)
            colour+=col*new_weight[:,None]
            detail+=np.mean(fine,axis=1)*new_weight
            material_stats[material]={'median_linear_rgb':base.tolist(),'highpass_sigma_texels':sigma,'fine_detail_strength':strength if material=='brass' else .035,'source_support_texels':int(support.sum())}
        if state=='remembered':
            oxide=np.zeros_like(enamel);dust=np.zeros_like(enamel)
            rough=(np.clip(.37+.04*recess-.025*detail,.30,.45))*brass+.115*enamel
            metallic=.98*brass
            coat=.32*enamel
        else:
            oxide=np.clip((1-np.exp(-2.6*recess))*(1-.88*exposed),0,.87)*brass
            dust=np.clip(.035+.10*recess-.03*exposed,0,.13)
            # Sample the brown colour from the same-state image material.
            metal_source=source[(~old_enamel)&old_occupied]
            luminance=metal_source@np.array([.2126,.7152,.0722])
            oxide_colour=np.median(metal_source[luminance<np.quantile(luminance,.15)],axis=0)*.48
            colour=colour*(1-.78*oxide[:,None])+oxide_colour*(.78*oxide[:,None])
            # Dust changes response without painting large grey reflection marks.
            rough=(np.clip(.525+.035*recess-.02*exposed-.025*detail,.45,.60)+.22*oxide)*brass+(.19+.35*dust)*enamel
            metallic=np.clip(.94-.78*oxide,0,1)*brass
            coat=.10*enamel
        folder=OUT/'tex2'/state;folder.mkdir(parents=True,exist_ok=True)
        maps={'basecolor':srgb(colour),'roughness':rough,'metallic':metallic,'oxide-mask':oxide,'dust-mask':dust,'coat-weight':coat,
              'orm':np.stack([ao_values,rough,metallic],axis=-1)}
        outputs['tex2'][state]={}
        for name,value in maps.items():
            image=np.zeros((SIZE,SIZE)+value.shape[1:],np.float32);image[occupied]=value
            path=folder/(name+'.png');save(path,pad(image,occupied));outputs['tex2'][state][name]=str(path)
        outputs['tex2'][state].update({'normal':str(OUT/'bakes/normal.png'),'ao':str(OUT/'bakes/ao.png')})
        exposed_mask=(brass>.99)&(recess<.05)
        recessed_mask=(brass>.99)&(recess>.4)
        report[state]={'source':str(source_path),'materials':material_stats,
            'exposed_brass_roughness_p05_p50_p95':np.quantile(rough[exposed_mask],[.05,.5,.95]).tolist(),
            'enamel_roughness_p05_p50_p95':np.quantile(rough[enamel>.99],[.05,.5,.95]).tolist(),
            'exposed_oxide_mean':float(np.mean(oxide[exposed_mask])),
            'recess_oxide_mean':float(np.mean(oxide[recessed_mask])) if np.any(recessed_mask) else None,
            'oxide_coverage_above_point1_brass':float(np.mean(oxide[brass>.99]>.1))}
    (OUT/'textures.json').write_text(json.dumps(outputs,indent=2))
    (OUT/'texture-decisions.json').write_text(json.dumps({'states':report,'material_id':'New high-surface ID bake, with exact circular border / preserved generated-star distance coverage evaluated on new low-UV surface positions to avoid triangle-scale boundary aliasing.',
        'grain':'Only image-derived high-pass colour; no procedural noise. Smooth per-material median base removes broad photographic illumination/mottling.',
        'oxide':'Brown same-state image colour; zero base oxide, placement from measured concave curvature and AO, attenuated on convex high points.',
        'normal':'Rebaked corrected high/low, 2048 tangent space, separate rear reach composite.',
        'enamel':'Deep-blue source per-material colour, strongly reduced image contrast; gloss/coat uses continuous geometry normal and uniform roughness, no painted specular patches.',
        'uvs':'Refreshed intrinsic atlas after QEM folded the old UV interpolation. Transfer by closest point among 32 nearest original face centres, then barycentric source-UV sampling. High-pass filtering happens in the original image atlas before transfer.',
        'source_transfer_distance_p50_p95_max_mm':np.quantile(transfer_distances*1000,[.5,.95,1.]).tolist()},indent=2))
    print('TEXTURES_COMPLETE',json.dumps(report,indent=2),flush=True)

if __name__=='__main__':
    main()
