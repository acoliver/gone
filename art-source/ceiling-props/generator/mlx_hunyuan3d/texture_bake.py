"""Project multi-view images onto a mesh's UV atlas.

This is the non-neural half of Hunyuan3D-Paint: once the paint model has produced a set of
images of the object from known viewpoints, they have to be baked into a single texture.
Upstream does this with a CUDA rasteriser; this uses mlx_hunyuan3d.rasterizer, which is
portable and produces the same (face index, barycentric) output.

The method is the usual one:

  1. Rasterise the mesh IN UV SPACE, giving for every texel the face it belongs to and its
     barycentric coordinates - hence its 3D position and surface normal.
  2. For each camera, project those texel positions into that view and depth-test them
     against the view's own depth buffer, so texels on the far side of the model are
     rejected rather than smeared with whatever is in front of them.
  3. Blend the views, weighting each by how squarely it faces the surface. A camera looking
     edge-on at a triangle sees it stretched across very few pixels, so its colour there is
     unreliable; cosine weighting suppresses that automatically.
"""

from __future__ import annotations

import numpy as np

from .rasterizer import interpolate, look_at_screen, rasterize


def unwrap(vertices: np.ndarray, faces: np.ndarray, return_vertex_map: bool = False):
    """UV-unwrap with xatlas. Returns (vertices, faces, uvs) re-indexed to the atlas.

    xatlas splits vertices along UV seams, so the mesh is re-indexed and the returned arrays
    are NOT the ones passed in.

    With return_vertex_map=True also returns the atlas->input vertex index map. That map is
    what lets a caller re-express the atlas mesh in a DIFFERENT coordinate frame - notably
    the frame the caller supplied, rather than the mirrored/axis-swapped paint frame.
    """
    import xatlas

    vmapping, indices, uvs = xatlas.parametrize(vertices, faces)
    result = (vertices[vmapping], np.asarray(indices, dtype=np.int64), np.asarray(uvs))
    if return_vertex_map:
        return (*result, np.asarray(vmapping, dtype=np.int64))
    return result


def _uv_to_screen(uvs: np.ndarray, texture_size: int) -> np.ndarray:
    """UV coordinates as screen-space vertices for the rasteriser (z is unused, set flat)."""
    screen = np.zeros((uvs.shape[0], 3), dtype=np.float64)
    screen[:, 0] = uvs[:, 0] * texture_size
    # Image rows run top-down while v runs bottom-up.
    screen[:, 1] = (1.0 - uvs[:, 1]) * texture_size
    return screen


