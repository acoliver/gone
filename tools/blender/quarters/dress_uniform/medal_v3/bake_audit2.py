"""Compare the actual bake ray's high surface with the nearest-high reference."""
from pathlib import Path
import sys
SOURCE=Path(__file__).resolve().parent
folder='fit1' if '--before' in sys.argv else 'fit2'
text=(SOURCE/'bakecheck.py').read_text().replace('tmp/issue130-v3/fit1','tmp/issue130-v3/'+folder)
text=text.replace("report={'sampling'", "audit=[]\nreport={'sampling'")
needle="   row['mapped_normal_error_degrees'].append(float(np.degrees(np.arccos(np.clip(mapped@reference,-1,1)))))"
extra="""
   if part=='Body' and (region=='side' or row['mapped_normal_error_degrees'][-1]>10):
    hit_full=tree.ray_cast(Vector(p+normal*extrusion),Vector(-normal),reach)
    ray_error=None;ray_nearest_angle=None
    if hit_full[0] is not None:
     hit_co=np.array(hit_full[0]);hj=hit_full[2];hw=barycentric(hit_co,hv[ht[hj]]);ray_normal=hw@hcn[hl[hj]];ray_normal/=np.linalg.norm(ray_normal)
     ray_error=float(np.degrees(np.arccos(np.clip(mapped@ray_normal,-1,1))));ray_nearest_angle=float(np.degrees(np.arccos(np.clip(reference@ray_normal,-1,1))))
    audit.append({'region':region,'triangle':int(triangle.polygon_index),'position_mm':p.tolist(),'uv':(weights@uv[ls]).tolist(),'nearest_error_degrees':row['mapped_normal_error_degrees'][-1],'ray_error_degrees':ray_error,'nearest_vs_ray_degrees':ray_nearest_angle,'nearest_distance_mm':float(distance)})
"""
assert needle in text
text=text.replace(needle,needle+extra)
text=text.replace("(OUT/'bake-check.json').write_text", "(SOURCE.parents[4]/'tmp/issue130-v3/fit2'/('bake-audit-'+('before' if '--before' in __import__('sys').argv else 'after')+'.json')).write_text(json.dumps(audit,indent=2))\n(OUT/('bake-check-audit.json' if '--before' in __import__('sys').argv else 'bake-check.json')).write_text")
# The before audit must not write into the predecessor directory.
if folder=='fit1':text=text.replace("(OUT/('bake-check-audit.json' if '--before' in __import__('sys').argv else 'bake-check.json'))", "(SOURCE.parents[4]/'tmp/issue130-v3/fit2'/'bake-check-before.json')")
exec(compile(text,str(SOURCE/'bakecheck.py'),'exec'),{'__file__':str(SOURCE/'bakecheck.py'),'__name__':'__main__'})
