"""Transfer generated colour and project material-separated photographic references."""
import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, distance_transform_edt, map_coordinates, label
from scipy.optimize import least_squares
from scipy.spatial import ConvexHull, cKDTree
from common import FIT, OUT, HY, REFS, SIZE
sys.path.insert(0, str(HY))
from mlx_hunyuan3d.rasterizer import rasterize


def read(path):
    return np.asarray(Image.open(path).convert('RGB'), np.float32)/255


def save(path, array):
    Image.fromarray(np.uint8(np.clip(array,0,1)*255+.5)).save(path)


def linear(rgb):
    return np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)


def srgb(rgb):
    return np.where(rgb<=.0031308,rgb*12.92,1.055*np.maximum(rgb,0)**(1/2.4)-.055)


def sample(image, xy):
    return np.stack([map_coordinates(image[...,c],[xy[:,1],xy[:,0]],order=1,mode='nearest')
                     for c in range(image.shape[-1])],axis=-1)


def pad(image, occupied):
    index = distance_transform_edt(~occupied, return_distances=False, return_indices=True)
    return image[tuple(index)]


def ellipse_for_blue(rgb):
    h,w = rgb.shape[:2]
    yy,xx = np.mgrid[:h,:w]
    r,g,b = rgb.transpose(2,0,1)
    blue = (b>r*1.7)&(b>g*1.22)&(b>.10)
    labels,n = label(blue)
    counts = np.bincount(labels.ravel()); counts[0]=0
    # The blue wool and ribbon share the enamel hue. Select complete central
    # lower components, never the frame-spanning fabric or upper ribbon.
    keep = []
    for component in np.flatnonzero(counts>500):
        cy,cx = np.nonzero(labels==component)
        if cx.min()>w*.30 and cx.max()<w*.72 and cy.min()>h*.35 and cy.max()<h*.90:
            keep.append(component)
    assert keep, 'No isolated enamel pockets detected'
    keep = [i for i in keep if counts[i] >= max(counts[j] for j in keep)*.12]
    blue &= np.isin(labels,keep)
    y,x = np.nonzero(blue)
    points = np.c_[x,y]
    hull = points[ConvexHull(points).vertices]
    def residual(p):
        cx,cy,la,lb,theta = p
        a,b = np.exp([la,lb]); c,s=np.cos(theta),np.sin(theta)
        dx,dy=hull[:,0]-cx,hull[:,1]-cy
        return ((c*dx+s*dy)/a)**2+((-s*dx+c*dy)/b)**2-1
    p=least_squares(residual,[*hull.mean(0),np.log(np.ptp(x)/2),np.log(np.ptp(y)/2),0],loss='soft_l1').x
    a,b=np.exp(p[2:4]); c,s=np.cos(p[4]),np.sin(p[4])
    matrix=np.array([[c,-s],[s,c]])@np.diag([a,b])@np.array([[c,s],[-s,c]])
    return blue, p[:2], matrix, {'center_px':p[:2].tolist(),'axes_px':[a,b],
        'rotation_radians':float(p[4]),'fit_rms':float(np.sqrt(np.mean(residual(p)**2))),
        'blue_pixels':len(points),'blue_bbox':[int(x.min()),int(y.min()),int(x.max()),int(y.max())]}


