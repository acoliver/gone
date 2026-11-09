from pathlib import Path
import json
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
R=Path(__file__).resolve().parent
ROOT=R.parents[2]
p=np.load(R/'position.npy')[:,:,:3]-np.array([.55,.11,.1])
n=np.load(R/'surface_normals.npy')[:,:,:3]*2-1
x,y,z=np.moveaxis(p,-1,0)
paint=np.flipud(np.asarray(Image.open(R/'720_paint_rebake.png').convert('RGB'))/255.)
scans={}
for name in ['steel','oxide']:
 scans[name]=np.asarray(Image.open(ROOT/f'assets/props/hatch/hatch_detail_{name}_albedo.png').convert('RGB'))/255.
# Match the hatch's physical scan sampling, with orientation set by the fitted surface.
axis=np.argmax(np.abs(n),axis=-1)
u=np.where(axis==0,y,x);v=np.where(axis==2,y,z)
u=u/.20+.177;v=v/.20+.397
samples={}
for name,a in scans.items():
 h,w=a.shape[:2];samples[name]=a[np.floor(v*h).astype(int)%h,np.floor(u*w).astype(int)%w]
steel=samples['steel'];oxide=samples['oxide']
luma=lambda a:a@np.array([.2126,.7152,.0722])
sl=luma(steel);sl=sl/max(float(np.median(sl)),.02)
pl=luma(paint);pl=gaussian_filter(pl,1.5);pl=np.clip(pl/max(float(np.median(pl[pl>.01])),.02),.8,1.15)
# The painter's broad tone is retained weakly, without its red/dark rust islands.
base=np.array([.355,.383,.275])[None,None,:]*(.92+.08*pl[:,:,None])*(.86+.14*np.clip(sl[:,:,None],.3,1.8))
# Millimetre-scale edge masks choose photographed oxide and exposed steel, never raised rust.
edge_dist=np.minimum(np.minimum(abs(abs(x)-.55),abs(abs(y)-.109)),abs(z+.1))
edge=np.exp(-np.maximum(edge_dist,0)/.0015)
oxide_l=luma(oxide);grain=np.clip(oxide_l/max(float(np.median(oxide_l)),.02),.2,2)
fleck=np.clip((grain-.72)*1.8,0,1)
rust=np.clip(edge*.68*(.25+.75*fleck),0,.8)
# Four end fasteners supply narrow gravity-aligned streaks down the generated end faces.
streak=np.zeros_like(x)
for xx in [-.545,.545]:
 for yy in [-.065,.065]:
  drop=-.052-z
  run=np.exp(-((y-yy+.0003*np.sin(z*170))/.0012)**2)
  run*=np.clip(1-drop/.029,0,1)*(drop>=0)*np.exp(-abs(x-xx)/.0035)
  streak=np.maximum(streak,run)
# Selected rail fasteners collect short, narrow oxide tails on the underside.
for xx in [-.46,-.10,.28]:
 dy=y+.044
 run=np.exp(-((x-xx)/.0010)**2)*np.exp(-np.maximum(dy,0)/.009)*(dy>=0)*np.exp(-abs(z+.1)/.002)
 streak=np.maximum(streak,run*.65)
rust=np.maximum(rust,streak*.82)
oxide_tone=np.array([.29,.157,.074])[None,None,:]*(.76+.24*np.clip(grain[:,:,None],.25,1.6))
colour=base*(1-rust[:,:,None])+oxide_tone*rust[:,:,None]
wear=edge*np.clip((sl-1.0)*1.8,0,.55)*(1-rust)
exposed=np.mean(steel,axis=-1)[:,:,None]*np.array([1.02,1.04,.96])[None,None,:]
exposed=np.clip(exposed,.21,.51)
colour=colour*(1-wear[:,:,None])+exposed*wear[:,:,None]
rough=np.clip(.72+.12*rust+.07*(1-np.clip(sl,0,1)),.6,.9)
metal=np.clip(.38*(1-rust)+.25*wear,0,1)
orm=np.stack([np.ones_like(rough),rough,metal],axis=-1)
for name,a in [('olive_weathered_albedo',colour),('olive_unweathered_control',base),('olive_orm',orm),('rust_mask',np.repeat(rust[:,:,None],3,axis=2))]:
 Image.fromarray((np.flipud(np.clip(a,0,1))*255).astype('uint8')).save(R/(name+'.png'))
valid=np.linalg.norm(n,axis=-1)>.8
ed=valid&(edge_dist<.003);broad=valid&(edge_dist>.012)
info={'material_sources':['hatch_detail_steel_albedo.png','hatch_detail_oxide_albedo.png','720_paint_rebake.png'],'rust_is_albedo_only':True,'generated_normal_strength':.14,'edge_width_m':.0015,'end_streak_half_width_m':.0012,'end_streak_length_m':.029,'edge_rust_mean':float(np.mean(rust[ed])),'broad_face_rust_mean':float(np.mean(rust[broad])),'edge_to_broad_rust_ratio':float(np.mean(rust[ed])/max(np.mean(rust[broad]),1e-9)),'weather_albedo_mean_absolute_difference':float(np.abs(colour-base)[valid].mean())}
(R/'weather-stats.json').write_text(json.dumps(info,indent=2));print(json.dumps(info,indent=2))
