"""Resample dense tear boundaries at card spacing, and measure root coverage."""
import math

import bmesh
import bpy
import numpy as np
from mathutils import Vector

from fabric_mesh import new_object
from card_contacts import CardContacts


def boundary_chains(obj, group_name=None):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.normal_update()
    bm.verts.index_update()
    deform = bm.verts.layers.deform.active
    group = obj.vertex_groups[group_name].index if group_name else None
    remaining = {e for e in bm.edges if e.is_boundary and
                 (group is None or all(v[deform].get(group, 0.) >= .5 for v in e.verts))}
    chains = []
    while remaining:
        degree = {}
        for edge in remaining:
            for vertex in edge.verts:
                degree[vertex] = degree.get(vertex, 0)+1
        if max(degree.values()) > 2:
            raise ValueError(f'{obj.name}: branched fringe boundary')
        endpoints = [v for v, d in degree.items() if d == 1]
        current = min(endpoints or list(degree), key=lambda v: v.index)
        segments = []
        while True:
            edge = next((e for e in current.link_edges if e in remaining), None)
            if edge is None:
                break
            remaining.remove(edge)
            following = edge.other_vert(current)
            a, b = obj.matrix_world @ current.co, obj.matrix_world @ following.co
            tangent = (b-a).normalized()
            center = obj.matrix_world @ edge.link_faces[0].calc_center_median()
            inward = center-(a+b)/2
            inward = (inward-tangent*inward.dot(tangent)).normalized()
            normal = (obj.matrix_world.to_3x3() @ edge.link_faces[0].normal).normalized()
            segments.append((np.array(a), np.array(b), np.array(inward), np.array(normal)))
            current = following
        chains.append(segments)
    bm.free()
    return chains


def measured_coverage(obj, chains, root_pairs=None):
    covered = 0.
    total = 0.
    records = []
    for index, chain in enumerate(chains):
        starts = np.array([s[0] for s in chain])
        delta = np.array([s[1]-s[0] for s in chain])
        lengths = np.linalg.norm(delta, axis=1)
        distance = np.r_[0., lengths.cumsum()]
        records.append((starts, delta, lengths, distance))
        total += distance[-1]
    intervals = [[] for _ in chains]
    roots = root_pairs if root_pairs is not None else [sorted(face.vertices)[:2] for face in obj.data.polygons]
    for ids in roots:
        a, b = [np.array(obj.matrix_world @ obj.data.vertices[i].co) for i in ids]
        root = (a+b)/2
        nearest = None
        for index, (starts, delta, lengths, distance) in enumerate(records):
            t = np.clip(np.einsum('ij,ij->i', root-starts, delta)/lengths**2, 0, 1)
            residual = np.linalg.norm(root-starts-t[:, None]*delta, axis=1)
            j = int(residual.argmin())
            if nearest is None or residual[j] < nearest[0]:
                s = distance[j]+t[j]*lengths[j]
                width = abs(float((b-a) @ (delta[j]/lengths[j])))
                nearest = (residual[j], index, max(0., s-width/2), min(distance[-1], s+width/2))
        _, index, lo, hi = nearest
        intervals[index].append((lo, hi))
    for runs in intervals:
        end = 0.
        for lo, hi in sorted(runs):
            covered += max(0., hi-max(lo, end))
            end = max(end, hi)
    return dict(boundary_length_m=float(total), covered_root_length_m=float(covered),
                authored_coverage=float(covered/total), method='union of card-root projections onto actual lip arclength')


