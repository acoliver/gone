from pathlib import Path
import json
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
R=Path(__file__).resolve().parent
rng=np.random.default_rng(72003)
b=json.loads((R/'build-stats.json').read_text())
SLOTS=np.linspace(-.455,.455,14)
allstats={}

def save(name,a):
 Image.fromarray((np.flipud(np.clip(a,0,1))*255).astype('uint8')).save(R/(name+'.png'))

for prefix in ['body','grille','hardware']:
 p=np.load(R/(prefix+'_position.npy'))[:,:,:3]-[.55,.11,.1]
 n=np.load(R/(prefix+'_normals.npy'))[:,:,:3]*2-1
 x,y,z=np.moveaxis(p,-1,0)
 valid=(np.linalg.norm(n,axis=-1)>.7)&(np.linalg.norm(n,axis=-1)<1.2)
 grain=gaussian_filter(rng.random(x.shape),.7)
 grain=(grain-grain.mean())*.06
 if prefix=='body':
  base=np.broadcast_to(np.array([.355,.383,.275]),(*x.shape,3)).copy()
  base*=1+grain[:,:,None]
  side=np.clip((abs(n[:,:,0])+abs(n[:,:,1])-.35)*1.7,0,1)
  bottom=np.clip((-n[:,:,2]-.3)*1.6,0,1)
  edge=np.maximum(np.exp(-abs(z+.098)/.0028)*side,np.exp(-abs(abs(x)-.548)/.0025)*side)
  channel=np.minimum(abs(abs(y)-.057),abs(abs(x)-.506))
  in_channel=(abs(x)<.514)&(abs(y)<.064)&(z<-.073)
  grime=np.exp(-channel/.0045)*in_channel
  rust=np.clip(edge*.70+np.exp(-channel/.0018)*in_channel*.38,0,.85)
  streak=np.zeros_like(x)
  # Long side streaks descend in Z from the four actual mounted fasteners.
  for stud in b['side_fasteners']:
   drop=stud['z']-z
   width=.0015+.00045*np.clip(drop/.035,0,1)
   line=np.exp(-((x-stud['x']-.00035*np.sin(drop*130))/width)**2)
   line*=np.clip(1-drop/.042,0,1)*(drop>=0)*np.exp(-abs(y-stud['y'])/.008)*side
   streak=np.maximum(streak,line)
  for xx in [-.545,.545]:
   for yy in [-.065,.065]:
    drop=-.052-z
    line=np.exp(-((y-yy)/.0016)**2)*np.clip(1-drop/.034,0,1)*(drop>=0)*np.exp(-abs(x-xx)/.005)*side
    streak=np.maximum(streak,line)
  rust=np.maximum(rust,.88*streak)
  wear=edge*.22*(.9+grain)
  soot=np.clip(grime*.80,0,.82)
  edge_zone=valid&(edge>.25)
  broad=valid&(edge<.01)&(~in_channel)&(streak<.001)
  allstats['edge_rust_mean']=float(rust[edge_zone].mean())
  allstats['broad_face_rust_mean']=float(rust[broad].mean())
  allstats['edge_to_broad_rust_ratio']=float(rust[edge_zone].mean()/max(rust[broad].mean(),1e-9))
 elif prefix=='grille':
  base=np.broadcast_to(np.array([.145,.157,.123]),(*x.shape,3)).copy()
  ds=np.min(abs(x[:,:,None]-SLOTS),axis=-1)
  lip=np.exp(-abs(ds-.018)/.0022)*(abs(y)<.035)
  corners=np.exp(-((abs(ds-.018)/.005)**2+(abs(abs(y)-.032)/.006)**2))
  edge=np.maximum(lip,np.exp(-abs(abs(y)-.0465)/.0012))
  soot=np.clip(.45*lip+.68*corners+.17*np.exp(-abs(abs(y)-.038)/.005),0,.90)
  rust=.30*edge*np.exp(-abs(z+.099)/.003)
  wear=.18*lip*(1-soot)
 else:
  base=np.broadcast_to(np.array([.205,.225,.166]),(*x.shape,3)).copy()
  edge=np.maximum(np.exp(-abs(abs(y)-.0475)/.0010),np.exp(-abs(abs(y)-.0404)/.0010))*(abs(x)<.494)
  heads=np.zeros_like(x)
  for xx in [-.46,-.28,-.10,.10,.28,.46]:
   for yy in [-.044,.044]:
    heads=np.maximum(heads,np.exp(-(((x-xx)/.0035)**2+((y-yy)/.0035)**2)))
  soot=.42*heads+.30*np.exp(-abs(z+.091)/.0012)
  rust=np.clip(.42*heads+.28*edge,0,.65)
  wear=edge*.60*(.8+.2*np.sin(x*53)**2)
 oxide=np.array([.285,.124,.047])[None,None,:]*(1+grain[:,:,None])
 colour=base*(1-rust[:,:,None])+oxide*rust[:,:,None]
 colour=colour*(1-soot[:,:,None])+np.array([.020,.023,.017])*soot[:,:,None]
 colour=colour*(1-wear[:,:,None])+np.array([.42,.40,.32])*wear[:,:,None]
 rough=np.clip(.70+.18*soot+.12*rust-.18*wear,.48,.95)
 metallic=np.clip(.48*(1-rust)*(1-soot)+.28*wear,.04,.78)
 for name,a in [('albedo',colour),('control',base),('orm',np.stack([np.ones_like(x),rough,metallic],-1)),('control_orm',np.stack([np.ones_like(x),np.full_like(x,.70),np.full_like(x,.48)],-1)),('rust',np.repeat(rust[:,:,None],3,axis=-1)),('soot',np.repeat(soot[:,:,None],3,axis=-1))]:save(prefix+'_'+name,a)
 allstats[prefix]={'albedo_mean_abs_effect':float(np.abs(colour-base)[valid].mean()),'rust_fraction_above_0p1':float((rust[valid]>.1).mean()),'soot_fraction_above_0p1':float((soot[valid]>.1).mean()),'metal_weather_is_texture_only':True}
