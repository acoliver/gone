from pathlib import Path
import json,numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
R=Path(__file__).resolve().parent;rng=np.random.default_rng(72004)
b=json.loads((R/'build-stats.json').read_text());SLOTS=np.linspace(-.455,.455,14);stats={}
def save(name,a):Image.fromarray((np.flipud(np.clip(a,0,1))*255).astype('uint8')).save(R/(name+'.png'))
for prefix in ['body','grille','hardware']:
 p=np.load(R/(prefix+'_position.npy'))[:,:,:3]-[.55,.11,.1];n=np.load(R/(prefix+'_normals.npy'))[:,:,:3]*2-1;x,y,z=np.moveaxis(p,-1,0)
 valid=(np.linalg.norm(n,axis=-1)>.7)&(np.linalg.norm(n,axis=-1)<1.2)
 # Non-repeating continuous world-coordinate fields, with three non-aligned
 # frequencies. Physical masks carry the large features, not atlas pixels.
 field=(np.sin(x*173+y*411+np.sin(z*313))*np.cos(y*237-z*391)+np.sin(x*359-z*563+y*197)*.45)/1.45
 grain=(gaussian_filter(rng.random(x.shape),.65)-.5)*.07
 edge=np.maximum(np.exp(-abs(z+.098)/.008),np.exp(-abs(abs(x)-.527)/.016))
 seam=np.exp(-abs(abs(y)-.057)/.015)*(abs(x)<.513)*(z<-.065)
 side=np.clip((abs(n[:,:,0])+abs(n[:,:,1])-.3)*1.8,0,1)
 streak=np.zeros_like(x)
 for stud in b['side_fasteners']:
  drop=stud['z']-z;width=.0042+.0016*np.clip(drop/.048,0,1)
  centre=stud['x']+.0011*np.sin(drop*90)
  line=np.exp(-((x-centre)/width)**2)*np.clip(1-drop/.052,0,1)*(drop>=0)*np.exp(-abs(y-stud['y'])/.012)*side
  streak=np.maximum(streak,line)
 # Channel rivets bleed onto the receiving shoulders as well as down the
 # side faces. Keep a sustained tail before tapering at the lower lip;
 # linear fading from the origin erased these tails at the viewed underside.
 for xc in [-.46,-.28,-.10,.10,.28,.46]:
  drop=-.045-z
  width=.0042+.0016*np.clip(drop/.052,0,1)
  line=np.exp(-((x-xc-.001*np.sin(z*180))/width)**2)
  line*=np.clip((.065-drop)/.012,0,1)*(drop>=0)
  shoulder=np.clip((abs(y)-.048)/.009,0,1)*np.clip((.112-abs(y))/.006,0,1)
  streak=np.maximum(streak,.98*line*shoulder)
 if prefix=='body':
  base=np.broadcast_to(np.array([.355,.383,.275]),(*x.shape,3)).copy()*(1+grain[:,:,None])
  chip=edge*np.clip((field+.42)*2.2,0,1)
  rust=np.clip(.92*chip+.54*seam+.018,0,.96)
  soot=np.clip(.88*seam+.45*np.exp(-abs(z+.084)/.022)*(abs(x)<.50),0,.92)
  wear=np.clip(chip*.35,0,.5)
  dust=np.clip(.76*np.exp(-abs(z+.013)/.024)*(.7+.3*np.clip(n[:,:,2]+.5,0,1))+.45*edge*(1-chip),0,.85)
 elif prefix=='grille':
  base=np.broadcast_to(np.array([.145,.157,.123]),(*x.shape,3)).copy()
  ds=np.min(abs(x[:,:,None]-SLOTS),axis=-1);lip=np.exp(-abs(ds-.018)/.006)
  edge=np.maximum(lip,np.exp(-abs(abs(y)-.0465)/.004))
  rust=np.clip(.64*edge*np.clip(field+.8,0,1)+.025,0,.85)
  soot=np.clip(.68+.26*lip+.13*field,0,.96)
  wear=.32*edge*np.clip(field+.2,0,1);dust=.45*np.exp(-abs(abs(y)-.045)/.007)*(1-wear)
 else:
  base=np.broadcast_to(np.array([.205,.225,.166]),(*x.shape,3)).copy()
  rail_edge=np.maximum(np.exp(-abs(abs(y)-.0475)/.0035),np.exp(-abs(abs(y)-.0404)/.0035))*(abs(x)<.494)
  cap_edge=np.maximum(np.exp(-abs(abs(y)-.108)/.006),np.exp(-abs(z+.096)/.006))*(abs(x)>.51)
  edge=np.maximum(rail_edge,cap_edge)
  heads=np.zeros_like(x)
  for xx in [-.46,-.28,-.10,.10,.28,.46]:
   for yy in [-.044,.044]:heads=np.maximum(heads,np.exp(-(((x-xx)/.008)**2+((y-yy)/.008)**2)))
  rust=np.clip(.70*edge*np.clip(field+.8,0,1)+.72*heads+.025,0,.96)
  soot=np.clip(.40+.35*heads+.15*np.sin(x*31)**2,0,.86)
  wear=.68*edge*np.clip(field+.65,0,1);dust=.60*edge*(1-wear)
 oxide=np.array([.245,.075,.021])*(1+grain[:,:,None]);metal=np.array([.105,.112,.088]);dust_colour=np.array([.66,.625,.49])
 def colour(r,st):
  r=np.maximum(r,st*.97);c=base*(1-r[:,:,None])+oxide*r[:,:,None]
  c=c*(1-soot[:,:,None])+np.array([.009,.012,.007])*soot[:,:,None]
  c=c*(1-wear[:,:,None])+metal*wear[:,:,None]
  return c*(1-dust[:,:,None])+dust_colour*dust[:,:,None]
 final=colour(rust,streak);norust=colour(np.zeros_like(x),np.zeros_like(x));nostreak=colour(rust,np.zeros_like(x))
 rough=np.clip(.73+.17*soot+.09*rust-.26*wear,.43,.98);metallic=np.clip(.4*(1-rust)*(1-soot)*(1-dust)+.5*wear,.02,.8)
 broad=(edge<.1)&(seam<.1)&(streak<.05)
 mask=np.stack([(edge>.3).astype(float),(broad).astype(float),(streak>.2).astype(float)],-1)*valid[:,:,None]
 for name,a in [('albedo',final),('no_rust',norust),('no_streak',nostreak),('control',base),('orm',np.stack([np.ones_like(x),rough,metallic],-1)),('control_orm',np.stack([np.ones_like(x),np.full_like(x,.70),np.full_like(x,.48)],-1)),('rust',np.repeat(np.maximum(rust,streak*.97)[:,:,None],3,-1)),('soot',np.repeat(soot[:,:,None],3,-1)),('zones',mask)]:save(prefix+'_'+name,a)
 stats[prefix]={'albedo_mean_abs_effect':float(np.abs(final-base)[valid].mean()),'edge_rust_mean':float(rust[valid&(edge>.3)].mean()),'broad_rust_mean':float(rust[valid&broad].mean()),'olive_paint_fraction_rust_below_0p25':float((rust[valid]<.25).mean()),'metal_weather_is_texture_only':True}
 stats[prefix]['edge_to_broad_rust_ratio']=stats[prefix]['edge_rust_mean']/max(stats[prefix]['broad_rust_mean'],1e-8)
 # Detect discontinuities at a fixed 16-pixel grid versus other pixels. Texture
 # atlases have seams, so this is reported with lit-image autocorrelation too.
 grad=np.abs(np.diff(final,axis=1)).mean(-1);grid=np.arange(grad.shape[1])%16==0
 stats[prefix]['atlas_16px_grid_gradient_ratio']=float(grad[:,grid].mean()/max(grad[:,~grid].mean(),1e-8))
