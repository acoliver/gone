"""Remove baked torso-crest pigment while preserving every other contribution."""
import argparse
import json
from pathlib import Path
import shutil
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from baked_age_colour import aged_linear, raster_fields
from common import export
from fringe_cards import image_from_array


def pixels(image):
    width, height = image.size
    data = np.empty((height, width, 4), np.float32)
    image.pixels.foreach_get(data.ravel())
    return data


def mask_pixels(path):
    image = bpy.data.images.load(str(path), check_existing=False)
    image.colorspace_settings.name = 'Non-Color'
    return pixels(image)


def apply_delta(rgba, delta):
    encoded = rgba[:, :, :3]
    linear = np.where(encoded <= .04045, encoded/12.92, ((encoded+.055)/1.055)**2.4)
    colour = np.clip(linear+delta, 0, 1)
    result = rgba.copy()
    result[:, :, :3] = np.where(colour <= .0031308, colour*12.92, 1.055*colour**(1/2.4)-.055)
    return result


def rebake(base, out):
    out.mkdir(parents=True, exist_ok=True)
    shutil.copytree(base/'textures', out/'textures', dirs_exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(base/'finished.blend'))
    body = bpy.data.objects['TunicBody']
    shader = body.data.materials[0].node_tree.nodes['Principled BSDF']
    old = shader.inputs['Base Color'].links[0].from_node.image
    width, height = old.size
    if width != height:
        raise ValueError('Pilot colour atlas must be square')
    rgba = pixels(old)
    # Apply a linear-light difference to the shipped pixels. Quantised source
    # masks cannot then rebake unrelated pigment, opacity or dust boundaries.
    original = mask_pixels(base/'textures/tunicbody_ao_up_curvature.png')
    exposure = mask_pixels(base/'textures/tunicbody_fade_dust.png')
    fields = raster_fields(body, width)
    fields[:, :, 0] = original[:, :, 1]
    fields[:, :, 3] = exposure[:, :, 2]
    rng = np.random.default_rng(9613+sum(map(ord, body.name)))
    fields[:, :, 4] = rng.random((height, width), dtype=np.float32)
    grain = .995+.01*fields[:, :, 4:5]
    ao_image = body.data.materials[0].node_tree.nodes['AO'].image
    ao_width, ao_height = ao_image.size
    rows = np.minimum(np.arange(height)*ao_height//height, ao_height-1)
    cols = np.minimum(np.arange(width)*ao_width//width, ao_width-1)
    ao = pixels(ao_image)[rows[:, None], cols[None, :], 0]
    palette = json.loads(Path(__file__).with_name('target-colours.json').read_text())['colours']
    for dust in [True, False]:
        corrected, _, _ = aged_linear(ao, fields, palette, dust=dust, crest_fade=False)
        fields[:, :, 1] = original[:, :, 2]
        previous, _, _ = aged_linear(ao, fields, palette, dust=dust)
        source = rgba if dust else mask_pixels(base/'textures/tunicbody_no_dust_control.png')
        result = apply_delta(source, (corrected-previous)*grain)
        name = 'tunicbody_aged_base.png' if dust else 'tunicbody_no_dust_control.png'
        image = image_from_array('Pilot exposure fade' if dust else 'Pilot exposure no-dust control',
                                 result, out/'textures'/name)
        if dust:
            for material in body.data.materials:
                texture = material.node_tree.nodes['Principled BSDF'].inputs['Base Color'].links[0].from_node
                texture.image = image
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'finished.blend'))
    export(out/'candidate.glb')
    bpy.ops.wm.open_mainfile(filepath=str(out/'finished.blend'))
    export(out/'repeat.glb')
    if (out/'candidate.glb').read_bytes() != (out/'repeat.glb').read_bytes():
        raise ValueError('Crest rebake does not reproduce identical export bytes')
    for name in ['game-sheet.npz', 'finished.json', 'hem-boundary-check.json', 'collisions.json', 'attachment-audit.json']:
        shutil.copyfile(base/name, out/name)
    print('PASS: final-mesh crest rebake; saved source exports identical bytes')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, default=ROOT/'tmp/age/tunic14/short-fibres')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    rebake(args.base.resolve(), args.out.resolve())
