"""Construct a mass-balanced loose-wool height-field SDF with installed scipy/skimage."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / 'tools/blender/quarters_aging'))
from residue_sdf import height_field, mesh_sdf


def build(lost_area, out):
    voxel = .001
    x = np.arange(-.142, .143, voxel)
    y = np.arange(-.072, .073, voxel)
    z = np.arange(-.003, .040, voxel)
    h, _ = height_field(x, y, 9521)
    xx, yy = np.meshgrid(x, y, indexing='ij')
    # Loose fibres have a peaked deposit, unlike a uniform foam-residue slab.
    envelope = np.exp(-((xx/.085)**2+(yy/.042)**2)*1.8)
    h = np.maximum(h, 0)*envelope
    # Concentrate the same lost wool into a soft central deposit.
    h *= np.exp(-((xx/.070)**2+(yy/.034)**2)*.65)
    target_volume = lost_area*.0035/.05
    h *= target_volume/(h.sum()*voxel**2)
    sdf = np.maximum(z[None, None, :]-h[:, :, None], -z[None, None, :])
    sdf[[0, -1], :, :] = .01
    sdf[:, [0, -1], :] = .01
    sdf[:, :, [0, -1]] = .01
    v, f, _ = mesh_sdf(sdf.astype(np.float32), np.array([x[0], y[0], z[0]]), voxel)
    mesh = trimesh.Trimesh(v, f, process=False)
    if mesh.volume < 0:
        f = f[:, ::-1]
        mesh = trimesh.Trimesh(v, f, process=False)
    np.savez_compressed(out, vertices=v, faces=f)
    report = dict(lost_area_m2=lost_area, wool_thickness_m=.0035, packing_fraction=.05,
                  expected_volume_m3=target_volume, measured_volume_m3=float(mesh.volume),
                  ratio=float(mesh.volume/target_volume), height_m=float(np.ptp(v[:, 2])),
                  source='shared residue_sdf.height_field and mesh_sdf; tunic-local deposition envelope')
    out.with_suffix('.json').write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--lost-area', type=float, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if a.lost_area <= 0:
        p.error('Lost area must be measured and positive')
    build(a.lost_area, a.out)
