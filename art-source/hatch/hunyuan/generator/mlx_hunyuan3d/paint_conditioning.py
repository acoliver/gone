"""Render the normal and position maps that condition the paint model.

The paint UNet takes 12 latent channels: cat[noisy(4), normal(4), position(4)]. The last
eight come from VAE-encoded renders of the mesh itself, produced here with the portable
rasteriser rather than upstream's CUDA one.

Conventions follow MeshRender.render_normal / render_position exactly:

  * Normals are WORLD space, not camera space (upstream calls this use_abs_coor=True), and
    are area-weighted vertex normals, then encoded as (n + 1) * 0.5.
  * Position is 0.5 - vertex / scale_factor.
  * Background is white, applied through the visibility mask, NOT black. Getting this
    wrong biases every edge texel toward dark and shows up as a grubby rim on the bake.

Cameras are upstream's six candidate views, which unlike the shape model DO include
top and bottom - the paint model is not restricted to a single rotation axis.
"""

from __future__ import annotations

import numpy as np

from .rasterizer import interpolate, look_at_screen, rasterize

CANDIDATE_AZIMUTHS = (0.0, 90.0, 180.0, 270.0, 0.0, 180.0)
CANDIDATE_ELEVATIONS = (0.0, 0.0, 0.0, 0.0, 90.0, -90.0)
CANDIDATE_VIEW_WEIGHTS = (1.0, 0.1, 0.5, 0.1, 0.05, 0.05)

# Upstream's weights assume a CANONICALLY ORIENTED asset: azimuth 0 is the subject's front
# and the two +/-90 elevation views are its top and bottom, which matter least, hence 0.05.
#
# That assumption breaks for anything reconstructed from re-oriented views. Our ships are
# generated lying on their side (see the shape-stage fix), so after normalize_for_paint the
# azimuth cameras look along the HEIGHT and LENGTH axes, and the two elevation cameras look
# along the LATERAL axis -- they are the port and starboard FLANKS, the largest surfaces on
# the model, being weighted at 0.05. The result is that the flanks are barely baked (22% of
# their texels had no coverage at all) and the gap filler invents the rest, which is what
# reads as smeared patterns along the sides.
SIDE_LAID_VIEW_WEIGHTS = (1.0, 0.1, 0.5, 0.1, 0.8, 0.8)

# Upstream's camera-index encoding. The elevation buckets are separate embedding ranges,
# and polar views collapse 12 azimuth slots into 4 because azimuth means less overhead.
_ELEVATION_DIVISOR = {-20: 1, 0: 1, 20: 1, -90: 3, 90: 3}
_ELEVATION_OFFSET = {-20: 0, 0: 12, 20: 24, -90: 36, 90: 40}
MAX_NUM_REF_IMAGE = 5