def photo_data(path):
    rgb = read(path)
    blue,center,matrix,report=ellipse_for_blue(rgb)
    yy,xx=np.mgrid[:rgb.shape[0],:rgb.shape[1]]
    local=np.stack([xx-center[0],yy-center[1]],axis=-1)@np.linalg.inv(matrix).T
    radius=np.linalg.norm(local,axis=-1)
    r,g,b=rgb.transpose(2,0,1)
    masks=[(r>b*1.2)&(g>b*1.05)&(r>g*.95)&(radius<1.35),blue&(radius<1.08)]
    maps=[];stats=[]
    for material,mask in zip(['brass','enamel'],masks):
        assert mask.sum()>100,(path,material,mask.sum())
        col=linear(rgb)
        luminance=col@np.array([.2126,.7152,.0722])
        sigma=max(matrix.diagonal())*.14
        smooth=gaussian_filter(luminance*mask,sigma)/np.maximum(gaussian_filter(mask.astype(float),sigma),1e-8)
        target=float(np.median(luminance[mask]))
        # Divide only the smooth per-material illumination estimate. Retain fine
        # photographed colour, scratches, oxide and dust rather than inventing noise.
        delit=col*(target/np.maximum(smooth,.004))[...,None]
        nearest=distance_transform_edt(~mask,return_distances=False,return_indices=True)
        filled=delit[tuple(nearest)]
        maps.append(filled)
        stats.append({'material':material,'pixels':int(mask.sum()),'smooth_sigma_px':float(sigma),
                      'linear_luminance_median':target,
                      'median_linear_rgb':np.median(delit[mask],axis=0).tolist(),
                      'luminance_p10_p90':np.quantile(luminance[mask],[.1,.9]).tolist()})
        save(OUT/'projection'/f'{path.stem}-{material}-delit.png',srgb(filled))
        save(OUT/'projection'/f'{path.stem}-{material}-mask.png',mask)
    report.update({'path':str(path),'delight':'linear colour divided by Gaussian per-material smooth luminance, preserving median luminance',
                   'materials':stats,'unobserved_pixels':'Nearest observed pixel of the same material; no procedural colour.'})
    return maps,center,matrix,report


