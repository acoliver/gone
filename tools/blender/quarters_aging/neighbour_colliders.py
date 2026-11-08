"""Use nonintersecting fitted back contacts while a seat ages from its fitted pose."""
from pathlib import Path

import bpy

from common import collision, surface_tree

ROOT = Path(__file__).resolve().parents[3]


def slide(obj, distance, start, end, axis=1):
    position = obj.location.copy()
    obj.location[axis] += distance
    obj.keyframe_insert(data_path='location', frame=start)
    obj.location = position
    obj.keyframe_insert(data_path='location', frame=end)
    for curve in obj.animation_data.action.fcurves:
        for key in curve.keyframe_points:
            key.interpolation = 'LINEAR'


def morph_contact(comparison, fitted, frames):
    proxy = comparison.copy()
    proxy.data = comparison.data.copy()
    proxy.modifiers.clear()
    proxy.animation_data_clear()
    bpy.context.collection.objects.link(proxy)
    proxy.name = 'MorphCollision_'+comparison.name
    proxy['aged_export'] = False
    proxy.hide_render = True
    source = surface_tree(fitted)
    inverse = proxy.matrix_world.inverted()
    basis = proxy.shape_key_add(name='Fitted contact')
    aged = proxy.shape_key_add(name='Actual comparison contact')
    for vertex in basis.data:
        point, _, _, _ = source.find_nearest(proxy.matrix_world@vertex.co)
        vertex.co = inverse@point
    aged.value = 0
    aged.keyframe_insert(data_path='value', frame=1)
    aged.value = 1
    aged.keyframe_insert(data_path='value', frame=frames)
    for curve in proxy.data.shape_keys.animation_data.action.fcurves:
        for key in curve.keyframe_points:
            key.interpolation = 'LINEAR'
    collision(proxy, .001)
    return proxy


def fitted_backs(frames=240, mode='fitted'):
    helpers = []
    for name in ['BackCushion_C', 'BackCushion_L', 'BackCushion_R']:
        comparison = bpy.data.objects[name]
        for mod in list(comparison.modifiers):
            if mod.type == 'COLLISION':
                comparison.modifiers.remove(mod)
        if mode in {'staged', 'rear'}:
            aged_proxy = comparison.copy()
            aged_proxy.data = comparison.data.copy()
            aged_proxy.modifiers.clear()
            aged_proxy.animation_data_clear()
            bpy.context.collection.objects.link(aged_proxy)
            aged_proxy.name = 'ComparisonCollision_'+name
            aged_proxy['aged_export'] = False
            aged_proxy.hide_render = True
            collision(aged_proxy, .001)
            # Its hanging skirt reaches the deck; 0.6 m still overlaps the
            # fitted cover's allowed motion before the scheduled approach.
            slide(aged_proxy, 1.2, frames+60, frames*(3 if mode == 'rear' else 2)+60,
                  axis=1 if mode == 'rear' else 2)
            helpers.append(aged_proxy.name)
        with bpy.data.libraries.load(str(ROOT/'tools/blender/quarters/sofa/sofa-working.blend'), link=False) as (_, target):
            target.objects = [name]
        proxy = target.objects[0]
        bpy.context.collection.objects.link(proxy)
        proxy.name = 'FittedCollision_'+name
        proxy['aged_export'] = False
        proxy.hide_render = True
        proxy.animation_data_clear()
        if mode == 'morph':
            morphed = morph_contact(comparison, proxy, frames)
            helpers.append(morphed.name)
            bpy.data.objects.remove(proxy, do_unlink=True)
            continue
        collision(proxy, .001)
        if mode != 'fitted':
            proxy.location.y += .6
            slide(proxy, -.6, 1, max(2, frames//2))
        helpers.append(proxy.name)
    return {'helpers': helpers, 'pose': mode,
            'reason': 'The sofa-k back poses already cross the fitted centre cover at frame one.',
            'comparison_contact_direction': {'morph': 'fitted-to-aged morph', 'staged': 'downward', 'rear': 'forward from rear'}.get(mode),
            'comparison_contact_frames': [1, frames] if mode == 'morph' else [frames+60, frames*(3 if mode == 'rear' else 2)+60] if mode in {'staged', 'rear'} else None,
            'limitation': 'SAT must still test final cloth and fringe against the actual exported comparison meshes.'}