# Uneven frosted glass uses a non-repeating image, with end darkening and small
# dust flecks. Brightness envelope is measured separately from isolated specks.
w,h=1024,128
u=np.linspace(-1,1,w)[None,:]
v=np.linspace(-1,1,h)[:,None]
envelope=.985-.22*abs(u)**1.6+.020*np.sin(u*7.2)+.012*np.sin(u*17.5+.4)
envelope=np.broadcast_to(envelope,(h,w)).copy()
envelope*=.984+.016*np.cos(v*2)
frost=gaussian_filter(rng.random((h,w)),1.5)
brightness=envelope*(.974+.052*frost)
dust=np.ones((h,w))
for _ in range(190):
 cx=rng.integers(0,w);cy=rng.integers(0,h);r=rng.uniform(.45,1.25)
 yy,xx=np.ogrid[:h,:w]
 dust*=1-rng.uniform(.23,.53)*np.exp(-((xx-cx)**2+(yy-cy)**2)/(2*r*r))
brightness*=dust
save('glass_emission',brightness[:,:,None]*np.array([.87,.84,.71])[None,None,:])
# Image UVs use increasing V upwards; the save helper flips arrays accordingly.
centre=float(np.mean(envelope[:,450:574]));ends=float(np.mean(envelope[:,np.r_[0:70,954:1024]]))
allstats.update({'glass_brightness_envelope_min':float(envelope.min()),'glass_brightness_envelope_max':float(envelope.max()),'glass_length_brightness_variation_fraction':float((envelope.max()-envelope.min())/envelope.max()),'glass_end_to_centre_brightness_ratio':ends/centre,'glass_dust_specks':190,'gravity_blender':[0,0,-1],'side_streak_length_m':.042,'side_streak_half_width_m':[.0015,.00195],'rust_tone_variation_fraction':.06,'texture_resolution_px':[1024,1024],'generated_normal_strength':0,'rust_is_albedo_and_orm_only':True})
assert .15<=allstats['glass_length_brightness_variation_fraction']<=.30
(R/'weather-stats.json').write_text(json.dumps(allstats,indent=2))
print(json.dumps(allstats,indent=2))