def bake(
    vertices: np.ndarray,
    faces: np.ndarray,
    uvs: np.ndarray,
    views: list[dict],
    texture_size: int = 1024,
    ortho_scale: float = 1.2,
    depth_eps: float = 2e-3,
    # Upstream's bake_exp. A linear cosine lets a view that sees a surface almost edge-on
    # still contribute substantially, so the dominant view smears stretched, grazing-angle
    # content across side surfaces that a side view saw properly but was outvoted on.
    # Raising the power sharply suppresses oblique contributions.
    cos_power: float = 4.0,
    return_diagnostics: bool = False,
) -> tuple[np.ndarray, np.ndarray] | tuple[np.ndarray, np.ndarray, dict]:
    """Bake `views` into a texture.

    Each view is {"image": (H, W, 3) float in 0..1, "azimuth": deg, "elevation": deg}.
    Returns (texture (S, S, 3) float, filled mask (S, S) bool). When diagnostics are
    requested, a third result records the dominant source view, weights and pre-inpaint
    coverage so a visible region cannot be silently rescued by push-pull filling.
    """
    vertices = np.asarray(vertices, dtype=np.float64)
    faces = np.asarray(faces, dtype=np.int64)

    # 1. texel -> surface point and normal
    uv_screen = _uv_to_screen(uvs, texture_size)
    tex_find, tex_bary = rasterize(uv_screen, faces, (texture_size, texture_size))
    covered = tex_find > 0
    if not covered.any():
        raise ValueError("UV rasterisation produced no covered texels; check the unwrap")

    position = interpolate(vertices, tex_find, tex_bary, faces)
    normals = _vertex_normals(vertices, faces)
    normal = interpolate(normals, tex_find, tex_bary, faces)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True) + 1e-9

    accum = np.zeros((texture_size, texture_size, 3), dtype=np.float64)
    weight = np.zeros((texture_size, texture_size), dtype=np.float64)
    if return_diagnostics:
        dominant_view = np.full((texture_size, texture_size), -1, dtype=np.int16)
        dominant_weight = np.zeros((texture_size, texture_size), dtype=np.float32)
        view_coverage_counts = []

    flat_pos = position[covered]
    flat_nrm = normal[covered]
    flat_face = tex_find[covered]

    for view_index, view in enumerate(views):
        image = np.asarray(view["image"], dtype=np.float64)
        height, width = image.shape[:2]
        azimuth, elevation = float(view["azimuth"]), float(view.get("elevation", 0.0))
        # Upstream trusts the views unequally (front 1.0, back 0.5, sides 0.1, poles 0.05)
        # because the generated views are not equally reliable. Without this the poles,
        # which cover the most texels on a flat model, dominate the blend.
        view_weight = float(view.get("weight", 1.0))

        # Depth buffer for this camera, so occluded texels can be rejected.
        screen = look_at_screen(vertices, (height, width), azimuth, elevation, ortho_scale)
        find, bary = rasterize(screen, faces, (height, width))
        depth_buffer = interpolate(screen[:, 2:3], find, bary, faces)[..., 0]

        # Same transform applied to the texel points themselves.
        pts = look_at_screen(flat_pos, (height, width), azimuth, elevation, ortho_scale)
        px = np.floor(pts[:, 0]).astype(np.int64)
        py = np.floor(pts[:, 1]).astype(np.int64)
        ok = (px >= 0) & (px < width) & (py >= 0) & (py < height)
        cy = np.clip(py, 0, height - 1)
        cx = np.clip(px, 0, width - 1)
        hit_face = find[cy, cx]
        ok &= hit_face > 0

        # Occlusion test. Comparing the texel's depth against the depth buffer with a
        # fixed epsilon does not work: within a single pixel the surface depth varies by
        # far more than any sane tolerance at grazing angles, so almost every texel gets
        # rejected as occluded (measured: 0.18% of texels survived at 2e-3, which bakes an
        # essentially black texture). The rasteriser already reports which FACE won each
        # pixel, so identity is an exact test and needs no tuning. The depth comparison is
        # kept only as a fallback for the neighbouring-face case, where a texel legitimately
        # lands on a pixel won by an adjacent triangle.
        same_face = hit_face == flat_face
        near_depth = np.abs(pts[:, 2] - depth_buffer[cy, cx]) < depth_eps
        ok &= same_face | near_depth

        # Facing weight. Normals get the rotation only - look_at_screen also applies the
        # screen offset and scale, which is meaningless for a direction vector.
        view_normal = _rotate_only(flat_nrm, azimuth, elevation)
        facing = np.clip(-view_normal[:, 2], 0.0, 1.0) ** cos_power
        ok &= facing > 1e-3
        if return_diagnostics:
            view_coverage_counts.append(int(ok.sum()))
        if not ok.any():
            continue

        contribution = facing[ok] * view_weight
        sample = image[py[ok], px[ok]]

        idx = np.where(covered)
        sel = (idx[0][ok], idx[1][ok])
        np.add.at(accum, sel, sample * contribution[:, None])
        np.add.at(weight, sel, contribution)
        if return_diagnostics:
            previous = dominant_weight[sel]
            better = contribution > previous
            dominant_weight[sel[0][better], sel[1][better]] = contribution[better]
            dominant_view[sel[0][better], sel[1][better]] = view_index

    filled = weight > 1e-6
    texture = np.zeros_like(accum)
    texture[filled] = accum[filled] / weight[filled][:, None]
    if return_diagnostics:
        diagnostics = {
            "covered": covered,
            "filled": filled,
            "total_weight": weight.astype(np.float32),
            "dominant_view": dominant_view,
            "dominant_weight": dominant_weight,
            "view_coverage_counts": np.asarray(view_coverage_counts, dtype=np.int64),
        }
        return texture, filled, diagnostics
    return texture, filled


def _rotate_only(vectors: np.ndarray, azimuth: float, elevation: float) -> np.ndarray:
    ar, er = np.radians(azimuth), np.radians(elevation)
    ca, sa = np.cos(ar), np.sin(ar)
    ce, se = np.cos(er), np.sin(er)
    rot_y = np.array([[ca, 0.0, sa], [0.0, 1.0, 0.0], [-sa, 0.0, ca]])
    rot_x = np.array([[1.0, 0.0, 0.0], [0.0, ce, -se], [0.0, se, ce]])
    out = np.asarray(vectors, dtype=np.float64) @ rot_y.T @ rot_x.T
    out[:, 2] = -out[:, 2]  # match look_at_screen's depth convention
    return out


