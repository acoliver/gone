"""Deposit nine cut-residue templates below tears and across front spill fans."""
import argparse
import json
from pathlib import Path
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from card_contacts import CardContacts
from common import surface_tree
from fabric_mesh import join, material, new_object
from powder_cards import powder_card
from sofa_decay_material import linear_to_srgb
from sofa_decay_policy import FOAM, ORDER
from sofa_full_decay import ROOT, checkpoint
from triangle_contacts import intersect


class DepositContacts(CardContacts):
    def clear_mesh(self, points, faces):
        triangles = np.asarray(points)[faces]
        for triangle in triangles:
            selected = np.all(self.maximum >= triangle.min(0), axis=1) & np.all(self.minimum <= triangle.max(0), axis=1)
            if any(intersect(triangle, other) for other in self.triangles[selected]):
                return False
        return True

    def add_mesh(self, points, faces):
        triangles = np.asarray(points)[faces]
        self.triangles = np.concatenate([self.triangles, triangles])
        self.minimum = np.concatenate([self.minimum, triangles.min(1)])
        self.maximum = np.concatenate([self.maximum, triangles.max(1)])


def load_templates(path):
    with bpy.data.libraries.load(str(path), link=False) as (source, target):
        target.objects = [n for n in source.objects if n.startswith('fragment-') and int(n[-2:]) < 9]
    templates = []
    for obj in target.objects:
        points = np.array([v.co[:] for v in obj.data.vertices])
        points -= points.mean(0)
        axes = np.linalg.svd(points, full_matrices=False)[2]
        if np.linalg.det(axes) < 0:
            axes[-1] *= -1
        points = points@axes.T
        obj.data.calc_loop_triangles()
        faces = np.array([t.vertices[:] for t in obj.data.loop_triangles])
        from mathutils.bvhtree import BVHTree
        tree = BVHTree.FromPolygons(points.tolist(), faces.tolist(), all_triangles=True)
        crossings = [(i, j) for i, j in tree.overlap(tree) if i < j and
                     not (set(faces[i]) & set(faces[j])) and intersect(points[faces[i]], points[faces[j]])]
        if crossings:
            print('REJECT_FRAGMENT_SELF_CONTACT', obj.name, crossings, flush=True)
        else:
            templates.append((obj.name, points, faces))
    if len(templates) < 8:
        raise ValueError('Deposition requires at least eight contact-free cut-residue templates')
    return sorted(templates, key=lambda entry: entry[0])


