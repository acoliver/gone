"""Remove sub-contact-size rest edges while retaining the cloth's UV panels."""
import bmesh
import numpy as np


def resolve_short_edges(obj, minimum=.0028):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    collapsed = 0
    for _ in range(12):
        occupied, selected = set(), []
        for edge in sorted(bm.edges, key=lambda e: e.calc_length()):
            if edge.calc_length() >= minimum:
                break
            if not any(v in occupied for v in edge.verts):
                selected.append(edge)
                occupied.update(edge.verts)
        if not selected:
            break
        collapsed += len(selected)
        bmesh.ops.collapse(bm, edges=selected, uvs=True)
    uv = bm.loops.layers.uv.active
    def panel(face):
        u = np.mean([loop[uv].uv.x for loop in face.loops])
        return 0 if u < .48 else 1 if u < 1 else 2 if u < 1.6 else 3
    edges = [e for e in bm.edges if len(e.link_faces) == 2 and
             panel(e.link_faces[0]) == panel(e.link_faces[1])]
    bmesh.ops.beautify_fill(bm, faces=list(bm.faces), edges=edges)
    bm.to_mesh(obj.data)
    bm.free()
    return {'minimum_edge_target_m': minimum, 'collapsed_edges': collapsed}
