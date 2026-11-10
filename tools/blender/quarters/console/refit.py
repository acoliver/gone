"""Grow the accepted saved cages above their fixed deck; no guide rebuild (#129).

Run in Blender. Subsequent build.py exports read this edited saved source.
The scene version makes repeating this adjustment a no-op, including UV packing.
"""
import json
import math
from pathlib import Path
import sys

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'wardrobe'))
from batch_tools import unwrap

WIDTH = .874
HEIGHT = WIDTH * 10 / 16
DELTA = HEIGHT - .238
SLOPE = .6
RISE = DELTA / math.sqrt(1 + SLOPE**2)
UPPER_BORDER_TRIM = .018
HOUSING_TRIM = UPPER_BORDER_TRIM / math.sqrt(1 + SLOPE**2)
HEIGHT_AFTER_TRIM = .69 + RISE - HOUSING_TRIM
REFIT_VERSION = 1292


def trim_upper_border():
    objects = bpy.data.objects
    top = objects['BezelTop']
    top.location.z -= UPPER_BORDER_TRIM / 2
    for vertex in top.data.vertices:
        vertex.co.z *= (.030 - UPPER_BORDER_TRIM) / .030
    # Keep the glass, gasket, rivets and lower border fixed. Only the metal
    # above the glass changes, leaving a 12 mm top bar and 1 mm gasket gap.
    for name in ['BezelLeft', 'BezelRight']:
        for vertex in objects[name].data.vertices:
            above = max(0, vertex.co.z - HEIGHT / 2)
            vertex.co.z -= above * UPPER_BORDER_TRIM / .031
    for vertex in objects['ArmouredHousing'].data.vertices:
        x, y, z = vertex.co
        fraction = max(0, (z - .925) / (.69 + RISE - .925))
        front = -.045 + SLOPE * (z - .42) - .0256 * fraction
        front_weight = (.275 - y) / (.275 - front)
        vertex.co.z -= HOUSING_TRIM * fraction
        vertex.co.y -= SLOPE * HOUSING_TRIM * fraction * front_weight
    bpy.context.scene['console_refit'] = REFIT_VERSION


def apply_refit():
    objects = bpy.data.objects
    screen = objects['ScreenPlane']
    screen.location += screen.rotation_euler.to_matrix() @ Vector((0, 0, DELTA/2))
    for name, old in [('Display', .238), ('ScreenGasket', .244),
                      ('BezelLeft', .300), ('BezelRight', .300)]:
        obj = objects[name]
        for vertex in obj.data.vertices:
            vertex.co.z *= (old + DELTA) / old
    objects['BezelTop'].location.z += DELTA/2
    objects['BezelBottom'].location.z -= DELTA/2
    # Rivets are joined in bezel-local coordinates, with their own retained origin.
    rivets = objects['BezelRivets']
    frame = rivets.matrix_local.copy()
    for vertex in rivets.data.vertices:
        point = frame @ vertex.co
        point.z += DELTA/2 if point.z > 0 else -DELTA/2
        vertex.co = frame.inverted() @ point
    housing = objects['ArmouredHousing']
    mesh = bmesh.new()
    mesh.from_mesh(housing.data)
    # Add a cap transition so the unchanged .6 screen slope cannot invert the
    # head's thin upper edge against its fixed rear depth at the taller height.
    transition = .42 + (.925 - .42) * .27 / (.27 + RISE)
    bmesh.ops.bisect_plane(mesh, geom=list(mesh.verts)+list(mesh.edges)+list(mesh.faces),
                          plane_co=(0, 0, transition), plane_no=(0, 0, 1), dist=1e-7)
    mesh.to_mesh(housing.data)
    mesh.free()
    for vertex in housing.data.vertices:
        x, y, z = vertex.co
        fraction = max(0, (z - .42) / .27)
        front = -.045 + SLOPE * (z - .42)
        front_weight = (.275 - y) / (.275 - front)
        z += RISE * fraction
        y += SLOPE * RISE * fraction * front_weight
        if z > .925:
            y -= .0256 * (z - .925) / (.69 + RISE - .925) * front_weight
        vertex.co = (x, y, z)
    trim_upper_border()


def refit():
    source = HERE / 'console-working.blend'
    bpy.ops.wm.open_mainfile(filepath=str(source))
    version = bpy.context.scene.get('console_refit')
    if version == REFIT_VERSION:
        print('Console #129 saved-source refit already applied')
        return
    if version == 129:
        trim_upper_border()
    else:
        apply_refit()
    asset = [o for o in bpy.context.scene.objects if o.get('quarters_prop') == 'console']
    unwrap([o for o in asset if o.type == 'MESH'])
    bpy.context.scene['console_refit'] = REFIT_VERSION
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(source))
    spec = json.loads((HERE / 'construction.json').read_text())
    spec['bounds_gltf'][1][1] = HEIGHT_AFTER_TRIM
    spec['display_size_m'] = [WIDTH, HEIGHT]
    spec['refit'] = dict(issue=129, source='tracked console-working.blend cages',
                         old_display_m=[.874, .238], old_height_m=.69,
                         native_rise_m=RISE, fixed_parts=['LowerDeckHousing', 'DesktopSupport',
                         'BaseShoe', 'ControlPanel', 'Keys', 'Toggles', 'HousingRivets'],
                         cap_transition_height_m=.925, cap_front_inset_m=.0256,
                         upper_border_trim_m=UPPER_BORDER_TRIM, housing_trim_m=HOUSING_TRIM,
                         top_bar_height_m=.030 - UPPER_BORDER_TRIM)
    spec['fit_notes'] += ' The upper metal border is shortened by 18 mm along the screen plane, leaving a 12 mm top bar and retaining the complete 16:10 glass. The closed housing cap follows this trim above .925 m; all lower parts stay fixed. UVs are repacked at uniform physical density for both finish atlases.'
    (HERE / 'construction.json').write_text(json.dumps(spec, indent=2)+'\n')


if __name__ == '__main__':
    refit()
