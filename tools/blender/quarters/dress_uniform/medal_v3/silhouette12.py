"""Continuous projected full-perimeter comparisons at studio and fixed game cameras."""
from pathlib import Path
import json
import re
import sys
import numpy as np
import shapely
from shapely.geometry import Polygon
from PIL import Image, ImageDraw, ImageFont

SOURCE=Path(__file__).resolve().parent
ROOT=SOURCE.parents[4];OUT=ROOT/'tmp/issue130-v3/fit1'
after='--after' in sys.argv
folder=OUT;suffix='after' if after else 'before'
sys.path.insert(0,str(SOURCE))
from projection import project

def outline(data,camera):
 polys=[];parts={}
 for d in data:
  p=project(np.array(d['vertices']),camera);t=np.array(d['triangles']);q=p[t]
  a=q[:,1]-q[:,0];b=q[:,2]-q[:,0]
  # Either orientation covers the same projected solid on a closed mesh.
  chosen=(a[:,0]*b[:,1]-a[:,1]*b[:,0])>1e-12
  chunks=[]
  for i in range(0,int(chosen.sum()),12000):
   chunks.append(shapely.union_all(shapely.polygons(q[chosen][i:i+12000]),grid_size=.00001))
  poly=shapely.union_all(chunks,grid_size=.00001)
  # Float32 cut seams and projected roundoff create long, zero-width slits.
  # Close only gaps below 0.0002px, then discard sub-0.001px2 interior rings.
  poly=poly.buffer(.0001,quad_segs=1).buffer(-.0001,quad_segs=1)
  pieces=list(poly.geoms) if hasattr(poly,'geoms') else [poly]
  poly=shapely.union_all([Polygon(p.exterior,[h for h in p.interiors if Polygon(h).area>.001]) for p in pieces])
  parts[d['name'].split('_')[0]]=poly
  polys.append(poly)
 return shapely.union_all(polys),parts

def samples(boundary,step=.05):
 lines=list(boundary.geoms) if hasattr(boundary,'geoms') else [boundary]
 return shapely.get_coordinates(shapely.line_interpolate_point(np.repeat(np.array(lines,dtype=object),[max(2,int(np.ceil(l.length/step))) for l in lines]),
  np.concatenate([np.linspace(0,l.length,max(2,int(np.ceil(l.length/step))),endpoint=False) for l in lines])))

def measure(a,b):
 pa=samples(a.boundary);pb=samples(b.boundary)
 da=shapely.distance(shapely.points(pa),b.boundary);db=shapely.distance(shapely.points(pb),a.boundary)
 error=np.r_[da,db];worst=pa[da.argmax()] if da.max()>db.max() else pb[db.argmax()]
 return {'max_px':float(error.max()),'p95_px':float(np.percentile(error,95)),'rms_px':float(np.sqrt(np.mean(error**2))),
  'samples':len(error),'sampling_spacing_px':.05,'max_sampling_underestimate_bound_px':.025,'worst_pixel':worst.tolist(),
  'symmetric_difference_area_px2':float(a.symmetric_difference(b).area)}

report={'scope':'Standalone fitted mesh at the unchanged studio camera and frozen game close-camera registration; not a mounted runtime capture. Full projected union includes all three parts and the hanger opening.',
 'method':'Union of all forward oriented projected triangles. Bidirectional polygon-boundary distances sampled every <=0.05px, maximum sampling underestimation <=0.025px. Numerical seams cleaned at subpixel precision; real hanger openings retained.',
 'numerical_cleanup':{'precision_grid_px':.00001,'slit_close_buffer_px':.0001,'discard_holes_below_area_px2':.001,'conservative_error_bound_px':.0003},
 'cameras':{}}
for camera in ['studio','game']:
 outlines={};parts={}
 for kind in ['high','low']:
  data=json.loads((folder/(kind+'-arrays.json')).read_text());outlines[kind],parts[kind]=outline(data,camera)
  print('PROJECTED',camera,kind,flush=True)
 report['cameras'][camera]={'all_parts':measure(outlines['high'],outlines['low']),
  'parts':{name:measure(parts['high'][name],parts['low'][name]) for name in parts['high']},
  'high_body_width_px':float(parts['high']['Body'].bounds[2]-parts['high']['Body'].bounds[0])}
 (OUT/('silhouette-'+camera+'-'+suffix+'.json')).write_text(json.dumps({kind:shapely.to_geojson(p) for kind,p in outlines.items()}))
(OUT/('silhouette-errors-'+suffix+'.json')).write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2),flush=True)
print('SILHOUETTE11_COMPLETE',suffix,flush=True)
