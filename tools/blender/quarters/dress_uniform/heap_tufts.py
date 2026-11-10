"""Scatter curled fibre bundles across the actual mound, clear of fallen cloth."""
import math

import numpy as np
from mathutils import Vector

from card_contacts import CardContacts
from common import surface_tree
from fabric_mesh import new_object
from soft_tuft import tuft_sections


def add_heap_tufts(mound, blockers, material, record):
    points = np.array([mound.matrix_world @ v.co for v in mound.data.vertices])
    tree = surface_tree(mound)
    contacts = CardContacts(blockers)
    lo, hi = points.min(0), points.max(0)
    rng = np.random.default_rng(95122)
    vertices, faces, patterns = [], [], []
    accepted = 0
    for attempt in range(2400):
        x, y = rng.uniform(lo[:2], hi[:2])
        hit, normal, _, _ = tree.ray_cast(Vector((x, y, hi[2]+.02)), Vector((0, 0, -1)))
        if hit is None or normal.z < .25 or hit.z < -.947:
            continue
        angle = rng.uniform(0, math.tau)
        direction = Vector((math.cos(angle), math.sin(angle), 0))
        direction = (direction-normal*direction.dot(normal)).normalized()
        sideways = normal.cross(direction).normalized()
        direction = (direction+normal*.08).normalized()
        sections = tuft_sections(hit+normal*.00035, direction, sideways, normal,
                                 rng.uniform(.003, .004), rng.uniform(.004, .006),
                                 rows=3, curl_strength=.8)
        quads = [[a[0], a[1], b[1], b[0]] for a, b in zip(sections, sections[1:])]
        if not all(contacts.clear(quad) for quad in quads):
            continue
        start = len(vertices)
        vertices.extend(sections.reshape(-1, 3))
        variant = int(rng.integers(8))
        for row, quad in enumerate(quads):
            contacts.add(quad)
            base = start+row*2
            faces.append((base, base+1, base+3, base+2))
            low, high = (variant+row/2)/8, (variant+(row+1)/2)/8
            patterns.append([(0, low), (1, low), (1, high), (0, high)])
        accepted += 1
        if accepted == 150:
            break
    if accepted == 0:
        raise ValueError('No clear top-facing mound surface for loose fibre bundles')
    material = material.copy()
    material.name = 'Loose pale wool heap bundles'
    obj = new_object('HeapFibres', vertices, faces, material)
    for polygon, face, pattern in zip(obj.data.polygons, faces, patterns):
        coordinates = dict(zip(face, pattern))
        for loop in polygon.loop_indices:
            obj.data.uv_layers.active.data[loop].uv = coordinates[obj.data.loops[loop].vertex_index]
    obj['aged_export'] = True
    record['heap_fibre_cards'] = accepted
    record['heap_fibre_surface'] = dict(curved=True, source='actual world-space mound bounds and upward ray hits',
                                       attempted=attempt+1, triangles=len(faces)*2, sat_checked=True)
    return record
