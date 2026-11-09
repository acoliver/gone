"""The mound must not gain a rectangular film from the positive SDF isovalue."""
import json
from pathlib import Path
import sys
import numpy as np
import trimesh
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_fibre_heap import build

root = Path(__file__).resolve().parents[4]
out = root/'tmp/age/tunic9/heap-control.npz'
out.parent.mkdir(parents=True, exist_ok=True)
build(.0016761162551119924, out)
data = np.load(out)
vertices = data['vertices']
corners = (abs(vertices[:, 0]) > .13) & (abs(vertices[:, 1]) > .06)
assert not corners.any(), f'{corners.sum()} vertices still form the rectangular corner film'
mesh = trimesh.Trimesh(vertices, data['faces'], process=False)
assert mesh.is_watertight
report = json.loads(out.with_suffix('.json').read_text())
assert .015 <= report['height_m'] <= .035, report
assert .9 <= report['ratio'] <= 1.1, report
print('PASS: compact mound has no rectangular corner film, is closed, and preserves height and wool mass')
