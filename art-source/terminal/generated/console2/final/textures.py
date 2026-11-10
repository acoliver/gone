from pathlib import Path
import json,numpy as np
from scipy.ndimage import map_coordinates,distance_transform_edt,label
from scipy.spatial import cKDTree
from PIL import Image
O=Path(__file__).resolve().parent;S=O;N=2048
standing=json.loads((O/'geometry-report.json').read_text())['standing'];delta=standing['delta_m'];stretch=standing['lower_body_vertical_scale']
ref=np.asarray(Image.open(O.parent.parent/'room9/ref-console-design.png').convert('RGB'),dtype=float)
r,g,b=ref.transpose(2,0,1);yy,xx=np.indices(r.shape)
# Lit olive paint only: dark screen, brown backdrop, deep shadows and neutral highlights are excluded.
mask=(g-r>=2)&(g>=102)&(g<=174)&(r/g.clip(1)>.80)&(b/g.clip(1)>.50)&(b/g.clip(1)<.80)&(xx>25)&(xx<365)&(yy>20)&(yy<380)
regions,count=label(mask);sizes=np.bincount(regions.ravel());sizes[0]=0;mask&=sizes[regions]>=12
median=np.median(ref[mask],axis=0)/255
Image.fromarray(np.uint8(mask)*255).save(O/'reference-paint-mask.png')
coverage=np.asarray(Image.open(S/'uv-coverage.png').convert('L'))[::-1]>250
positions=np.load(S/'surface-position.npy')[:,:,:3]*1.6-np.array([.6,.8,.01]);normals=np.load(S/'surface-normal.npy')[:,:,:3]*2-1
points=positions[coverage];norm=normals[coverage]
ao=np.asarray(Image.open(S/'console-ao.png').convert('L'),dtype=np.float32)[::-1][coverage]/255
dist=cKDTree(np.load(S/'convex-features.npy')).query(points,workers=4)[0]
def linear(a):return np.where(a<=.04045,a/12.92,((a+.055)/1.055)**2.4)
def srgb(a):return np.where(a<=.0031308,a*12.92,1.055*np.maximum(a,0)**(1/2.4)-.055)
def noise(scale,seed):
 coords=(points+np.array([.65,.85,.05]))*scale+2
 lattice=np.random.default_rng(seed).random(tuple(np.ceil(coords.max(0)+3).astype(int)),dtype=np.float32)
 return map_coordinates(lattice,coords.T,order=3,mode='nearest',prefilter=True)
# A broad field and finer modulation give irregular chips rather than uniform silver flecks.
# A larger second octave modulates local chip size. High frequency detail
# supplies the many tiny chips, while the sparse broad peaks join larger ones.
large=noise(9,491);finechips=noise(145,819)
field=.55*finechips+.30*noise(53,931)+.15*large
field+=.35*np.clip((large-.65)/.35,0,1)**2
band=dist<.004
contact=(points[:,1]<-.46)&(points[:,2]>.615+delta)&(points[:,2]<.705+delta)
eligible=band&~contact;threshold=np.quantile(field[eligible],1-.09*band.sum()/eligible.sum());chip=eligible&(field>threshold)
selector=noise(87,624);steel=chip&(selector>=np.quantile(selector[chip],.95));rust=chip&~steel&(selector<np.quantile(selector[chip],.25));under=chip&~steel&~rust
mottle=noise(11,713);fine=noise(75,912)
color=linear(median)[None,:]*(.90+.20*mottle[:,None])*(.97+.06*fine[:,None])
color*=1-(np.where(contact,.12,.18)*(1-ao))[:,None]
streaks=[];streakmask=np.zeros(len(points),np.float32)
for x,start,length,width,strength,phase in [(-.36,.684,.23,.004,.13,.3),(-.19,.553,.17,.0025,.15,1.4),(.025,.683,.31,.0032,.10,3.3),(.225,.553,.21,.0045,.11,2.2),(.375,.688,.26,.0028,.14,4.5)]:
 start+=delta;length*=stretch
 z=points[:,2];drift=.0023*np.sin(z*42+phase)+.001*np.sin(z*103+phase)
 lateral=np.exp(-((points[:,0]-x-drift)/width)**2)
 fall=np.clip((start-z)/.012,0,1)*np.clip((z-(start-length))/length,0,1)
 broken=np.clip(.6+.25*np.sin(z*71+phase)+.15*np.sin(z*137+phase),0,1)
 w=strength*lateral*fall*broken*(norm[:,1]<-.45)*(points[:,1]<-.35)
 streakmask=np.maximum(streakmask,w);streaks.append({'seam_x_m':x,'start_z_m':start,'length_m':length,'nominal_width_mm':width*2000,'maximum_blend':strength})