def main():
    parts=json.loads((FIT/'low-arrays.json').read_text())
    vertices=[];faces=[];uv=[];part_ids=[];offset=0
    for pi,part in enumerate(parts):
        vertices.extend(part['vertices']);faces.extend((np.array(part['triangles'])+offset).tolist())
        uv.extend(part['triangle_uv']);part_ids.extend([pi]*len(part['triangles']))
        offset+=len(part['vertices'])
    vertices=np.array(vertices);faces=np.array(faces);uv=np.array(uv);part_ids=np.array(part_ids)
    screen=np.c_[uv.reshape(-1,2)*[SIZE,-SIZE]+[0,SIZE],np.zeros(len(faces)*3)]
    fi,bary=rasterize(screen,np.arange(len(faces)*3).reshape(-1,3),(SIZE,SIZE))
    occupied=fi>0;face=fi[occupied]-1;weights=bary[occupied]
    position=np.einsum('ni,nij->nj',weights,vertices[faces[face]])
    normals=np.cross(vertices[faces[:,1]]-vertices[faces[:,0]],vertices[faces[:,2]]-vertices[faces[:,0]])
    normals/=np.linalg.norm(normals,axis=1)[:,None]
    normal=normals[face]
    np.savez_compressed(OUT/'bakes/uv-surface.npz',occupied=occupied,face=face,bary=weights,position=position,normal=normal,part=part_ids[face])
    rear=np.zeros((SIZE,SIZE),bool);rear[occupied]=(part_ids[face]==0)&(normal[:,1]>.25)
    rear_distance=distance_transform_edt(~rear)
    rear_support=rear_distance<=8
    for name in ['ao','geometry-masks']:
        front=read(OUT/'bakes'/f'{name}.png');back=read(OUT/'bakes'/f'{name}-rear.png')
        front[rear_support]=back[rear_support]
        save(OUT/'bakes'/f'{name}.png',front)
    geometry=read(OUT/'bakes/geometry-masks.png')
    ao=read(OUT/'bakes/ao.png')[...,0]
    enamel=geometry[...,0][occupied]
    convex=geometry[...,1][occupied];concave=geometry[...,2][occupied]
    for label,channel in [('enamel-id',geometry[...,0]),('brass-id',1-geometry[...,0]),
                          ('curvature-convex',geometry[...,1]),('curvature-concave',geometry[...,2])]:
        save(OUT/'bakes'/f'{label}.png',pad(channel,occupied))
    # Atlas faces may be reordered by xatlas. Match by original vertex identity,
    # then align each atlas triangle's corners to each frozen low triangle.
    atlas=np.load(OUT/'paint/atlas.npz')
    distance,original=cKDTree(vertices).query(atlas['vertices'])
    assert distance.max()<1e-10,float(distance.max())
    source_faces=original[atlas['faces']]
    lookup={tuple(sorted(f)):i for i,f in enumerate(source_faces)}
    paint_uv=np.empty((len(faces),3,2))
    for i,tri in enumerate(faces):
        j=lookup[tuple(sorted(tri))]
        for k,vi in enumerate(tri):
            corner=int(np.flatnonzero(source_faces[j]==vi)[0])
            paint_uv[i,k]=atlas['uv'][atlas['faces'][j,corner]]
    puv=np.einsum('ni,nij->nj',weights,paint_uv[face])
    paint=linear(sample(atlas['texture'],puv*[SIZE,-SIZE]+[-.5,SIZE-.5]))
    paint_full=np.zeros((SIZE,SIZE,3),np.float32);paint_full[occupied]=srgb(paint)
    save(OUT/'paint/transferred-game-uv-colour.png',pad(paint_full,occupied))
    # Fit the projected enamel outline to the photographed blue ellipse. The
    # fitted mesh itself is immutable; only the image's camera mapping changes.
    features=json.loads((FIT/'features.json').read_text())
    center=np.array(features['star_center_mm'])/1000
    rim=np.array(next(x['points_mm'] for x in features['features'] if x['name']=='rim_step_0'))/1000
    radius=float(np.median(np.linalg.norm(rim[:,[0,2]]-center,axis=1)))
    points=(position[:,[0,2]]-center)/radius
    points[:,1]*=-1
    records={}; projection_colours={}
    for state,views in REFS.items():
        records[state]={};projected=[]
        for view,path in views.items():
            maps,c,m,report=photo_data(path)
            # Symmetric square root of the ellipse is the foreshortening/roll
            # registration for an orthographic camera. Side surfaces additionally
            # project depth at the inferred oblique azimuth.
            coords=points@m.T+c
            if view=='oblique':
                ratio=np.linalg.eigvalsh(m).min()/np.linalg.eigvalsh(m).max()
                angle=float(np.arccos(np.clip(ratio,0,1)))
                coords[:,0]+=(-position[:,1])*np.sin(angle)*np.linalg.eigvalsh(m).max()/radius
                report['inferred_azimuth_degrees']=float(np.degrees(angle))
            colours=[sample(image,coords) for image in maps]
            projected.append(colours[0]*(1-enamel[:,None])+colours[1]*enamel[:,None])
            records[state][view]=report
        side=np.clip((np.abs(normal[:,0])+.4*np.abs(normal[:,2])-.15)/.75,0,1)
        side=np.where(part_ids[face]!=0, .6, side)
        colour=projected[0]*(1-side[:,None])+projected[1]*side[:,None]
        projection_colours[state]=colour
        image=np.zeros((SIZE,SIZE,3),np.float32);image[occupied]=srgb(colour)
        save(OUT/'projection'/f'{state}-projected-game-uv.png',pad(image,occupied))
    # Match only per-material colour statistics for A, preserving Paint's spatial
    # detail. The present/remembered oxide and dust colours come from the photos.
    wear=convex
    recess=np.clip(.65*concave+.6*(1-ao[occupied]),0,1)
    outputs={}
    for route in ['A','B']:
        outputs[route]={}
        for state in ['remembered','present']:
            source=paint.copy() if route=='A' else projection_colours[state].copy()
            if route=='A':
                for mask in [enamel<.5,enamel>=.5]:
                    # Constrain generated colour to its geometry-owned material.
                    # Ratios preserve image variation while correcting material
                    # swaps from generative painting, never replacing geometry.
                    target=np.median(projection_colours[state][mask],axis=0)
                    original_median=np.median(source[mask],axis=0)
                    source[mask]*=target/np.maximum(original_median,.005)
            lum=source@np.array([.2126,.7152,.0722])
            detail=np.zeros_like(lum)
            for mask in [enamel<.5,enamel>=.5]:
                median=np.median(lum[mask]); lo,hi=np.quantile(lum[mask],[.1,.9])
                detail[mask]=np.clip((lum[mask]-median)/max(hi-lo,.005),-1,1)
            brass=1-enamel
            if state=='remembered':
                rough=(.29-.07*wear+.06*recess-.045*detail)*brass+(.15-.025*detail)*enamel
                metallic=.98*brass
                colour=source*(1-.08*recess[:,None]*brass[:,None])
                oxide=np.zeros_like(brass);dust=np.zeros_like(brass)
            else:
                oxide=np.clip((.22+.62*recess-.23*wear-.12*detail)*brass,0,.82)
                dust=np.clip((.10*recess+.045*np.maximum(-detail,0))*(1-.7*wear),0,.18)
                # Dry oxide and dust tints are sampled from same-state photographs.
                dark=projection_colours[state][(brass>.5)&(detail<0)]
                oxide_colour=np.median(dark,axis=0)
                dust_colour=np.quantile(projection_colours[state][enamel>.5],.85,axis=0)
                colour=source*(1-.22*oxide[:,None])
                colour=colour*(1-.20*oxide[:,None])+oxide_colour*.20*oxide[:,None]
                colour=colour*(1-dust[:,None])+dust_colour*dust[:,None]
                rough=(.43+.18*oxide+.08*recess-.065*wear-.035*detail)*brass+(.22+.22*dust-.02*detail)*enamel
                metallic=np.clip(.94-.54*oxide-.55*dust,0,1)*brass
            folder=OUT/route/state;folder.mkdir(parents=True,exist_ok=True)
            maps={'basecolor':srgb(colour),'roughness':np.clip(rough,.08,.8),
                  'metallic':metallic,'oxide-mask':oxide,'dust-mask':dust,
                  'orm':np.stack([ao[occupied],np.clip(rough,.08,.8),metallic],axis=-1)}
            outputs[route][state]={}
            for name,values in maps.items():
                full=np.zeros((SIZE,SIZE)+values.shape[1:],np.float32);full[occupied]=values
                path=folder/(name+'.png');save(path,pad(full,occupied))
                outputs[route][state][name]=str(path)
            outputs[route][state]['normal']=str(OUT/'bakes/normal.png')
            outputs[route][state]['ao']=str(OUT/'bakes/ao.png')
    (OUT/'projection/settings.json').write_text(json.dumps({'photos':records,'mesh_enamel_radius_m':radius,
         'mesh_face_center_xz_m':center.tolist(),'projection':'front ellipse registration for face, depth-aware oblique for side/rim; normal-weighted blend; per-material same-class nearest sampling',
         'rear_and_unseen_hardware':'No rear photograph supplied. Continue nearest observed brass of the front/oblique images, with no fabricated markings.',
         'side_weight':'clamp((abs(nx) + .4 abs(nz) - .15)/.75); hardware=.6',
         'atlas_transfer_max_vertex_distance_m':float(distance.max()),
         'atlas_transfer':'Exact original-triangle identity plus barycentric atlas UV sampling; no geometry replacement',
         'uv_occupied_pixels':int(occupied.sum()),'outputs':outputs,
         'surface_policy':'All colour and fine variation from images. AO and signed curvature are masks only. No procedural noise.',
         'states':'Remembered as issued. Present after 1000 years dry sealed sterile oxygenated storage, brown oxide and fine dust, intact enamel; no green corrosion or wet streaks.',
    },indent=2))
    (OUT/'textures.json').write_text(json.dumps(outputs,indent=2))
    print('COLOURS_COMPLETE',flush=True)

if __name__=='__main__':
    main()
