"""Fray the fallen wool's opaque straight edges and account for the lost fibre."""
import numpy as np

from opacity_bake import opacity_bake


def lost_area(obj, image):
    width, height = image.size
    pixels = np.empty(width*height*4, np.float32)
    image.pixels.foreach_get(pixels)
    pixels = pixels.reshape(height, width, 4)[:, :, 0]
    positions = np.array([obj.matrix_world @ v.co for v in obj.data.vertices])
    obj.data.calc_loop_triangles()
    uv = obj.data.uv_layers['BakeUV'].data
    area = 0.
    for triangle in obj.data.loop_triangles:
        corners = np.array([uv[i].uv[:] for i in triangle.loops])*[width, height]
        lo = np.maximum([0, 0], np.floor(corners.min(0)).astype(int))
        hi = np.minimum([width-1, height-1], np.ceil(corners.max(0)).astype(int))
        x, y = np.meshgrid(np.arange(lo[0], hi[0]+1)+.5, np.arange(lo[1], hi[1]+1)+.5)
        a, b, c = corners
        determinant = np.linalg.det(np.array([b-a, c-a]))
        if abs(determinant) < 1e-12:
            continue
        v = ((x-a[0])*(c[1]-a[1])-(y-a[1])*(c[0]-a[0]))/determinant
        w = ((b[0]-a[0])*(y-a[1])-(b[1]-a[1])*(x-a[0]))/determinant
        inside = (v >= 0) & (w >= 0) & (v+w <= 1)
        tile = pixels[lo[1]:hi[1]+1, lo[0]:hi[0]+1]
        missing = int(np.sum(inside & (tile < .5)))
        world = positions[np.array(triangle.vertices)]
        physical_area = np.linalg.norm(np.cross(world[1]-world[0], world[2]-world[0]))*.5
        area += missing*physical_area/(abs(determinant)*.5)
    return float(area)


def fray(sheet, directory, seed):
    image, report = opacity_bake(sheet, directory/f'{sheet.name.lower()}_opacity.png',
                                 size=1024, seed=seed, gain=1.5)
    report['lost_area_m2'] = lost_area(sheet, image)
    return image, report
