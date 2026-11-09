from pathlib import Path
import json,numpy as np
from PIL import Image
from scipy.spatial import cKDTree
R=Path(__file__).resolve().parent
b=json.loads((R/'build-stats.json').read_text());SLOTS=np.linspace(-.455,.455,14);stats={}
def save(name,a):
 Image.fromarray((np.flipud(np.clip(a,0,1))*255+.5).astype('uint8')).save(R/(name+'.png'))
def noise(p,scale,seed):
 q=p/scale;cell=np.floor(q).astype(np.int64);f=q-cell;f=f*f*(3-2*f);out=np.zeros(p.shape[:-1])
 for i in range(2):
  for j in range(2):
   for k in range(2):
    c=cell+[i,j,k]
    v=(c[...,0]*73856093)^(c[...,1]*19349663)^(c[...,2]*83492791)^seed
    v=(v^(v>>13))*1274126177;v=(v^(v>>16))&0xffffffff
    weight=(f[...,0] if i else 1-f[...,0])*(f[...,1] if j else 1-f[...,1])*(f[...,2] if k else 1-f[...,2])
    out+=weight*(v/4294967295.)
 return out
for prefix in ['body','grille','hardware']:
 p=np.load(R/(prefix+'_position.npy'))[:,:,:3]-[.55,.11,.1];n=np.load(R/(prefix+'_normals.npy'))[:,:,:3]*2-1;x,y,z=np.moveaxis(p,-1,0)
 valid=(np.linalg.norm(n,axis=-1)>.7)&(np.linalg.norm(n,axis=-1)<1.2)
 distance=cKDTree(np.load(R/(prefix+'_sharp_edges.npy'))).query(p.reshape(-1,3),workers=4)[0].reshape(x.shape)
 edge=np.exp(-(distance/.0021)**1.4)
 mottling=noise(p,.012,72005);fine=noise(p,.0018,84371)
 # Irregular paint loss can only occur inside the narrow true-edge band.
 chip=edge*np.clip((.70*mottling+.30*fine-.25)*2.0,0,1)
 near_channel=np.exp(-((abs(y)-.056)/.006)**2)*(z<-.068)*(abs(x)<.507)
 side=np.clip((abs(n[:,:,0])+abs(n[:,:,1])-.3)*1.8,0,1)
 streak=np.zeros_like(x);heads=np.zeros_like(x)
 for stud in b['side_fasteners']:
  drop=stud['z']-z;centre=stud['x']+.00045*(noise(p,.016,329)-.5)
  width=.0014+.0004*np.clip(drop/.047,0,1)
  line=np.exp(-((x-centre)/width)**2)*np.clip((.052-drop)/.018,0,1)*(drop>=0)*np.exp(-abs(y-stud['y'])/.007)*side
  streak=np.maximum(streak,.75*line)
  heads=np.maximum(heads,np.exp(-(((x-stud['x'])/.0045)**2+((z-stud['z'])/.0045)**2))*np.exp(-abs(y-stud['y'])/.006))
 for xx in [-.46,-.28,-.10,.10,.28,.46]:
  for yy in [-.044,.044]:
   heads=np.maximum(heads,np.exp(-(((x-xx)/.0045)**2+((y-yy)/.0045)**2))*np.exp(-abs(z+.099)/.010))
 # Separate receiving-shoulder tails from side-face gravity streaks.
 for xx in [-.46,-.28,-.10,.10,.28,.46]:
  drop=-.045-z
  line=np.exp(-((x-xx)/.0017)**2)*np.clip((.065-drop)/.018,0,1)*(drop>=0)
  shoulder=np.clip((abs(y)-.055)/.006,0,1)*np.clip((.108-abs(y))/.004,0,1)
  streak=np.maximum(streak,.65*line*shoulder)
 if prefix=='body':
  base_colour=np.array([.355,.383,.255]);soot=.50*near_channel
  rust=np.clip(.78*chip+.55*heads+.003,0,.86)
  dust=.14*np.clip(n[:,:,2],0,1)*(.65+.35*noise(p,.039,67))
  age=.055
 elif prefix=='grille':
  base_colour=np.array([.225,.247,.160]);soot=.40*np.exp(-(y/.062)**4)+.14*edge
  rust=np.clip(.67*chip+.003,0,.82);streak*=.15
  dust=.08*np.clip(n[:,:,2],0,1);age=.055
 else:
  base_colour=np.array([.310,.343,.218]);soot=.24*np.exp(-((abs(y)-.046)/.005)**2)*(abs(x)<.498)
  rust=np.clip(.75*chip+.50*heads+.003,0,.86);streak*=.30
  dust=.18*np.clip(n[:,:,2],0,1)*(.65+.35*noise(p,.033,29));age=.055
 base=np.broadcast_to(base_colour,(*x.shape,3)).copy()
 base*=1+.008*(noise(p,.0009,145)-.5)[:,:,None]
 wear=.20*chip
 oxide=np.array([.235,.092,.028]);metal=np.array([.13,.14,.108]);dust_colour=np.array([.53,.52,.39])
 def colour(r,st,du=dust):
  r=np.maximum(r,st)
  c=base*(1-age)
  c=c*(1-r[:,:,None])+oxide*r[:,:,None]
  c=c*(1-soot[:,:,None])+np.array([.018,.021,.013])*soot[:,:,None]
  c=c*(1-wear[:,:,None])+metal*wear[:,:,None]
  return c*(1-du[:,:,None])+dust_colour*du[:,:,None]
 final=colour(rust,streak);norust=colour(np.zeros_like(x),np.zeros_like(x));nostreak=colour(rust,np.zeros_like(x));nodust=colour(rust,streak,np.zeros_like(x))
 rough=np.clip(.70+.11*soot+.12*rust+.08*dust-.17*wear,.45,.95)
 metallic=np.clip(.48*(1-rust)*(1-soot)*(1-dust)+.25*wear,.03,.70)
 broad=distance>.005
 allrust=np.maximum(rust,streak)
 olive=(allrust<.20)&(soot<.20)&(wear<.1)
 zones=np.stack([(distance<.0025).astype(float),broad.astype(float),(streak>.12).astype(float)],-1)*valid[:,:,None]
 coverage=np.stack([olive.astype(float),broad.astype(float),np.ones_like(x)],-1)*valid[:,:,None]
 masks={'zones':zones,'coverage':coverage,'dustmask':np.repeat((dust>.025)[:,:,None],3,-1)*valid[:,:,None]}
 images={'albedo':final,'no_rust':norust,'no_streak':nostreak,'no_dust':nodust,'control':base,'orm':np.stack([np.ones_like(x),rough,metallic],-1),'control_orm':np.stack([np.ones_like(x),np.full_like(x,.70),np.full_like(x,.48)],-1),'rust':np.repeat(allrust[:,:,None],3,-1),'soot':np.repeat(soot[:,:,None],3,-1),**masks}
 for name,a in images.items():save(prefix+'_'+name,a)
 em=float(allrust[valid&(distance<.0025)].mean());bm=float(allrust[valid&broad].mean())
 stats[prefix]={'albedo_mean_abs_effect':float(np.abs(final-base)[valid].mean()),'edge_rust_mean':em,'broad_rust_mean':bm,'edge_to_broad_rust_ratio':em/max(bm,1e-9),'broad_olive_paint_fraction':float(olive[valid&broad].mean()),'all_olive_paint_fraction':float(olive[valid].mean()),'edge_band_m':.0025,'sharp_edge_sample_count':int(len(np.load(R/(prefix+'_sharp_edges.npy'))))}
