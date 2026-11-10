from pathlib import Path
import json, numpy as np
from scipy.spatial import cKDTree
from scipy.ndimage import map_coordinates, distance_transform_edt, label, find_objects
from PIL import Image
O=Path(__file__).resolve().parent;OLD=O.parent/'finish3';N=2048
coverage=np.array(Image.open(O/'uv-coverage.png').convert('L'))[::-1]>250
positions=np.load(O/'surface-position.npy')[:,:,:3]*1.6-np.array([.6,.8,.01]);normals=np.load(O/'surface-normal.npy')[:,:,:3]*2-1
points=positions[coverage];norm=normals[coverage];ao=np.asarray(Image.open(O/'console-ao.png').convert('L'),dtype=np.float32)[::-1][coverage]/255
features=np.load(O/'convex-features.npy');dist=cKDTree(features).query(points,workers=4)[0]
def load(name):return np.asarray(Image.open(OLD/name).convert('RGB'),dtype=np.float32)[::-1][coverage]/255
source=load('hunyuan-albedo.png');previous=load('console-albedo.png');oldorm=load('console-orm.png')
def sat(a):return (a.max(1)-a.min(1))/np.maximum(a.max(1),.001)
def linear(a):return np.where(a<=.04045,a/12.92,((a+.055)/1.055)**2.4)
def srgb(a):return np.where(a<=.0031308,a*12.92,1.055*np.maximum(a,0)**(1/2.4)-.055)
def lab(a):
 xyz=linear(a)@np.array([[.4124564,.2126729,.0193339],[.3575761,.7151522,.1191920],[.1804375,.0721750,.9503041]])/np.array([.95047,1,1.08883]);f=np.where(xyz>.008856,xyz**(1/3),7.787*xyz+16/116)
 return np.stack([116*f[:,1]-16,500*(f[:,0]-f[:,1]),200*(f[:,1]-f[:,2])],axis=1)
good=(norm[:,1]<-.2)&(oldorm[:,2]<.03)&(oldorm[:,0]>.9)&(sat(previous)>.2)&(previous[:,1]>previous[:,0])
median=np.median(previous[good],axis=0)
sourcegood=(norm[:,1]<-.2)&(sat(source)>.2)&(source[:,1]>source[:,0])&(source.max(1)<.8)
sourcemedian=np.median(source[sourcegood],axis=0)
light=(source.max(1)+source.min(1))/2
pale=(sat(source)<.18)&(light>.52)
delta=np.linalg.norm(lab(source)-lab(sourcemedian[None,:]),axis=1)
unseen=(norm[:,1]>-.2);recolour=unseen&(pale|(delta>25))
right=(points[:,0]>.35)&(points[:,1]<-.45)&(points[:,2]>.50)&(points[:,2]<.72)
print('PALETTE',median*255,'SOURCE',sourcemedian*255,'UNSEEN_RECOLOUR',int(recolour.sum()),'RIGHT_PALE',int((right&pale).sum()),flush=True)
rng=np.random.default_rng(491)
def noise(scale,seed):
 coords=(points+np.array([.65,.85,.05]))*scale+2
 shape=np.ceil(coords.max(0)+3).astype(int);lattice=np.random.default_rng(seed).random(tuple(shape),dtype=np.float32)
 return map_coordinates(lattice,coords.T,order=3,mode='nearest',prefilter=True)
n40=noise(40,491);n150=noise(150,819);field=.25*n40+.75*n150
# Thin curvature band restricts chips to physical convex edges, not UV island borders.
band=dist<.004
threshold=float(np.quantile(field[band],.80));chip=band&(field>threshold)
# Do not reintroduce the right-contact silver blob after correcting its source colour.
contact=(points[:,1]<-.46)&(points[:,2]>.615)&(points[:,2]<.705)
chip&=~contact
steelthreshold=float(np.quantile(field[chip],.9));steel=chip&(field>=steelthreshold)
# Continuous world-space mottling is identical on roof, sides, back and front.
mottle=noise(11,713);fine=noise(75,912);paint=linear(median)[None,:]*(.90+.20*mottle[:,None])*(.97+.06*fine[:,None])
under=linear(np.array([46,49,39])/255);bare=linear(np.array([108,109,102])/255)
color=paint.copy();color[chip]=under;color[steel]=bare
strength=np.where(contact,.12,.18);darkening=strength*(1-ao);color*=1-darkening[:,None]
rough=np.clip(.65+.07*(mottle-.5),0,1);rough[chip]=.72;rough[steel]=.43
metal=np.zeros(len(points),np.float32);metal[steel]=1
occlusion=ao.copy();occlusion[contact]=.88+.12*ao[contact]
orm=np.stack([occlusion,rough,metal],axis=1)
# Fill only UV padding from the nearest covered surface; colour decisions stay in world space.
nearest=distance_transform_edt(~coverage,return_distances=False,return_indices=True)
def save(name,values):
 a=np.zeros((N,N,3),np.float32)
 if values.ndim==1:values=np.repeat(values[:,None],3,axis=1)
 a[coverage]=values;a[~coverage]=a[nearest[0][~coverage],nearest[1][~coverage]]
 Image.fromarray(np.uint8(np.clip(a[::-1],0,1)*255+.5)).save(O/name)
save('paint-resolved.png',srgb(color));save('orm-resolved.png',orm);save('chip-mask.png',chip.astype(np.float32));save('convex-edge-mask.png',band.astype(np.float32));save('recoloured-mask.png',recolour.astype(np.float32))
# Measure UV-connected flecks in world units, excluding island fragments at image edges.
mask=np.zeros((N,N),bool);mask[coverage]=chip;labels,count=label(mask)
sizes=[]
for i,region in enumerate(find_objects(labels),1):
 if region is None:continue
 selected=positions[region][labels[region]==i]
 if len(selected)>=2:sizes.append(float(np.linalg.norm(np.ptp(selected,axis=0))*1000))
sizes=np.array(sizes)
report={'paint_median_srgb_255':(median*255).tolist(),'source_front_olive_median_srgb_255':(sourcemedian*255).tolist(),'unseen_texels_tested':int(unseen.sum()),'unseen_off_palette_texels_recoloured':int(recolour.sum()),'right_contact_pale_texels':int((right&pale).sum()),'right_contact_source_max_srgb_255':(source[right].max(0)*255).tolist(),'right_contact_source_p95_srgb_255':(np.percentile(source[right],95,axis=0)*255).tolist(),'object_space_wear':{'convex_angle_degrees':8,'band_width_mm':4,'noise_scales_per_m':[40,150],'noise_weights':[.25,.75],'edge_texels':int(band.sum()),'chip_texels':int(chip.sum()),'edge_chip_coverage':float(chip.sum()/band.sum()),'steel_fraction_of_chips':float(steel.sum()/chip.sum()),'flat_face_chips':int((chip&~band).sum()),'chip_world_diameter_p10_p50_p90_mm':np.percentile(sizes,[10,50,90]).tolist(),'chip_components_measured':len(sizes),'box_projected_textures':0},'contact_shadow':{'max_albedo_darkening':float(darkening[contact].max()),'min_orm_occlusion':float(occlusion[contact].min()),'max_combined_texture_darkening':float((1-(1-darkening[contact])*occlusion[contact]).max()),'chip_texels_in_contact_band':int((chip&contact).sum())}}
(O/'texture-report.json').write_text(json.dumps(report,indent=2));print('TEXTURES_DONE',json.dumps(report),flush=True)
