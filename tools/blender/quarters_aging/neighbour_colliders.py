"""Use nonintersecting fitted back contacts while a seat ages from its fitted pose."""
from pathlib import Path

import bpy

from common import collision

ROOT = Path(__file__).resolve().parents[3]


def fitted_backs():
    helpers = []
    for name in ['BackCushion_C', 'BackCushion_L', 'BackCushion_R']:
        comparison = bpy.data.objects[name]
        for mod in list(comparison.modifiers):
            if mod.type == 'COLLISION':
                comparison.modifiers.remove(mod)
        with bpy.data.libraries.load(str(ROOT/'tools/blender/quarters/sofa/sofa-working.blend'), link=False) as (_, target):
            target.objects = [name]
        proxy = target.objects[0]
        bpy.context.collection.objects.link(proxy)
        proxy.name = 'FittedCollision_'+name
        proxy['aged_export'] = False
        proxy.hide_render = True
        collision(proxy, .001)
        helpers.append(proxy.name)
    return {'helpers': helpers, 'pose': 'fitted',
            'reason': 'The sofa-k back poses already cross the fitted centre cover at frame one.',
            'limitation': 'Comparison backs remain visible; SAT must still test the final seat against those actual meshes.'}
