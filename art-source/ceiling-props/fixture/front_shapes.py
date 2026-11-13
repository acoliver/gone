from common import *
from make_shapes import generate
from finish import directional_metrics
views=json.loads((ROOT/'selected-views.json').read_text())
rows=generate({'front':views['front']},[720,721,722],'front-only')
if len(rows)!=3:raise RuntimeError('The accepted front-only set requires three successful seeds')
for row in rows:
 row['directional_metrics']=directional_metrics(row)
 row['best_grille_surface']=max(row['directional_metrics'],key=lambda k:row['directional_metrics'][k]['score'])
 row['selection_score']=max(m['score'] for m in row['directional_metrics'].values())-abs(row['length_width_ratio']-5)*.1
chosen=max(rows,key=lambda r:r['selection_score'])
old=json.loads((ROOT/'hunyuan/710/stats.json').read_text());old['rejected']=True
allrows=[old,*rows];dump(ROOT/'mesh-results.json',allrows);dump(ROOT/'chosen.json',chosen)
sheet(CONCEPTS+[(f"s{r['seed']} {v} L/W {r['length_width_ratio']:.2f}",p) for r in allrows for v,p in r.get('renders',{}).items()],ROOT/'sheet-clay.jpg')
(ROOT/'SHAPES_READY').touch()
d=ROOT/'hunyuan'/str(chosen['seed']);painted=d/'painted.glb'
ok=run('paint-'+str(chosen['seed']),[PY,PORT/'paint.py','--mesh',chosen['mesh'],'--image',views['front']['rgba'],'--out',painted,'--model-path',PORT/'weights/Hunyuan3D-2','--resolution','512','--texture-size','1024','--seed',chosen['seed'],'--memory-limit-gb','32','--vae-chunk','1','--save-views',d/'paint-views.png','--save-bake-diagnostics',d/'paint-coverage.npz','--metallic','0.35','--roughness','0.7'],gpu=True,cwd=PORT)
dump(ROOT/'paint-result.json',{'success':ok and painted.exists(),'path':str(painted),'log':str(ROOT/'logs'/('paint-'+str(chosen['seed'])+'.log'))})
if not ok:note('Paint failed; use concept-image projection for PBR. The actual exception is retained in the paint log and failures.json. No game shader is changed.')
(ROOT/'PAINT_READY').touch()
