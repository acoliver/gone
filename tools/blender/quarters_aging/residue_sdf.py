"""Closed powder/crust isosurfaces and fragments cut from the same height-field SDF.

Run with the Hunyuan Python, not Blender's bundled Python. NPZ is the boundary
between scipy/skimage construction and Blender simulation/baking.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.ndimage import binary_fill_holes, distance_transform_edt, gaussian_filter, label, map_coordinates
from scipy.spatial import cKDTree
from skimage.measure import marching_cubes


def height_field(x, y, seed):
    rng = np.random.default_rng(seed)
    xx, yy = np.meshgrid(x, y, indexing='ij')
    h = np.full(xx.shape, .006)
    for _ in range(24):
        cx = rng.uniform(x[0]+.02, x[-1]-.02)
        cy = rng.uniform(y[0], y[-1]) if rng.random() < .4 else rng.uniform(y[-1]-.20, y[-1])
        radius = rng.uniform(.015, .045)
        h += rng.uniform(.008, .025)*np.exp(-((xx-cx)**2+(yy-cy)**2)/(2*radius**2))
    h = .004+.016*(1-np.exp(-np.maximum(h-.004, 0)/.016))
    spacing = x[1]-x[0]
    for wavelength, amplitude in [(.040, .005), (.012, .004), (.004, .0014)]:
        noise = gaussian_filter(rng.normal(size=h.shape), wavelength/spacing/4)
        h += noise/max(float(noise.std()), 1e-8)*amplitude
    sites = rng.uniform([x[0], y[0]], [x[-1], y[-1]], (50, 2))
    distances = cKDTree(sites).query(np.c_[xx.ravel(), yy.ravel()], k=2)[0]
    crack = (distances[:, 1]-distances[:, 0]).reshape(h.shape)
    h -= rng.uniform(.003, .008)*np.exp(-(crack/.002)**2)
    # Taper to zero at the footprint so the residue has no vertical box walls.
    border = np.minimum.reduce([xx-x[0], x[-1]-xx, yy-y[0], y[-1]-yy])
    h = .006+.020*np.tanh(np.logaddexp(0, (h-.006)/.002)*.002/.020)
    h *= np.clip(border/.018, 0, 1)
    return h, sites


def underside(x, y):
    x, y = np.broadcast_arrays(x, y)
    # Broad curvature must survive the 700-triangle target, including underneath.
    variation = .004*(.5+.25*np.sin(x*95)+.25*np.sin(y*110+x*47))
    variation += .0005*np.sin(y*310)*np.sin(x*270)
    return .0005+variation


def field(width=.66, depth=.70, voxel=.002, seed=9501):
    x = np.arange(-width/2-.01, width/2+.01+voxel/2, voxel, dtype=np.float32)
    y = np.arange(-depth/2-.01, depth/2+.01+voxel/2, voxel, dtype=np.float32)
    z = np.arange(-.004, .085, voxel, dtype=np.float32)
    h, sites = height_field(x, y, seed)
    xx, yy = np.meshgrid(x, y, indexing='ij')
    zz = z[None, None, :]
    floor = underside(xx, yy)[:, :, None]
    sdf = np.maximum(zz-h[:, :, None], -zz+floor)
    sdf = np.maximum(sdf, np.minimum.reduce([xx-x[0], x[-1]-xx, yy-y[0], y[-1]-yy])[:, :, None]*-1+.002)
    rng = np.random.default_rng(seed+1)
    distances, nearest = cKDTree(sites).query(np.c_[xx.ravel(), yy.ravel()], k=2)
    chosen = rng.choice(len(sites), 8, replace=False)
    for cell in chosen:
        mask = nearest[:, 0].reshape(xx.shape) == cell
        tilt = rng.uniform(np.radians(5), np.radians(35))
        yaw = rng.uniform(0, 2*np.pi)
        plane = h+np.tan(tilt)*((xx-sites[cell, 0])*np.cos(yaw)+(yy-sites[cell, 1])*np.sin(yaw))
        half = rng.uniform(.0015, .003)
        slab = np.abs(zz-plane[:, :, None])-half
        slab = np.maximum(slab, zz-h[:, :, None]-.008)
        outline = np.where(mask, -(distances[:, 1]-distances[:, 0]).reshape(xx.shape)/2, .01)
        slab = np.maximum(slab, outline[:, :, None]+.001+.0004*np.sin(xx[:, :, None]*700))
        sdf = np.minimum(sdf, slab)
    # Close plate tips at the same domain bounds and floor as the powder.
    rear = np.clip((yy-.18)/.07, 0, 1)
    rear_ceiling = .011+.002*np.sin(xx*600)*np.sin(yy*700)
    sdf = np.maximum(sdf, zz-(.040*(1-rear)+rear_ceiling*rear)[:, :, None])
    sdf = np.maximum(sdf, -zz+floor)
    sdf[[0, -1], :, :] = .01
    sdf[:, [0, -1], :] = .01
    sdf[:, :, [0, -1]] = .01
    return sdf.astype(np.float32), np.array([x[0], y[0], z[0]]), voxel


def mesh_sdf(sdf, origin, voxel, level=.000013):
    vertices, faces, normals, _ = marching_cubes(sdf, level, spacing=(voxel,)*3, allow_degenerate=False)
    return vertices.astype(np.float64)+origin, faces, normals


def filled_proxy(sdf, origin, voxel):
    """Fill sub-surface pore tunnels for the low-poly collision/bake target."""
    level = .000013
    inside = sdf < level
    footprint = np.any(inside, axis=2)
    columns = np.argwhere(footprint)
    last = sdf.shape[2]-1-np.argmax(inside[:, :, ::-1], axis=2)[footprint]
    lower = sdf[columns[:,0], columns[:,1], last]
    upper = sdf[columns[:,0], columns[:,1], last+1]
    top = np.zeros(footprint.shape)
    top[footprint] = origin[2]+voxel*(last+(level-lower)/(upper-lower))
    holes = binary_fill_holes(footprint) & ~footprint
    nearest = distance_transform_edt(~footprint, return_distances=False, return_indices=True)
    top[holes] = top[nearest[0][holes], nearest[1][holes]]
    regions, _ = label(footprint | holes)
    largest = np.argmax(np.bincount(regions.ravel())[1:])+1
    footprint = regions == largest
    x = origin[0]+np.arange(sdf.shape[0])*voxel
    y = origin[1]+np.arange(sdf.shape[1])*voxel
    z = origin[2]+np.arange(sdf.shape[2])*voxel
    bottom = underside(x[:, None], y[None, :])
    # Sub-voxel sheets and narrow necks consume the collapse budget as handles.
    # Keep the collision envelope at least two Z cells thick. Normal and AO
    # still come from the pore-rich dense source.
    top = np.maximum(top, bottom+2*voxel)
    filled = np.maximum(z[None,None,:]-top[:,:,None], bottom[:,:,None]-z[None,None,:])
    filled[~footprint] = .01
    filled[:, :, [0,-1]] = .01
    # Keep float32 marching-cubes crossings away from grid corners. Otherwise
    # export/import vertex merging can identify distinct sub-micrometre tips.
    proxy_level = level+.0000005
    filled = np.clip(np.rint(filled/.000001)*.000001,
                     proxy_level-voxel, proxy_level+voxel)
    return mesh_sdf(filled, origin, voxel, level=proxy_level)


def fragments(sdf, origin, voxel, seed=9501, count=12):
    """Intersect one 60 mm residue patch with Voronoi columns and thin skin slabs."""
    rng = np.random.default_rng(seed)
    patch = np.array([.0, .18])
    sites = patch+rng.uniform(-.027, .027, (count, 2))
    fine = .0006
    x = np.arange(patch[0]-.03, patch[0]+.03, fine)
    y = np.arange(patch[1]-.03, patch[1]+.03, fine)
    z = np.arange(.001, .080, fine)
    xx, yy, zz = np.meshgrid(x, y, z, indexing='ij')
    coordinates = np.array([(xx-origin[0])/voxel, (yy-origin[1])/voxel, (zz-origin[2])/voxel])
    residue = map_coordinates(sdf, coordinates, order=1, mode='constant', cval=.1)
    result = []
    for i, site in enumerate(sites):
        cell = np.full(residue.shape, -1.)
        for j, other in enumerate(sites):
            if i == j:
                continue
            direction = other-site
            normal = direction/np.linalg.norm(direction)
            cell = np.maximum(cell, (xx-(site[0]+other[0])/2)*normal[0]+(yy-(site[1]+other[1])/2)*normal[1])
        # Retain a skin layer from the actual residue, not an invented sphere.
        top = np.max(np.where((cell < 0) & (residue < 0), zz, 0))
        fragment = np.maximum.reduce([residue, cell, top-.008-zz])
        fragment[[0, -1], :, :] = .01
        fragment[:, [0, -1], :] = .01
        fragment[:, :, [0, -1]] = .01
        if fragment.min() < 0:
            vertices, faces, normals = mesh_sdf(fragment, np.array([x[0], y[0], z[0]]), fine)
            centre = vertices.mean(0)
            result.append((vertices-centre, faces, normals))
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--seed', type=int, default=9501)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    sdf, origin, voxel = field(seed=a.seed)
    vertices, faces, normals = mesh_sdf(sdf, origin, voxel)
    gv, gf, _ = filled_proxy(sdf, origin, voxel)
    np.savez_compressed(a.out/'seat-residue.npz', vertices=vertices, faces=faces, normals=normals,
                        game_vertices=gv, game_faces=gf)
    library = fragments(sdf, origin, voxel, a.seed)
    for i, (v, f, n) in enumerate(library):
        np.savez_compressed(a.out/f'fragment-{i:02d}.npz', vertices=v, faces=f, normals=n)
    (a.out/'residue.json').write_text(json.dumps({'seed': a.seed, 'voxel_m': voxel,
        'dense_triangles': len(faces), 'templates': len(library),
        'bounds_m': [vertices.min(0).tolist(), vertices.max(0).tolist()]}, indent=2)+'\n')


if __name__ == '__main__':
    main()