color=color*(1-streakmask[:,None])+linear(np.array([96,62,44])/255)*streakmask[:,None]
# Sparse accumulated dust is strongest in sheltered upward-facing areas.
up=np.clip(norm[:,2],0,1)
dust=np.clip(.15*(.20+.80*up)*(.35+.65*(1-ao))*np.clip(.25+.75*noise(17,2031),0,1),0,.15)
gray=color@np.array([.2126,.7152,.0722])
dustcolor=.60*color+.40*gray[:,None]
dustcolor=np.minimum(1,dustcolor*1.22+.006)
color=color*(1-dust[:,None])+dustcolor*dust[:,None]
paintmask=~chip&(streakmask<.005)
# Match the measured paint median after mottling and recess darkening, not before them.
color+=linear(median)-np.median(color[paintmask],axis=0)
color=np.clip(color,0,1)
rustvariation=.90+.2*noise(190,94)
color[under]=linear(np.array([48,49,37])/255)*rustvariation[under,None]
color[rust]=linear(np.array([96,62,44])/255)*rustvariation[rust,None]
color[steel]=linear(np.array([104,103,87])/255)*rustvariation[steel,None]
rough=np.clip(.68+.07*(mottle-.5),0,1);rough[under]=.77;rough[rust]=.84;rough[steel]=.58
metal=np.zeros(len(points),np.float32);metal[steel]=1
occlusion=ao.copy();occlusion[contact]=.88+.12*ao[contact]
orm=np.stack([occlusion,rough,metal],axis=1)
nearest=distance_transform_edt(~coverage,return_distances=False,return_indices=True)
def save(name,values):
 a=np.zeros((N,N,3),np.float32)
 if values.ndim==1:values=np.repeat(values[:,None],3,axis=1)
 a[coverage]=values;a[~coverage]=a[nearest[0][~coverage],nearest[1][~coverage]]
 Image.fromarray(np.uint8(np.clip(a[::-1],0,1)*255+.5)).save(O/name)
save('paint-resolved.png',srgb(color));save('orm-resolved.png',orm);save('chip-mask.png',chip.astype(float));save('paint-mask.png',paintmask.astype(float));save('streak-mask.png',streakmask/.15);save('dust-mask.png',dust/.15)
report={'reference_paint_median_srgb_255':(median*255).tolist(),'reference_selected_pixels':int(mask.sum()),'reference_mask':'reference-paint-mask.png','reference_selection':'Connected lit yellow-green pixels: G 102..174, G-R >=2, R/G >0.80, B/G 0.50..0.80, image interior; connected patches >=12 pixels. Excludes dark screen, brown background, deep shadows and neutral highlights.','resolved_paint_median_srgb_255':(np.median(srgb(color[paintmask]),axis=0)*255).tolist(),'chip_size_noise':{'fine_scale_per_m':145,'middle_scale_per_m':53,'large_scale_per_m':9,'large_octave_peak_boost':.35},'edge_chip_coverage':float(chip.sum()/band.sum()),'steel_fraction_of_chips':float(steel.sum()/chip.sum()),'rust_fraction_of_chips':float(rust.sum()/chip.sum()),'undercoat_fraction_of_chips':float(under.sum()/chip.sum()),'rust_median_srgb_255':(np.median(srgb(color[rust]),axis=0)*255).tolist(),'steel_median_srgb_255':(np.median(srgb(color[steel]),axis=0)*255).tolist(),'streaks':streaks,'streak_affected_texels':int((streakmask>.005).sum()),'resolution':[N,N],'dust':{'maximum_blend':float(dust.max()),'allowed_maximum_blend':.15,'upward_ao_driven':True,'median_blend':float(np.median(dust))}}
(O/'texture-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
