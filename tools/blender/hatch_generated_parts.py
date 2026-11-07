"""Frozen whole hardware objects and repaired seed-430 door body."""
from pathlib import Path
import json
from types import SimpleNamespace

import numpy as np
from mathutils import Matrix

import hatch_fit as fit
from hatch_generated_frame import reduce_region
from hatch_leaf_surface import seated_hardware, slab_geometry


class GeneratedParts:
    def __init__(self, document):
        self.root = Path(__file__).resolve().parents[2] / 'art-source/hatch/hunyuan/parts'
        manifest = json.loads((self.root / 'provenance.json').read_text())
        fit.validate_manifest(self.root, manifest)
        self.placements = json.loads((self.root / 'placements.json').read_text())
        self.recipe = json.loads((self.root / 'leaf-fit.json').read_text())
        self.vertices, self.faces = fit.read_source_glb(self.root / 'leaf-s430.glb')
        self.body = SimpleNamespace(vertices=self.vertices, faces=self.faces, recipe=self.recipe)
        self.cache = {}
        parts = {}
        for key in ['latch', 'wheel', 'leaf']:
            row = manifest['selected'][key]
            parts[key] = dict(file=row['file'], sha256=fit.sha256(self.root / row['file']), seed=row['seed'])
        parts['provenance_sha256'] = fit.sha256(self.root / 'provenance.json')
        parts['hub_cut'] = json.loads((self.root / 'hub-cut.json').read_text())['rows']
        parts['wheel_fit'] = json.loads((self.root / 'wheel-fit.json').read_text())
        document['generated_sources']['parts'] = parts
        document['fit_recipe']['slice'] = 'generated_frame_whole_latches_wheels_repaired_leaf'
        document['fit_recipe']['parts_operations'] = self.recipe['operations']

    def _region(self, part):
        shape = part['shape']
        if shape == 'generated_latch':
            row = self.placements['latch']
            p, f = fit.read_source_glb(self.root / 'latch-dog-s601.glb')
            p[:, :2] -= row['boss_source_xy']
            angle = np.radians(row['rotation_degrees'])
            rotation = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
            p[:, :2] = np.einsum('ij,kj->ik', p[:, :2], rotation) * row['scale']
            p[:, 2] = -(p[:, 2] - p[:, 2].min()) * row['scale']
            p -= (np.asarray(row['bounds'][0]) + row['bounds'][1]) / 2
            f = f[:, [0, 2, 1]]
            digest = fit.sha256(self.root / 'latch-dog-s601.glb')
        elif shape == 'generated_rib':
            registration = next(row for row in self.recipe['registrations'] if row['part_id'] == part['id'])
            selected = np.asarray(self.recipe['patches'][registration['source_patch']]['source_faces'])
            used, remap = np.unique(self.faces[selected], return_inverse=True)
            p, f, _, error, _ = seated_hardware(self.vertices[used], remap.reshape(-1, 3), selected,
                np.asarray(part['size']), registration['rotation'], registration['scale'], registration['center'])
            if error > 1e-6:
                raise fit.FitError(f'rib {part["id"]}: attachment bounds error {error:.9f} m')
            frame = np.asarray(registration['virtual_to_local'])
            p = np.einsum('ij,kj->ik', p, frame)
            if np.linalg.det(frame) < 0:
                f = f[:, [0, 2, 1]]
            digest = fit.sha256(self.root / 'leaf-s430.glb')
        else:
            raise fit.FitError('unsupported generated part: ' + part['id'])
        triangle = p[f]
        positive = np.linalg.norm(np.cross(triangle[:, 1]-triangle[:, 0], triangle[:, 2]-triangle[:, 0]), axis=1) > 0
        return fit.FittedRegion(part['id'], p, f[positive], np.flatnonzero(positive)), digest

    def geometry(self, part, parent, create, material):
        from hatch_bake import CINV
        import bpy
        shape = part['shape']
        key = (shape, tuple(np.round(part['size'], 6)))
        if shape == 'generated_wheel':
            data = np.load(self.root / 'wheel-low.npz')
            high_data = np.load(self.root / 'wheel-high.npz')
            center = np.asarray(json.loads((self.root / 'wheel-fit.json').read_text())['center'])
            p, f = data['vertices'] - center, data['faces']
            hp, hf = high_data['vertices'].copy(), high_data['faces'][:, [0, 2, 1]]
            hp[:, 2] *= -1
            hp -= center
            digest = fit.sha256(self.root / 'handwheel-s600.glb')
        else:
            if key not in self.cache:
                region, digest = self._region(part)
                budget = 600 if shape == 'generated_latch' else 240
                p, f, high = reduce_region(region, dict(origin=[0, 0, 0], basis=np.eye(3).tolist()),
                    budget, create, parent, material)
                hp = np.asarray([tuple((CINV @ v.co.to_4d())[:3]) for v in high.data.vertices])
                hf = np.asarray([tuple(polygon.vertices) for polygon in high.data.polygons])
                bpy.data.objects.remove(high, do_unlink=True)
                self.cache[key] = p, f, hp, hf, digest
            p, f, hp, hf, digest = self.cache[key]
        high = create('High_' + part['id'].replace('/', '_'), hp, hf, parent,
                      Matrix.Identity(4), material, recalc=False)
        for polygon in high.data.polygons:
            polygon.use_smooth = True
        high.hide_render = True
        high.hide_set(True)
        return p, f, high, digest

    def slab(self, part, group, variant, base_geometry, parent, create, material):
        label_row = variant['fit']['labels'][group['side']]
        label = dict(size=label_row['size'], center=(np.asarray(label_row['transform']['origin'][:2]) - group['transform']['origin'][:2]).tolist())
        p, f, paint_end = slab_geometry(part, self.body, base_geometry, label=label)
        hp, hf, _ = slab_geometry(part, self.body, base_geometry, high=True, label=label)
        high = create('High_' + part['id'].replace('/', '_'), hp, hf, parent,
                      Matrix.Identity(4), material, recalc=False)
        high.hide_render = True
        high.hide_set(True)
        return p, f, high, paint_end