def spaced_cards(obj, mat, seed, wool, blockers, group_name=None, tuft_mat=None):
    chains = boundary_chains(obj, group_name)
    if not chains:
        raise ValueError(f'{obj.name}: no {group_name or "open"} boundary')
    contacts = CardContacts(blockers)
    rng = np.random.default_rng(seed)
    vertices, faces, variants, offsets, extents = [], [], [], [], []
    uv_faces, root_pairs, soft_faces = [], [], []
    soft = bool(obj.get('pass11_wear'))
    omitted = 0
    for chain in chains:
        lengths = np.array([np.linalg.norm(s[1]-s[0]) for s in chain])
        distance = np.r_[0., lengths.cumsum()]
        spacing = .0095 if group_name == 'Seam allowance' else .016 if soft and group_name == 'Long wool fringe' else .011
        count = max(1, int(round(distance[-1]/spacing)))
        stride = distance[-1]/count
        for station in (np.arange(count)+.5)*stride:
            j = min(len(chain)-1, np.searchsorted(distance, station, side='right')-1)
            a, b, inward, normal = chain[j]
            point = Vector(a+(b-a)*((station-distance[j])/lengths[j]))
            tangent = Vector(b-a).normalized()
            outward = -Vector(inward)
            normal = Vector(normal)
            if obj.name.startswith('FallenHem_') and normal.z < 0:
                normal.negate()
            width = min(float(rng.uniform(.008, .012)), .9*stride)
            torn_allowance = group_name == 'Seam allowance' and bool(obj.get('pass10_wear'))
            minimum_length = .005 if torn_allowance else .003 if wool else .002
            mean_length = .009 if torn_allowance else .007 if wool else .004
            maximum_length = .014 if torn_allowance else .018 if wool else .006
            extent = float(np.clip(rng.lognormal(np.log(mean_length), .4),
                                   minimum_length, maximum_length))
            if group_name == 'Long wool fringe' and point.z > -.4:
                extent = min(extent, .006)
            curled = soft and (group_name == 'Seam allowance' or
                               (group_name == 'Long wool fringe' and point.z > -.4))
            if curled:
                minimum_length = .002
                extent = float(rng.uniform(.0025, .0045))
                if group_name == 'Long wool fringe':
                    width = min(float(rng.uniform(.012, .015)), .9*stride)
            droop = float(rng.uniform(0, math.radians(35)))
            twist = float(rng.uniform(-.15, .15))
            direction = (outward*math.cos(droop)+Vector((0, 0, -1))*math.sin(droop)).normalized()
            placement = None
            for side_normal in [normal, -normal]:
                sideways = tangent*math.cos(twist)+side_normal*math.sin(twist)
                for extra in [0., .0005, .001, .002, .003]:
                    offset = abs(math.sin(twist))*width/2+.0003+extra
                    root = point-outward*.0012+side_normal*offset
                    for tail_direction in [direction, (direction+side_normal*.4).normalized()]:
                        for factor in [1., .75, .5]:
                            length = max(minimum_length, extent*factor)
                            tip = root+tail_direction*length
                            if curled:
                                from soft_tuft import tuft_sections
                                sections = tuft_sections(root, tail_direction, sideways, side_normal, width, length)
                            else:
                                sections = np.array([[root-sideways*width/2, root+sideways*width/2],
                                                     [tip-sideways*width/2, tip+sideways*width/2]])
                            quads = [[a[0], a[1], b[1], b[0]] for a, b in zip(sections, sections[1:])]
                            if all(contacts.clear(quad) for quad in quads):
                                placement = sections
                                break
                        if placement is not None:
                            break
                    if placement is not None:
                        break
                if placement is not None:
                    break
            if placement is None:
                omitted += 1
                continue
            base = len(vertices)
            variant = int(rng.integers(8))
            root_pairs.append((base, base+1))
            if not curled:
                a, b = placement
                quad = [a[0], a[1], b[1], b[0]]
                contacts.add(quad)
                vertices.extend(quad)
                faces.append((base, base+1, base+2, base+3))
                soft_faces.append(False)
                uv_faces.append([(0, variant/8), (1, variant/8),
                                 (1, (variant+1)/8), (0, (variant+1)/8)])
            else:
                vertices.extend(placement.reshape(-1, 3))
                for row, (a, b) in enumerate(zip(placement, placement[1:])):
                    contacts.add([a[0], a[1], b[1], b[0]])
                    start = base+2*row
                    faces.append((start, start+1, start+3, start+2))
                    soft_faces.append(True)
                    lo, hi = row/(len(placement)-1), (row+1)/(len(placement)-1)
                    uv_faces.append([(0, (variant+lo)/8), (1, (variant+lo)/8),
                                     (1, (variant+hi)/8), (0, (variant+hi)/8)])
            variants.append(variant)
            offsets.append(offset)
            extents.append(length)
    result = new_object(obj.name+'_Fringe', vertices, faces, mat)
    # Face-normal recalculation can reverse a disconnected card. Preserve its
    # root/tip UV meaning by vertex identity, independently of winding.
    if tuft_mat is not None:
        result.data.materials.append(tuft_mat)
    for polygon in result.data.polygons:
        polygon.material_index = int(tuft_mat is not None and soft_faces[polygon.index])
        coordinates = dict(zip(faces[polygon.index], uv_faces[polygon.index]))
        for i in polygon.loop_indices:
            result.data.uv_layers.active.data[i].uv = coordinates[result.data.loops[i].vertex_index]
    report = measured_coverage(result, chains, root_pairs)
    report.update(cards=len(root_pairs), triangles=len(faces)*2, omitted_contacts=omitted,
                  maximum_root_offset_m=max(offsets, default=0.), sat_checked=True,
                  extent_min_max_m=[min(extents, default=0.), max(extents, default=0.)])
    report['coverage_pass'] = report['authored_coverage'] >= .70
    return result, report
