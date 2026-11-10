"""Offline constrained cable sweeps; all coordinates are metres in bay-local Y-up."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

import numpy as np
import trimesh


@dataclass(frozen=True)
class CableClass:
    name: str
    diameter: float
    bend_radius: float
    strand_count: int = 1
    strand_gap: float = 0.002


POWER = CableClass("power", 0.024, 0.144, 2, 0.003)
DATA = CableClass("data", 0.006, 0.048, 6, 0.002)


def _unit(v: np.ndarray) -> np.ndarray:
    length = float(np.linalg.norm(v))
    if length < 1e-10:
        raise ValueError("route contains coincident points")
    return v / length


def fillet_polyline(points: Sequence[Sequence[float]], minimum_radius: float, samples_per_arc: int = 16) -> np.ndarray:
    """Replace corners with tangent circular arcs, rejecting bends below the stated radius."""
    p = np.asarray(points, dtype=float)
    if p.ndim != 2 or p.shape[1] != 3 or len(p) < 2 or not np.isfinite(p).all():
        raise ValueError("route must be finite Nx3 points")
    result = [p[0]]
    for i in range(1, len(p) - 1):
        before, corner, after = p[i - 1:i + 2]
        incoming, outgoing = _unit(corner - before), _unit(after - corner)
        angle = math.acos(float(np.clip(np.dot(incoming, outgoing), -1, 1)))
        if angle < 1e-7:
            result.append(corner)
            continue
        if math.pi - angle < 1e-7:
            raise ValueError("180-degree route reversal cannot be filleted")
        tangent = minimum_radius * math.tan(angle / 2)
        if tangent >= min(np.linalg.norm(corner - before), np.linalg.norm(after - corner)):
            raise ValueError("segments too short for minimum-radius bend")
        a = corner - incoming * tangent
        b = corner + outgoing * tangent
        normal = _unit(np.cross(incoming, outgoing))
        center = a + np.cross(normal, incoming) * minimum_radius
        va, vb = a - center, b - center
        sweep = math.atan2(float(np.dot(normal, np.cross(va, vb))), float(np.dot(va, vb)))
        result.append(a)
        for j in range(1, samples_per_arc):
            theta = sweep * j / samples_per_arc
            result.append(center + va * math.cos(theta) + np.cross(normal, va) * math.sin(theta) + normal * np.dot(normal, va) * (1 - math.cos(theta)))
        result.append(b)
    result.append(p[-1])
    return np.asarray(result)


def add_controlled_sag(points: Sequence[Sequence[float]], supports: Sequence[int], sag: float) -> np.ndarray:
    """Apply parabolic slack only between explicit support indices on otherwise straight spans."""
    p = np.asarray(points, dtype=float).copy()
    if sag < 0 or any(i < 0 or i >= len(p) for i in supports):
        raise ValueError("invalid sag or support index")
    for start, end in zip(supports, supports[1:]):
        if end <= start + 1:
            continue
        axis = _unit(p[end] - p[start])
        up = np.array([0., 1., 0.])
        normal = up - axis * np.dot(up, axis)
        if np.linalg.norm(normal) < 1e-8:
            normal = np.cross(axis, np.array([1., 0., 0.]))
        normal = _unit(normal)
        for i in range(start + 1, end):
            t = (i - start) / (end - start)
            p[i] += normal * (4 * sag * t * (1 - t))
    return p


def _frames(path: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    tangents = np.empty_like(path)
    tangents[0] = _unit(path[1] - path[0]); tangents[-1] = _unit(path[-1] - path[-2])
    for i in range(1, len(path)-1): tangents[i] = _unit(path[i+1] - path[i-1])
    ref = np.array([0., 1., 0.])
    if abs(float(np.dot(ref, tangents[0]))) > .92: ref = np.array([1., 0., 0.])
    normals = np.empty_like(path); binormals = np.empty_like(path)
    normals[0] = _unit(ref - tangents[0] * np.dot(ref, tangents[0]))
    binormals[0] = _unit(np.cross(tangents[0], normals[0]))
    for i in range(1, len(path)):
        axis = np.cross(tangents[i-1], tangents[i]); sine = np.linalg.norm(axis)
        if sine > 1e-9:
            axis /= sine
            angle = math.atan2(sine, float(np.dot(tangents[i-1], tangents[i])))
            normals[i] = normals[i-1]*math.cos(angle)+np.cross(axis,normals[i-1])*math.sin(angle)+axis*np.dot(axis,normals[i-1])*(1-math.cos(angle))
        else: normals[i] = normals[i-1]
        normals[i] = _unit(normals[i] - tangents[i] * np.dot(normals[i], tangents[i]))
        binormals[i] = _unit(np.cross(tangents[i], normals[i]))
    return normals, binormals


def sweep_strands(points: Sequence[Sequence[float]], cable: CableClass, sides: int = 12) -> list[trimesh.Trimesh]:
    """Return distinct watertight strand meshes with transported frames and outward normals."""
    centerline = fillet_polyline(points, cable.bend_radius)
    normals, binormals = _frames(centerline)
    pitch = cable.diameter + cable.strand_gap
    radius = cable.diameter / 2
    meshes = []
    for strand in range(cable.strand_count):
        angle = 2 * math.pi * strand / cable.strand_count
        offset = (normals * math.cos(angle) + binormals * math.sin(angle)) * (pitch if cable.strand_count > 1 else 0)
        centers = centerline + offset
        vertices = []
        for center, n, b in zip(centers, normals, binormals):
            for side in range(sides):
                theta = 2 * math.pi * side / sides
                vertices.append(center + radius * (n * math.cos(theta) + b * math.sin(theta)))
        faces = []
        for ring in range(len(centers)-1):
            for side in range(sides):
                a=ring*sides+side; c=ring*sides+(side+1)%sides
                faces.extend([[a,c,a+sides],[c,c+sides,a+sides]])
        # End caps use separate center vertices, oriented outward along tangent.
        start_cap, end_cap = len(vertices), len(vertices)+1
        vertices.extend([centers[0], centers[-1]])
        for side in range(sides):
            nxt=(side+1)%sides
            faces.extend([[start_cap,nxt,side],[end_cap,(len(centers)-1)*sides+side,(len(centers)-1)*sides+nxt]])
        mesh=trimesh.Trimesh(vertices=np.asarray(vertices), faces=np.asarray(faces), process=False)
        mesh.fix_normals()
        uv=np.empty((len(vertices),2),dtype=float)
        for ring in range(len(centers)):
            uv[ring*sides:(ring+1)*sides,0]=np.linspace(0.,1.,len(centers))[ring]
            uv[ring*sides:(ring+1)*sides,1]=np.arange(sides)/sides
        uv[start_cap:end_cap+1]=[[0.,.5],[1.,.5]]
        mesh.visual=trimesh.visual.TextureVisuals(uv=uv)
        mesh.metadata.update({"material_group":cable.name,"strand_index":strand,"jacket_od_m":cable.diameter})
        meshes.append(mesh)
    return meshes


def support_stations(points: Sequence[Sequence[float]], maximum_pitch: float) -> np.ndarray:
    if maximum_pitch <= 0: raise ValueError("maximum support pitch must be positive")
    p=np.asarray(points,dtype=float); lengths=np.linalg.norm(np.diff(p,axis=0),axis=1)
    cumulative=np.r_[0.,np.cumsum(lengths)]
    stations=np.arange(0.,cumulative[-1],maximum_pitch).tolist()+[float(cumulative[-1])]
    return np.array([np.array([np.interp(s,cumulative,p[:,axis]) for axis in range(3)]) for s in stations])