def opening_sources(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.normal_update()
    group = obj.vertex_groups['Lip shrink'].index
    deform = bm.verts.layers.deform.active
    points = []
    for edge in bm.edges:
        if not edge.is_boundary or max(v[deform].get(group, 0) for v in edge.verts) < .5:
            continue
        middle = sum((obj.matrix_world@v.co for v in edge.verts), Vector())/2
        outward = (middle-obj.matrix_world@edge.link_faces[0].calc_center_median()).normalized()
        points.append((middle, outward))
    bm.free()
    if not points:
        raise ValueError('No tear lips available for deposition sources')
    return points


def deposit(source, out, library, seed=9666, visible_deposits=False):
    bpy.ops.wm.open_mainfile(filepath=str(source))
    record = json.loads(bpy.context.scene['sofa_decay_record'])
    rng = np.random.default_rng(seed)
    templates = load_templates(library)
    solids = [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.get('aged_export')]
    contacts = DepositContacts(solids)
    support_objects = [bpy.data.objects['Frame'], bpy.data.objects['Feet']]+[bpy.data.objects[n+'_Residue'] for n in ORDER]
    if visible_deposits:
        support_objects += [bpy.data.objects[n+'_GameContact'] for n in ORDER[:3]]
    supports = [surface_tree(o) for o in support_objects]
    foam_mat = material('Foam_Debris', FOAM)
    pieces, placements = [], []
    floor_positions = []
    rejected = 0

    def place(xy, floor, source_index):
        nonlocal rejected
        index = len(pieces)
        template, points, faces = templates[index % len(templates)]
        median = .011 if visible_deposits and not floor else .005
        size = float(np.clip(rng.lognormal(np.log(median), .55), .002, .025))
        points = points*(size/np.ptp(points, axis=0).max())
        yaw = rng.uniform(0, 2*np.pi)
        rotation = np.array([[np.cos(yaw), -np.sin(yaw), 0], [np.sin(yaw), np.cos(yaw), 0], [0, 0, 1]])
        points = points@rotation.T
        if floor:
            centre, normal = Vector((xy[0], xy[1], 0)), Vector((0, 0, 1))
        else:
            hits = [tree.ray_cast(Vector((xy[0], xy[1], .65)), Vector((0, 0, -1))) for tree in supports]
            hits = [h for h in hits if h[0] is not None]
            if not hits:
                rejected += 1
                return False
            point, normal, _, _ = max(hits, key=lambda hit: hit[0].z)
            centre = point
            if normal.z < 0:
                normal = -normal
        align = Vector((0, 0, 1)).rotation_difference(normal)
        points = np.array([align@Vector(p) for p in points])
        lift = -float(np.min(points@np.asarray(normal)))+.0007
        points += np.asarray(centre+normal*lift)
        if not contacts.clear_mesh(points, faces):
            rejected += 1
            return False
        crumb = new_object(f'DepositedCrumb_{index:03d}', points, faces, foam_mat)
        pieces.append(crumb)
        contacts.add_mesh(points, faces)
        triangles = points[faces]
        areas = np.linalg.norm(np.cross(triangles[:, 1]-triangles[:, 0], triangles[:, 2]-triangles[:, 0]), axis=1)
        centroid = np.average(triangles.mean(1), weights=areas, axis=0)
        placements.append({'template': template, 'size_m': size, 'floor': floor,
                           'source': source_index, 'centre_blender_m': centroid.tolist()})
        if floor:
            floor_positions.append(np.asarray(xy))
        return True

    spills = []
    for source_index, name in enumerate(ORDER[:3]):
        obj = bpy.data.objects[name+'_GameContact']
        lips = opening_sources(obj)
        cx = obj.matrix_world.translation.x
        accepted = 0
        # Most foam stays on the deck. Only the leaking front lips seed a
        # sparse floor tail; the powder drift belongs under those openings.
        cx = float(np.mean([middle.x for middle, _ in lips]))
        radii = np.linspace(0, .24, 6)
        for band, target in enumerate((2, 2, 1, 1, 0)):
            count, attempts = 0, 0
            while count < target and attempts < 10000:
                attempts += 1
                radius = np.sqrt(rng.uniform(radii[band]**2, radii[band+1]**2))
                angle = rng.uniform(-np.pi/2, np.pi/2)
                xy = np.array([cx+radius*np.sin(angle), -.478-radius*np.cos(angle)])
                if floor_positions and min(np.linalg.norm(xy-p) for p in floor_positions) < .024:
                    continue
                count += int(place(xy, True, source_index))
            if count != target:
                raise ValueError('Floor spill could not meet its radial density and spacing without contacts')
            accepted += count
        deck_accepted = 0
        for _ in range(3000):
            middle, outward = lips[int(rng.integers(len(lips)))]
            point = middle+outward*rng.uniform(.003, .030)
            deck_accepted += int(place((point.x, point.y), False, source_index))
            if deck_accepted >= 20:
                break
        lip_accepted = 0
        for _ in range(2000):
            x = rng.uniform(cx-.20, cx+.20)
            y = rng.uniform(-.420, -.345)
            lip_accepted += int(place((x, y), False, source_index))
            if lip_accepted >= 12:
                break
        powder = powder_card('PowderSpill_'+name, (cx, -.325, .3912),
                             (.20+source_index*.027, .018+source_index*.001),
                             out/'textures/powder', seed+source_index)
        unsupported = set()
        for vertex in powder.data.vertices:
            hits = [tree.ray_cast(Vector((vertex.co.x, vertex.co.y, 1.2)), Vector((0, 0, -1))) for tree in supports[:1]]
            heights = [hit[0].z for hit in hits if hit[0] is not None and hit[0].z > .35]
            if not heights:
                unsupported.add(vertex.index)
            else:
                vertex.co.z = max(heights)+.0005
        powder_points = np.array([v.co[:] for v in powder.data.vertices])
        bm = bmesh.new()
        bm.from_mesh(powder.data)
        remove = [face for face in bm.faces if any(v.index in unsupported for v in face.verts) or
                  not contacts.clear_mesh(powder_points, np.array([[v.index for v in face.verts]]))]
        bmesh.ops.delete(bm, geom=remove, context='FACES')
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
        if not bm.faces:
            bm.free()
            raise ValueError('No collision-free powder surface remains under the seat opening')
        powder_clipped = len(remove)
        bm.to_mesh(powder.data)
        bm.free()
        powder.data.calc_loop_triangles()
        powder_points = np.array([v.co[:] for v in powder.data.vertices])
        powder_faces = np.array([t.vertices[:] for t in powder.data.loop_triangles])
        contacts.add_mesh(powder_points, powder_faces)
        shader = powder.data.materials[0].node_tree.nodes['Principled BSDF']
        image = shader.inputs['Base Color'].links[0].from_node.image
        pixels = np.array(image.pixels[:], dtype=np.float32).reshape(image.size[1], image.size[0], 4)
        pixels[:, :, :3] *= linear_to_srgb(FOAM)/np.array([.28, .19, .10])
        image.pixels.foreach_set(pixels.ravel())
        image.save()
        image.pack()
        spills.append({'part': name, 'origin_blender_m': [cx, -.478, 0],
                       'floor_count': accepted, 'deck_count': deck_accepted,
                       'front_lip_count': lip_accepted, 'powder': powder.name,
                       'powder_clipped_triangles': powder_clipped})
    debris = pieces[0]
    debris.name = 'FoamDebris'
    join(debris, pieces[1:])
    record['debris'] = {'method': 'contact-free residue skin templates; opening-led deck deposits and front-lip drifts, sparse floor tails',
                         'visible_deposits': visible_deposits,
                         'nonfloor_size_median_m': .011 if visible_deposits else .005,
                         'support_objects': [o.name for o in support_objects],
                         'seed': seed, 'templates': [t[0] for t in templates], 'placements': placements,
                         'spills': spills, 'rejected_contacts': rejected,
                         'floor_minimum_spacing_m': .024, 'powder_support_clearance_m': .0005,
                         'crumb_support_clearance_m': .0007,
                         'powder_note': 'Sub-millimetre powder represented by alpha cards; fragments clear their geometric card planes.'}
    checkpoint(out, record, 'deposited.blend')
    return record


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--out', type=Path, default=ROOT/'tmp/age/pass6')
    p.add_argument('--library', type=Path, default=ROOT/'tmp/age/pass4/fragments8/fragment-library.blend')
    a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
    deposit(a.source, a.out, a.library)