w,h=2048,256;xx=np.linspace(-.485,.485,w)[None,:];yy=np.linspace(-.042,.042,h)[:,None]
index=np.argmin(abs(xx[:,:,None]-SLOTS),axis=-1);gains=np.array([.81,.96,.85,.12,.10,.14,.94,.77,.99,.82,.95,.73,.91,.79])
tints=np.array([[1,.77,.39] if i<7 else [.51,.77,1] for i in range(14)])
bright=np.broadcast_to(gains[index],(h,w)).copy();shadow=np.ones((h,w))
for i,xc in enumerate(SLOTS):
 cy=rng.uniform(-.027,.027);width=rng.uniform(.003,.010)
 shadow*=1-rng.uniform(.40,.88)*np.exp(-((xx-xc-rng.uniform(-.010,.010))/width)**2-((yy-cy)/rng.uniform(.010,.023))**2)
for _ in range(30):
 cx=rng.uniform(-.48,.48);cy=rng.uniform(-.04,.04)
 shadow*=1-rng.uniform(.3,.85)*np.exp(-((xx-cx)/rng.uniform(.0005,.002))**2-((yy-cy)/rng.uniform(.002,.007))**2)
bright*=shadow*(.94+.06*np.cos(yy*37));emission=bright[:,:,None]*tints[index]
save('glass_emission',emission)
means=[]
for i,xc in enumerate(SLOTS):
 mask=(abs(xx[0]-xc)<.016)
 rgb=emission[:,mask].mean((0,1));linear=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
 means.append({'slot':i+1,'x_m':float(xc),'emission_rgb_srgb_mean':rgb.tolist(),'relative_luminance_linear':float(linear@[.2126,.7152,.0722])})
failed=np.mean([m['relative_luminance_linear'] for m in means[3:6]]);healthy=np.mean([m['relative_luminance_linear'] for m in means[:3]+means[6:]])
stats.update({'glass_slots':means,'failed_section_slot_numbers':[4,5,6],'failed_section_length_m':.21,'failed_section_fraction_of_tube':.21/.97,'failed_section_linear_luminance_reduction':float(1-failed/healthy),'side_streak_length_m':.052,'channel_shoulder_streak_length_m':.065,'streak_gaussian_halfwidth_m':[.0042,.0058],'streak_fwhm_m':[.0042*2*np.sqrt(np.log(2)),.0058*2*np.sqrt(np.log(2))],'gravity_blender':[0,0,-1],'texture_resolution_px':[1024,1024],'glass_resolution_px':[2048,256],'texture_repeat':False,'field_method':'Continuous world-coordinate non-aligned frequencies and feature masks; no repeated image tiles','rust_is_albedo_and_orm_only':True})
(R/'weather-stats.json').write_text(json.dumps(stats,indent=2));print(json.dumps(stats,indent=2))
