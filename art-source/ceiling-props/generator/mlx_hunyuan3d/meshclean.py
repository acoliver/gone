"""Remove marching-cubes specks from a generated mesh.

Dense volume decoding leaves a handful of isolated 1-2 face fragments where the isosurface
grazes a voxel corner. They are invisible but they inflate the component count and stop a
mesh being watertight.

This is deliberately opt-in and deliberately conservative, because "small and disconnected"
does NOT mean "junk". The Viper's wingtip cannon pods come out as two separate components
of 1076 and 248 faces, sitting at mirrored positions either side of the hull; discarding
everything but the largest component would silently amputate them. Only fragments below an
explicit face count are dropped, and every one is reported so a bad threshold is visible
rather than silent.
"""

from __future__ import annotations

import trimesh


def prune_specks(mesh: trimesh.Trimesh, min_faces: int) -> tuple[trimesh.Trimesh, list[dict]]:
    """Drop connected components smaller than `min_faces`.

    Returns the cleaned mesh and a record of what was removed. The largest component is
    always kept regardless of the threshold, so an over-aggressive value cannot empty the
    mesh entirely.
    """
    if min_faces <= 0:
        return mesh, []

    parts = sorted(mesh.split(only_watertight=False), key=lambda p: -len(p.faces))
    if len(parts) <= 1:
        return mesh, []

    kept, removed = [parts[0]], []
    for part in parts[1:]:
        if len(part.faces) < min_faces:
            removed.append({
                "faces": len(part.faces),
                "centroid": part.centroid.round(4).tolist(),
                "extent": part.extents.round(4).tolist(),
            })
        else:
            kept.append(part)

    if not removed:
        return mesh, []
    return trimesh.util.concatenate(kept), removed


def report(removed: list[dict]) -> str:
    if not removed:
        return "  no components pruned"
    total = sum(item["faces"] for item in removed)
    lines = [f"  pruned {len(removed)} component(s), {total} faces:"]
    lines.extend(
        f"    {item['faces']:5d} faces  centroid={item['centroid']}  extent={item['extent']}"
        for item in removed
    )
    return "\n".join(lines)
