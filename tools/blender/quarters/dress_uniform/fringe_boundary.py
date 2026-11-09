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


def measured_coverage(obj, chains):
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
    for face in obj.data.polygons:
        a, b = [np.array(obj.matrix_world @ obj.data.vertices[i].co) for i in sorted(face.vertices)[:2]]
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


def spaced_cards(obj, mat, seed, wool, blockers, group_name=None):
    chains = boundary_chains(obj, group_name)
    if not chains:
        raise ValueError(f'{obj.name}: no {group_name or "open"} boundary')
    contacts = CardContacts(blockers)
    rng = np.random.default_rng(seed)
    vertices, faces, variants, offsets, extents = [], [], [], [], []
    omitted = 0
    for chain in chains:
        lengths = np.array([np.linalg.norm(s[1]-s[0]) for s in chain])
        distance = np.r_[0., lengths.cumsum()]
        spacing = .0095 if group_name == 'Seam allowance' else .011
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
            minimum_length = .003 if wool else .002
            extent = float(np.clip(rng.lognormal(np.log(.007 if wool else .004), .4),
                                   minimum_length, .018 if wool else .006))
            if group_name == 'Long wool fringe' and point.z > -.4:
                extent = min(extent, .006)
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
                            quad = [root-sideways*width/2, root+sideways*width/2,
                                    tip+sideways*width/2, tip-sideways*width/2]
                            if contacts.clear(quad):
                                placement = quad
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
            contacts.add(placement)
            base = len(vertices)
            vertices.extend(placement)
            faces.append((base, base+1, base+2, base+3))
            variants.append(int(rng.integers(8)))
            offsets.append(offset)
            extents.append(length)
    result = new_object(obj.name+'_Fringe', vertices, faces, mat)
    # Face-normal recalculation can reverse a disconnected card. Preserve its
    # root/tip UV meaning by vertex identity, independently of winding.
    for polygon in result.data.polygons:
        variant = variants[polygon.index]
        for i in polygon.loop_indices:
            corner = result.data.loops[i].vertex_index % 4
            result.data.uv_layers.active.data[i].uv = (
                1. if corner in [1, 2] else 0.,
                (variant+(corner >= 2))/8)
    report = measured_coverage(result, chains)
    report.update(cards=len(faces), triangles=len(faces)*2, omitted_contacts=omitted,
                  maximum_root_offset_m=max(offsets, default=0.), sat_checked=True,
                  extent_min_max_m=[min(extents, default=0.), max(extents, default=0.)])
    report['coverage_pass'] = report['authored_coverage'] >= .70
    return result, report