def _vertex_normals(vertices: np.ndarray, faces: np.ndarray) -> np.ndarray:
    normals = np.zeros_like(vertices)
    tris = vertices[faces]
    face_n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    for i in range(3):
        np.add.at(normals, faces[:, i], face_n)
    return normals / (np.linalg.norm(normals, axis=-1, keepdims=True) + 1e-9)


def _push_pull_fill(texture: np.ndarray, filled: np.ndarray) -> np.ndarray:
    """Fill unknown texels by pyramid (push-pull) interpolation.

    Iterative dilation is fine for a seam a few pixels wide, but these atlases can have
    LARGE unknown regions -- measured 22% of the Viper's flank texels, because the side
    cameras see those surfaces almost edge-on. Filling that by repeated dilation propagates
    colour inward from whichever boundary is nearest, which shows up as directional streaks
    and banding across the sides. Push-pull averages over progressively coarser levels
    instead, so a big hole gets a smooth low-frequency fill with no preferred direction.
    """
    colour = [texture * filled[..., None]]
    weight = [filled.astype(np.float64)]

    # Push: coarsen, carrying weights so unknown texels never contribute.
    while min(colour[-1].shape[:2]) > 1:
        c, w = colour[-1], weight[-1]
        h, wd = (c.shape[0] // 2) * 2, (c.shape[1] // 2) * 2
        c = c[:h, :wd].reshape(h // 2, 2, wd // 2, 2, c.shape[2]).sum(axis=(1, 3))
        w = w[:h, :wd].reshape(h // 2, 2, wd // 2, 2).sum(axis=(1, 3))
        colour.append(c)
        weight.append(w)

    # Pull: fill each level's unknowns from the level above it.
    for level in range(len(colour) - 1, 0, -1):
        coarse_c, coarse_w = colour[level], weight[level]
        known = coarse_w > 1e-9
        upsampled = np.zeros_like(colour[level - 1])
        up_w = np.zeros_like(weight[level - 1])
        avg = np.zeros_like(coarse_c)
        avg[known] = coarse_c[known] / coarse_w[known][:, None]
        rep_c = np.repeat(np.repeat(avg, 2, axis=0), 2, axis=1)
        rep_w = np.repeat(np.repeat(known.astype(np.float64), 2, axis=0), 2, axis=1)
        h = min(upsampled.shape[0], rep_c.shape[0])
        wd = min(upsampled.shape[1], rep_c.shape[1])
        upsampled[:h, :wd] = rep_c[:h, :wd]
        up_w[:h, :wd] = rep_w[:h, :wd]

        fine_w = weight[level - 1]
        missing = fine_w <= 1e-9
        colour[level - 1] = np.where(
            missing[..., None], upsampled * up_w[..., None], colour[level - 1])
        weight[level - 1] = np.where(missing, up_w, fine_w)

    out = texture.copy()
    final_w = weight[0]
    fill = (~filled) & (final_w > 1e-9)
    out[fill] = colour[0][fill] / final_w[fill][:, None]
    return out


def inpaint(texture: np.ndarray, filled: np.ndarray, iterations: int = 4) -> np.ndarray:
    """Fill unbaked texels, then bleed a few pixels past the chart edges.

    Two different problems, so two steps: push-pull handles large unobserved regions
    smoothly, and a short dilation afterwards covers the narrow inter-chart gutters that
    bilinear sampling reaches into (otherwise chart edges pull in black and read as dark
    seams on the model).
    """
    out = _push_pull_fill(texture, filled)
    known = filled.copy()
    for _ in range(iterations):
        if known.all():
            break
        total = np.zeros_like(out)
        count = np.zeros(known.shape, dtype=np.float64)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            total += np.roll(out, (dy, dx), axis=(0, 1)) * np.roll(
                known, (dy, dx), axis=(0, 1))[..., None]
            count += np.roll(known, (dy, dx), axis=(0, 1))
        grow = (~known) & (count > 0)
        out[grow] = total[grow] / count[grow][:, None]
        known |= grow
    return out
