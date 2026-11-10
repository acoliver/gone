"""Measure alpha-weighted powder visibility against the exported bed blockers."""
import json
import numpy as np
import trimesh
from verify import ROOT, load


def visible_fraction(card, blockers, camera, orthographic, rng):
    chosen = rng.choice(len(card.faces), 2000, p=card.area_faces / card.area)
    u, v = rng.random((2, len(chosen)))
    u, v = np.where(u + v > 1, 1 - u, u), np.where(u + v > 1, 1 - v, v)
    barycentric = np.c_[1 - u - v, u, v]
    points = np.einsum('ij,ijk->ik', barycentric, card.triangles[chosen])
    patterns = card.visual.uv[card.faces[chosen]]
    uv = np.einsum('ij,ijk->ik', barycentric, patterns)
    image = np.asarray(card.visual.material.baseColorTexture)
    x = np.clip((uv[:, 0] * image.shape[1]).astype(int), 0, image.shape[1] - 1)
    y = np.clip(((1 - uv[:, 1]) * image.shape[0]).astype(int), 0, image.shape[0] - 1)
    alpha = image[y, x, 3].astype(float) / 255
    origins = np.tile(camera, (len(points), 1))
    if orthographic:
        direction = np.array([0, .54, 0]) - camera
        direction /= np.linalg.norm(direction)
        origins = points - direction * 6
    delta = points - origins
    distance = np.linalg.norm(delta, axis=1)
    directions = delta / distance[:, None]
    visible = np.ones(len(points), dtype=bool)
    # Bound the ray/triangle broad-phase arrays independently of sample count.
    for start in range(0, len(points), 128):
        hits, local_indices, _ = blockers.ray.intersects_location(
            origins[start:start + 128], directions[start:start + 128], multiple_hits=False)
        indices = local_indices + start
        visible[indices] = np.linalg.norm(hits - origins[indices], axis=1) >= distance[indices] - .00005
    return float(alpha[visible].sum() / alpha.sum())


def main():
    _, soft = load(ROOT / 'assets/props/quarters/bed_soft_aged.glb')
    _, frame = load(ROOT / 'assets/props/quarters/bed.glb')
    blockers = trimesh.util.concatenate([*frame.values(),
                                        *[soft[name] for name in ('Mattress', 'Quilt', 'Pillow_L', 'Pillow_R')]])
    rng = np.random.default_rng(95)
    report = {}
    for name in ('FibreFoamPowder_Platform', 'FibreFoamPowder_Foot', 'FibreFoamPowder_Floor'):
        report[name] = {}
        for view, camera, ortho in (('doorway', [0, 1.65, 4.75], False),
                                    ('three_quarter', [-3.1, 2.45, 3.7], True)):
            report[name][view] = visible_fraction(soft[name], blockers, np.array(camera), ortho, rng)
    print(json.dumps({'unoccluded_powder_alpha_fraction': report, 'samples_per_card_per_view': 2000}, indent=2))


if __name__ == '__main__':
    main()