# Output is authored in linear light; only encode sRGB once for the texture.
w,h=2048,256;xx=np.linspace(-.485,.485,w)[None,:];yy=np.linspace(-.042,.042,h)[:,None]
failed=.51*np.exp(-((xx+.175)/.106)**6)
healthy=.92+.045*np.sin((xx+.23)*5.7)
bright=np.broadcast_to(healthy*(1-failed),(h,w)).copy();shadow=np.ones((h,w))
for cx,cy,wx,wy,depth in [(-.397,.018,.025,.021,.12),(-.202,-.025,.031,.022,.14),(.115,.019,.029,.019,.13),(.364,-.014,.038,.026,.11)]:
 shadow*=1-depth*np.exp(-((xx-cx)/wx)**2-((yy-cy)/wy)**2)
bright*=shadow*(.98-.025*(yy/.042)**2)
colour_linear=np.array([1.0,.91,.76]);drift=.012*np.sin((xx+.2)*4.3)
tint=np.stack([np.ones_like(xx),.91*(1+drift),.76*(1+drift*.6)],-1)
linear=bright[:,:,None]*tint
emission=np.where(linear<=.0031308,linear*12.92,1.055*np.maximum(linear,0)**(1/2.4)-.055)
save('glass_emission',emission)
means=[]
for i,xc in enumerate(SLOTS):
 mask=abs(xx[0]-xc)<.016;rgb=linear[:,mask].mean((0,1));means.append({'slot':i+1,'x_m':float(xc),'emission_rgb_linear_mean':rgb.tolist(),'relative_luminance_linear':float(rgb@[.2126,.7152,.0722]),'normalized_tint':(rgb/rgb[0]).tolist()})
failed_mean=np.mean([m['relative_luminance_linear'] for m in means[3:6]]);healthy_mean=np.mean([m['relative_luminance_linear'] for m in means[:3]+means[6:]])
stats.update({'glass_slots':means,'failed_section_slot_numbers':[4,5,6],'failed_section_length_m':.21,'failed_section_fraction_of_tube':.21/.97,'failed_section_linear_output_fraction':float(failed_mean/healthy_mean),'emission_colour_linear':[1,.91,.76],'maximum_authored_tint_drift_fraction':.012,'emission_max_adjacent_texel_linear_difference':float(np.max(np.abs(np.diff(linear,axis=1)))),'side_streak_length_m':.052,'channel_shoulder_streak_length_m':.065,'streak_fwhm_m':[.0014*2*np.sqrt(np.log(2)),.0018*2*np.sqrt(np.log(2))],'gravity_blender':[0,0,-1],'texture_resolution_px':[1024,1024],'glass_resolution_px':[2048,256],'texture_repeat':False,'field_method':'True sharp-edge distance sampled from mesh; nonperiodic hashed 3D smooth-value noise only modulates edge chips; fastener-distance heads and vertical Gaussian tails; channel-confined soot; normal-driven upper dust','rust_is_albedo_and_orm_only':True})
(R/'weather-stats.json').write_text(json.dumps(stats,indent=2));print(json.dumps(stats,indent=2))
