from pathlib import Path
O=Path(__file__).resolve().parent
p=O/'geometry.py';s=p.read_text();s=s.replace('extension=.225-depth','extension=.035')
a=s.index('seed_y0=');z=s.index('# Some source side triangles')
s=s[:a]+'''band_rear=front+.025/math.sqrt(1+b*b)
lip_bottom=.478;falloff=.200

def influence(points):
 y=points[:,1];z=points[:,2]
 # The entire front lip is rigid. Only the front 25 mm of top moves.
 # Below it, front-face displacement is affine in source z, ending 200 mm down.
 lower_front=-.366-.48*z+.025
 t=np.clip((z-lip_bottom)/.010,0,1)
 limit=np.where(z<=lip_bottom,lower_front,(1-t)*(-.366-.48*lip_bottom+.025)+t*band_rear)
 limit=np.maximum(limit,band_rear)
 front_band=np.clip((limit-y)/.008,0,1)
 return np.clip((z-(lip_bottom-falloff))/falloff,0,1)*front_band
''' +s[z:]
s=s.replace("from tessellate import local_tessellation","from tessellate import local_tessellation\nfrom lip_profile import measure_lip")
s=s.replace('w=influence(before)','lip_before=measure_lip(before,faces,(a,b,c))\nw=influence(before)')
s=s.replace('mesh.update();moved=', '''mesh.update()
lip_after=measure_lip(np.array([v.co[:] for v in mesh.vertices]),faces,(a,b,c),-extension*tangent)
for old,new in zip(lip_before,lip_after):
 assert abs(old['normal_thickness_mm']-new['normal_thickness_mm'])<.002,(old,new)
 assert abs(old['front_face_angle_from_vertical_deg']-new['front_face_angle_from_vertical_deg'])<.002,(old,new)
assert np.allclose(movement[(before[:,1]<band_rear-.008)&(before[:,2]>=lip_bottom)],-extension*tangent,atol=1e-10)
low=(before[:,2]<lip_bottom-falloff)
assert np.array_equal(before[low],after[low])
front_face=(before[:,2]>.29)&(before[:,2]<.46)&(before[:,1]<-.366-.48*before[:,2]+.010)
linear_expected=(before[front_face,2]-(lip_bottom-falloff))/falloff
assert np.allclose(w[front_face],linear_expected,atol=1e-12)
moved=''')
s=s.replace('if maximum>1.4:', 'if affected.any():')
s=s.replace("'Full-width front-edge and lip selection, smooth cubic proportional falloff in YZ, clipped at unchanged rear deck junction and below unchanged head'","'Rigid front lip and front 25 mm top band, in-plane 35 mm translation; front-face falloff linear in source z over 200 mm, local linear side blend; no radial or cubic falloff'")
s=s.replace("'falloff_radius_m':radius,","'front_band_along_slope_m':.025,'linear_z_falloff_height_m':falloff,'linear_z_falloff_top_m':lip_bottom,'linear_z_falloff_bottom_m':lip_bottom-falloff,'below_falloff_unchanged':True,'front_face_linear_z_verified_vertices':int(front_face.sum()),")
s=s.replace("int(affected.sum()) if maximum>1.4 else 0","int(affected.sum())")
s=s.replace("'protected_objects_before':protected", "'lip_profile':{'measurement':'Thickness normal to the deck at source y=-0.680 m; front-face least-squares angle from vertical at source z=0.510..0.528 m. After samples translated by the exact in-plane extension.','before':lip_before,'after':lip_after,'profile_preserved':True},'protected_objects_before':protected")
p.write_text(s)
p=O/'textures.py';s=p.read_text()
s=s.replace('field=.7*noise(38,491)+.3*noise(113,819);band=dist<.004', '''# A larger second octave modulates local chip size. High frequency detail
# supplies the many tiny chips, while the sparse broad peaks join larger ones.
large=noise(9,491);finechips=noise(145,819)
field=.55*finechips+.30*noise(53,931)+.15*large
field+=.35*np.clip((large-.65)/.35,0,1)**2
band=dist<.004''')
s=s.replace("np.quantile(selector[chip],.60)","np.quantile(selector[chip],.25)")
s=s.replace('[110,58,36]','[96,62,44]')
s=s.replace("'edge_chip_coverage':", "'chip_size_noise':{'fine_scale_per_m':145,'middle_scale_per_m':53,'large_scale_per_m':9,'large_octave_peak_boost':.35},'edge_chip_coverage':")
p.write_text(s)
p=O/'build.py';s=p.read_text();s=s.replace("scene.cycles.samples=64;", "prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='METAL';prefs.get_devices()\nfor device in prefs.devices:device.use=device.type=='METAL'\nassert any(d.use for d in prefs.devices),'Metal device unavailable'\nscene.cycles.device='GPU'\nscene.cycles.samples=64;")
p.write_text(s)
p=O/'validate.py';s=p.read_text().replace("abs(r['deck']['along_slope_depth_m']-.225)","abs(r['deck']['along_slope_depth_m']-.18205164686194586)")
s=s.replace('Deeper keyboard deck: 225 mm, full-size keyboard','Milder deck extension: +35 mm, refitted keyboard')
s=s.replace("'contact.png','report.json'","'contact.png','side-profile-comparison.png','report.json'")
s=s.replace("r['incomplete']=[]", "r['incomplete']=[]\nassert r['lip_profile']['profile_preserved']\nassert abs(t['undercoat_fraction_of_chips']-.70)<.001 and abs(t['rust_fraction_of_chips']-.25)<.001 and abs(t['steel_fraction_of_chips']-.05)<.001\nassert abs(t['edge_chip_coverage']-.09)<.001\nassert max(abs(np.array(t['rust_median_srgb_255'])-np.array([96,62,44])))<=4\nassert abs(r['keyboard']['deck_frame_dimensions_m'][1]-(r['deck']['along_slope_depth_m']-.020))<1e-5")
p.write_text(s)
