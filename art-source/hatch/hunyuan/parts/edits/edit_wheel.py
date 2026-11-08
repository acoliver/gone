"""Reproduce the six-fold wheel and the single approved planar dome cut."""
from pathlib import Path
import json
import math

import manifold3d as m
import numpy as np

import argparse
import sys
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])
OUT = args.output.resolve()
OUT.mkdir(parents=True, exist_ok=True)
SOURCE = Path(__file__).resolve().parents[1]
ROOT = SOURCE.parents[3]
inputs = np.load(OUT / 'hub-cut-input.npz')
measurements = json.loads((SOURCE / 'placements.json').read_text())['wheel']
cut = json.loads((OUT / 'hub-cut.json').read_text())['rows'][0]
points, inverse = np.unique(inputs['vertices'], axis=0, return_inverse=True)
faces = inverse[inputs['faces']]
tri = points[faces]
positive = np.linalg.norm(np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0]), axis=1) > 0
raw = m.Manifold(m.Mesh(points.astype(np.float32), faces[positive].astype(np.uint32)))
if raw.status() != m.Error.NoError:
    raise RuntimeError(f'wheel source topology: {raw.status()}')
print('SOURCE', raw.num_tri(), 'zero-area removed', int((~positive).sum()), flush=True)
radius = measurements['hub_keep_radius_source'] * measurements['scale']
cylinder = m.Manifold.cylinder(2., radius, circular_segments=192, center=True)
hub = raw ^ cylinder
outer = raw - cylinder
lo, hi = map(math.radians, measurements['sector_degrees'])
sector = outer.trim_by_plane((-math.sin(lo), math.cos(lo), 0), 0)
sector = sector.trim_by_plane((math.sin(hi), -math.cos(hi), 0), 0)
print('CENTRAL', hub.num_tri(), 'SECTOR', sector.num_tri(), flush=True)
assembled = hub
for index in range(6):
    assembled = assembled + sector.rotate((0, 0, index*60))
    print('REPEAT', index, assembled.num_tri(), assembled.status(), flush=True)
# Source-front remains outward. Removing z>seat affects only the central dome:
# all retained spoke/rim vertices are behind the cut plane.
assembled = assembled.trim_by_plane((0, 0, -1), -cut['cut_plane_z_m'])
if assembled.status() != m.Error.NoError:
    raise RuntimeError(f'edited wheel topology: {assembled.status()}')
mesh = assembled.to_mesh()
p, f = np.asarray(mesh.vert_properties)[:, :3].astype(float), np.asarray(mesh.tri_verts)
np.savez_compressed(OUT / 'wheel-high.npz', vertices=p, faces=f)
report = dict(triangles=len(f), vertices=len(p), bounds=[p.min(0).tolist(),p.max(0).tolist()],
    radial_bound_m=float(np.linalg.norm(p[:,:2],axis=1).max()), volume_m3=assembled.volume(),
    connected_components=len(assembled.decompose()), removed_zero_area_faces=int((~positive).sum()),
    cut_plane_z_m=cut['cut_plane_z_m'], cut_depth_each_face_m=cut['cut_depth_m'],
    hub_cylinder_segments=192, hub_radius_m=radius,
    operations=['Preserve the central source hub within radius 0.30 source units.',
        'Retain 7.5..67.5 degree outer spoke/rim sector; repeat six times at 60 degrees.',
        'Boolean-weld touching sector seams and hub attachment without vertex displacement.',
        'Remove the central dome beyond the approved face-normal plane, closing that plane.'])
(OUT/'wheel-edit.json').write_text(json.dumps(report,indent=2)+'\n')
print('WHEEL_EDIT',json.dumps(report),flush=True)
