from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
import json,numpy as np,struct
OUT=Path(__file__).resolve().parent
r=json.loads((OUT/'report.json').read_text());renders={}
for name in ['top','operator','side']:
 image=np.array(Image.open(OUT/f'{name}.png').convert('RGB'));mask=np.array(Image.open(OUT/f'render-masks/{name}-0001.png').convert('L'))>250
 assert image.shape==(900,1600,3)
 if not mask.any():raise RuntimeError(f'Empty key-top render mask: {name}')
 values=image[mask];renders[name]={'key_top_pixels':int(mask.sum()),'key_top_max_channel':int(values.max()),'key_top_max_rgb':values.max(0).tolist(),'key_top_median_rgb':np.median(values,axis=0).tolist(),'key_top_clipped_channel_count':int((values==255).sum())};assert values.max()<250,renders[name]
r['render_key_top_measurements']=renders
for name in ['albedo','orm','normal']:assert Image.open(OUT/f'keyboard_{name}.png').size==(2048,2048)
assert r['legend_count']==29 and r['matched_count']==29
assert all(v['painted_texels']>=5 for v in r['legends'])
assert r['triangles']<=30000
assert abs(r['dimensions_m'][0]-.8)<1e-5 and abs(r['dimensions_m'][2]-.055)<1e-5
b=(OUT/'keyboard.glb').read_bytes();length,kind=struct.unpack_from('<II',b,12);gltf=json.loads(b[20:20+length]);names=[n.get('name') for n in gltf['nodes']];assert 'Keyboard' in names and 'KeyboardBase' in names
r['export_nodes']=names;r['flux_scores']=json.loads((OUT/'flux-scores.json').read_text());r['shape_scores']=json.loads((OUT/'shape-scores.json').read_text());r['tracked_repo_files_changed']=False
(OUT/'report.json').write_text(json.dumps(r,indent=2)+'\n')
fontpath='/System/Library/Fonts/Supplemental/Arial.ttf';font=ImageFont.truetype(fontpath,24);small=ImageFont.truetype(fontpath,20);title=ImageFont.truetype(fontpath,34)
sheet=Image.new('RGB',(2400,1120),(27,29,31));d=ImageDraw.Draw(sheet);d.text((24,13),'Top-down generated keyboard | olive steel, dark rubber, worn Nalesha strokes',font=title,fill=(225,223,212))
seed=json.loads((OUT/'chosen-flux.json').read_text())['seed']
items=[(OUT/f'flux-{seed}.png',f'FLUX {seed} | top-down reference photo'),(OUT/'reference.png','Approved 29-key design | cropped top render'),(OUT/'top.png','Finished generated mesh | top'),(OUT/'operator.png','Operator view | 35 degrees above front'),(OUT/'side.png','Side view'),(OUT/'segmentation.png','Height-map key cores | design key numbers')]
for i,(path,label) in enumerate(items):
 col=i%3;row=i//3;x=col*800;y=65+row*485;image=Image.open(path).convert('RGB');image=ImageOps.contain(image,(792,440),Image.Resampling.LANCZOS);sheet.paste(image,(x+(800-image.width)//2,y+38+(440-image.height)//2));d.text((x+16,y+5),label,font=font,fill=(217,218,209))
d.text((24,1044),f"29 matched keys | 29 stroke legends | 2048 albedo / ORM / normal | Cycles 64 + denoise | 1600 x 900 per view",font=small,fill=(215,216,207))
d.text((24,1078),f"Shape {r['seed']}: mean / max centre error {r['mean_error_normalized']:.5f} / {r['max_error_normalized']:.5f}. Key-top render maxima: "+', '.join(f'{k} {v["key_top_max_channel"]}/255' for k,v in renders.items()),font=small,fill=(207,192,155));sheet.save(OUT/'contact.png')
print(json.dumps({'render_key_top_measurements':renders,'dimensions_m':r['dimensions_m'],'triangles':r['triangles'],'final_medians_srgb':r['final_medians_srgb'],'legend_count':r['legend_count'],'nodes':names},indent=2),flush=True)