def camera_info(azimuth: float, elevation: float) -> int:
    key = int(elevation)
    if key not in _ELEVATION_DIVISOR:
        raise ValueError(f"unsupported elevation {elevation}; "
                         f"expected one of {sorted(_ELEVATION_DIVISOR)}")
    return ((int(azimuth) // 30) + 9) % 12 // _ELEVATION_DIVISOR[key] + _ELEVATION_OFFSET[key]


def camera_labels(azimuths=CANDIDATE_AZIMUTHS, elevations=CANDIDATE_ELEVATIONS) -> np.ndarray:
    """Class-embedding indices, including the +MAX_NUM_REF_IMAGE shift the UNet applies."""
    return np.array([camera_info(a, e) for a, e in zip(azimuths, elevations)],
                    dtype=np.int32) + MAX_NUM_REF_IMAGE


SCALE_FACTOR = 1.15


def normalize_for_paint(vertices: np.ndarray, faces: np.ndarray | None = None):
    """Place a mesh the way upstream's MeshRender.set_mesh does.

    Two things matter and both are easy to get wrong:

    1. The mesh is scaled so its DIAMETER is scale_factor (1.15), i.e. max radius 0.575.
       The orthographic camera only spans 1.2 units, so normalising to radius 1.0 - the
       obvious choice, and what the shape pipeline does - puts most of the model outside
       the frustum. It does not error; the conditioning maps just come back cropped and
       the paint model produces flat, colourless output from them.
    2. Upstream then negates x and y and swaps y with z. That is a coordinate-convention
       change, and it decides which camera azimuth sees which side of the model.

    That second step has determinant -1: negating two axes preserves orientation, but the
    following swap does not, so the whole transform MIRRORS the mesh. Face winding is
    therefore reversed and every computed normal points inward. Nothing errors - the
    silhouettes are identical - but every facing test then rejects exactly the surfaces
    that are visible, and the texture bakes empty. Pass `faces` to get the winding fixed.
    """
    vertices = np.asarray(vertices, dtype=np.float64).copy()
    center = (vertices.max(axis=0) + vertices.min(axis=0)) / 2.0
    diameter = np.linalg.norm(vertices - center, axis=1).max() * 2.0
    vertices = (vertices - center) * (SCALE_FACTOR / max(float(diameter), 1e-9))

    vertices[:, [0, 1]] = -vertices[:, [0, 1]]
    vertices[:, [1, 2]] = vertices[:, [2, 1]]
    if faces is None:
        return vertices
    faces = np.asarray(faces, dtype=np.int64).copy()
    faces[:, [1, 2]] = faces[:, [2, 1]]
    return vertices, faces


def vertex_normals(vertices: np.ndarray, faces: np.ndarray) -> np.ndarray:
    """Area-weighted vertex normals, matching trimesh.geometry.mean_vertex_normals."""
    normals = np.zeros_like(vertices)
    tris = vertices[faces]
    # Not normalising the cross product leaves it proportional to triangle area, which is
    # what makes this an area-weighted mean.
    face_normals = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    for i in range(3):
        np.add.at(normals, faces[:, i], face_normals)
    lengths = np.linalg.norm(normals, axis=-1, keepdims=True)
    return normals / np.maximum(lengths, 1e-20)


def _render_attribute(vertices, faces, attribute, azimuth, elevation, resolution,
                      ortho_scale, background):
    screen = look_at_screen(vertices, (resolution, resolution), azimuth, elevation,
                            ortho_scale)
    findices, barycentric = rasterize(screen, faces, (resolution, resolution))
    values = interpolate(attribute, findices, barycentric, faces)
    mask = (findices > 0)[..., None].astype(np.float64)
    return values * mask + np.asarray(background, dtype=np.float64) * (1.0 - mask)


def render_normal_maps(vertices, faces, azimuths=CANDIDATE_AZIMUTHS,
                       elevations=CANDIDATE_ELEVATIONS, resolution: int = 512,
                       ortho_scale: float = 1.2, background=(1.0, 1.0, 1.0)):
    normals = vertex_normals(np.asarray(vertices, dtype=np.float64),
                             np.asarray(faces, dtype=np.int64))
    encoded = (normals + 1.0) * 0.5
    return [
        _render_attribute(vertices, faces, encoded, azimuth, elevation, resolution,
                          ortho_scale, background)
        for azimuth, elevation in zip(azimuths, elevations)
    ]


def render_position_maps(vertices, faces, azimuths=CANDIDATE_AZIMUTHS,
                         elevations=CANDIDATE_ELEVATIONS, resolution: int = 512,
                         ortho_scale: float = 1.2, background=(1.0, 1.0, 1.0)):
    vertices = np.asarray(vertices, dtype=np.float64)
    encoded = 0.5 - vertices / SCALE_FACTOR
    return [
        _render_attribute(vertices, faces, encoded, azimuth, elevation, resolution,
                          ortho_scale, background)
        for azimuth, elevation in zip(azimuths, elevations)
    ]
