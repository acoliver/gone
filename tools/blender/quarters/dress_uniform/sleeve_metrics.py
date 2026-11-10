"""Measure a pressed sleeve in the cross-section visible to the close camera."""
import numpy as np
import trimesh

def section_ratio(points, axis, view):
    axis = np.asarray(axis, dtype=float)/np.linalg.norm(axis)
    depth = np.asarray(view, dtype=float)-axis*np.dot(view, axis)
    depth /= np.linalg.norm(depth)
    width = np.cross(axis, depth)
    spans = np.ptp(np.asarray(points) @ np.column_stack([width, depth]), axis=0)
    if spans[0] <= 0:
        raise ValueError('Sleeve section has no camera-visible width')
    return dict(width_m=float(spans[0]), depth_m=float(spans[1]),
                ratio=float(spans[1]/spans[0]))


def pressed_sections(vertices, faces, pattern_uv, camera_position):
    face_uv = np.asarray(pattern_uv).mean(1)
    left = (face_uv[:, 0] > 1.09) & (face_uv[:, 0] < 1.56)
    sleeve = trimesh.Trimesh(vertices, faces[left], process=False)
    sleeve.remove_unreferenced_vertices()
    axis = np.linalg.svd(sleeve.vertices-sleeve.vertices.mean(0))[2][0]
    sections = []
    for station in [.25, .5, .75]:
        selected = left & (np.abs(face_uv[:, 1]-station) < .05)
        ids = np.unique(faces[selected])
        if not len(ids):
            raise ValueError(f'Missing sleeve station {station}')
        origin = vertices[ids].mean(0)
        section = sleeve.section(plane_origin=origin, plane_normal=axis)
        if section is None:
            raise ValueError(f'No sleeve cross-section at {station}')
        view = np.asarray(camera_position)-origin
        item = section_ratio(section.vertices, axis, view)
        item.update(pattern_station=station, origin_m=origin.tolist())
        sections.append(item)
    return dict(ratio=max(item['ratio'] for item in sections), sections=sections,
                camera_position_blender_m=np.asarray(camera_position).tolist(),
                method='maximum camera-ray depth / width of transverse sections at 25%, 50%, 75% pattern length')
