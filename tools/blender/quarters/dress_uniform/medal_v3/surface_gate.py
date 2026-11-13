"""Assert the requested geometry gates before starting bakes and captures."""
from pathlib import Path
import json
SOURCE=Path(__file__).resolve().parent;OUT=SOURCE.parents[4]/'tmp/issue130-v3/fit1'
fit=json.loads((OUT/'fit-report.json').read_text());verification=json.loads((OUT/'verification.json').read_text());local=json.loads((OUT/'local-measurements.json').read_text());silhouette=json.loads((OUT/'silhouette-errors-after.json').read_text())
assert fit['low_triangles']<=10500
for kind in ['high','low']:
 assert all(p['watertight'] and p['consistent_winding'] and p['min_triangle_area_m2']>1e-17 for p in verification[kind]['topology'].values())
 assert verification[kind]['uv']['zero_area_triangles']==verification[kind]['uv']['positive_area_overlaps']==0
 assert local['star'][kind]['peaks']==5
 assert local['field'][kind]['interior_sharp_edges']==0
for camera,row in silhouette['cameras'].items():
 error=row['all_parts'];bound=error['max_px']+error['max_sampling_underestimate_bound_px']+.0003
 assert bound<.5,(camera,bound)
 print(camera,'silhouette upper bound px',bound)
field=json.loads((OUT/'field-flatness.json').read_text());assert len(field['field_components'])==1 and field['guidance_fidelity_per_mm2']==field['field_interior_crease_edges']==0
print('SURFACE_GATES_PASSED',flush=True)
