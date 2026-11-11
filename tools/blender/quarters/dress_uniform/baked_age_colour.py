"""Bake measured grey-blue fade and dry dust from surface exposure masks."""
import json
from pathlib import Path

import bpy
import numpy as np

from fringe_cards import image_from_array


def surface_fields(obj):
    points = np.array([obj.matrix_world @ v.co for v in obj.data.vertices])
    normals = np.array([(obj.matrix_world.to_3x3() @ v.normal).normalized() for v in obj.data.vertices])
    squared_lengths = np.zeros(len(points))
    normal_offsets = np.zeros(len(points))
    for edge in obj.data.edges:
        a, b = edge.vertices
        delta = points[a]-points[b]
        squared_lengths[[a, b]] += delta @ delta
        normal_offsets[a] += delta @ normals[a]
        normal_offsets[b] -= delta @ normals[b]
    if np.any(squared_lengths == 0):
        raise ValueError(f'{obj.name}: exposure bake requires connected surface vertices')
    # The old displacement Laplacian grew with edge length squared, painting
    # coarse triangles lighter than equally curved, finely sampled wool.
    curvature = 2*normal_offsets/squared_lengths
    crest = np.clip(curvature/10., 0, 1)
    up = np.clip(normals[:, 2], 0, 1)
    upper = np.clip((points[:, 2]+.48)/.30, 0, 1)
    # Broad, irregular exposure is independent of the old stress-thinning map.
    from opacity_bake import value_noise
    broad = .5+.5*value_noise(points, .07, 9612)
    fine = .5+.5*value_noise(points, .0008, 9613)
    pile_height = np.clip((points[:, 2]+.95)/.035, 0, 1)
    return np.column_stack([up, crest, upper, broad, fine, pile_height]).astype(np.float32)


def raster_fields(obj, size):
    fields = surface_fields(obj)
    result = np.zeros((size, size, fields.shape[1]), np.float32)
    occupied = np.zeros((size, size), bool)
    obj.data.calc_loop_triangles()
    uv = obj.data.uv_layers['BakeUV'].data
    for triangle in obj.data.loop_triangles:
        tex = np.array([uv[i].uv[:] for i in triangle.loops])*size
        lo = np.maximum(0, np.floor(tex.min(0)).astype(int))
        hi = np.minimum(size-1, np.ceil(tex.max(0)).astype(int))
        a, b, c = tex
        determinant = np.linalg.det(np.array([b-a, c-a]))
        if abs(determinant) < 1e-12:
            continue
        x, y = np.meshgrid(np.arange(lo[0], hi[0]+1)+.5, np.arange(lo[1], hi[1]+1)+.5)
        v = ((x-a[0])*(c[1]-a[1])-(y-a[1])*(c[0]-a[0]))/determinant
        w = ((b[0]-a[0])*(y-a[1])-(b[1]-a[1])*(x-a[0]))/determinant
        u = 1-v-w
        inside = (u >= 0) & (v >= 0) & (w >= 0)
        if inside.any():
            barycentric = np.c_[u[inside], v[inside], w[inside]]
            result[lo[1]:hi[1]+1, lo[0]:hi[0]+1][inside] = np.einsum(
                'ij,jk->ik', barycentric, fields[np.array(triangle.vertices)])
            occupied[lo[1]:hi[1]+1, lo[0]:hi[0]+1][inside] = True
    # Extend a few texels into island gutters to avoid black filtered seams.
    for _ in range(6):
        previous = occupied.copy()
        for axis, shift in [(0, -1), (0, 1), (1, -1), (1, 1)]:
            valid = np.roll(previous, shift, axis)
            if axis == 0:
                valid[0 if shift == 1 else -1, :] = False
            else:
                valid[:, 0 if shift == 1 else -1] = False
            fill = valid & ~occupied
            shifted = np.roll(result, shift, axis)
            result[fill] = shifted[fill]
            occupied[fill] = True
    return result


def aged_linear(ao, masks, palette, debris=False, dust=True, crest_fade=True):
    up, crest, upper, broad, fine = np.moveaxis(masks[:, :, :5], -1, 0)
    if not crest_fade:
        crest = np.zeros_like(crest)
    visibility = np.clip(ao, 0, 1)
    fade = np.clip(.34+.12*broad+.18*crest+.25*upper+.15*up, 0, .96)
    fade *= .40+.60*visibility
    dark = np.array(palette['dark_fold']['linear'])
    faded = np.array(palette['dusty_grey_blue']['linear'])
    high = np.array(palette['faded_crest']['linear'])
    substrate = dark+(faded-dark)*fade[:, :, None]
    crest_mix = np.clip((.12*up+.25*crest+.18*upper)*visibility, 0, .55)
    substrate += (high-substrate)*crest_mix[:, :, None]
    upward = np.clip((up-.04)/.51, 0, 1)
    upward = upward*upward*(3-2*upward)
    coverage = np.clip(upward*(.32+.62*upper)*(.92+.08*fine)*visibility, 0, .94) if dust else np.zeros_like(up)
    if debris:
        fibre = np.array(palette['fibre_dust']['linear'])
        substrate = fibre[None, None, :]*(.75+.55*broad[:, :, None])
        coverage = up*.25 if dust else np.zeros_like(up)
    shadow = .70+.30*visibility if debris else .28+.72*visibility
    colour = substrate*shadow[:, :, None]
    dust_colour = np.array(palette['shoulder_dust']['linear'])
    colour = colour*(1-coverage[:, :, None])+dust_colour*coverage[:, :, None]
    return np.clip(colour, 0, 1), fade, coverage


def bake_colour(obj, out, palette, debris=False):
    mat = obj.data.materials[0]
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    old = nodes.get('Wool base with AO and opacity')
    size = old.image.size[0] if old else 1024
    if 'BakeUV' not in obj.data.uv_layers:
        from bake_down import bake_uv
        bake_uv(obj)
    masks = raster_fields(obj, size)
    rng = np.random.default_rng(9613+sum(map(ord, obj.name)))
    masks[:, :, 4] = rng.random((size, size), dtype=np.float32)
    ao_node = nodes.get('AO')
    ao = np.ones((size, size), np.float32)
    if ao_node:
        image = ao_node.image
        data = np.empty(image.size[0]*image.size[1]*4, np.float32)
        image.pixels.foreach_get(data)
        data = data.reshape(image.size[1], image.size[0], 4)[:, :, 0]
        rows = np.minimum((np.arange(size)*image.size[1]/size).astype(int), image.size[1]-1)
        columns = np.minimum((np.arange(size)*image.size[0]/size).astype(int), image.size[0]-1)
        ao = data[rows[:, None], columns[None, :]]
    # The main drape's fold contrast already comes from lighting and baked AO.
    # Adding a curvature pigment term paints the same rounded folds twice.
    crest_fade = obj.name != 'TunicBody'
    colour, fade, dust = aged_linear(ao, masks, palette, debris, crest_fade=crest_fade)
    grain = .995+.01*masks[:, :, 4:5]
    colour *= grain
    rgba = np.ones((size, size, 4), np.float32)
    if old:
        old.image.pixels.foreach_get(rgba.ravel())
    rgba[:, :, :3] = np.where(colour <= .0031308, colour*12.92, 1.055*colour**(1/2.4)-.055)
    if obj.name == 'FibreDust':
        edge = np.clip(masks[:, :, 5]/.045, 0, 1)
        rgba[:, :, 3] *= edge > .2+.8*masks[:, :, 4]
    image = image_from_array(obj.name+'_Age12Base', rgba, Path(out)/(obj.name.lower()+'_aged_base.png'))
    texture = nodes.new('ShaderNodeTexImage')
    texture.name = 'Baked target fade and dust'
    texture.image = image
    uv = nodes.new('ShaderNodeUVMap')
    uv.uv_map = 'BakeUV'
    links.new(uv.outputs['UV'], texture.inputs['Vector'])
    shader = nodes['Principled BSDF']
    links.new(texture.outputs['Color'], shader.inputs['Base Color'])
    shader.inputs['Roughness'].default_value = .97
    shader.inputs['Specular IOR Level'].default_value = .12
    if obj.name == 'FibreDust':
        normal = nodes['NORMAL']
        normal.image = fibre_normal(normal.image, out, rng)
    if old:
        cutoff = nodes.new('ShaderNodeMath')
        cutoff.operation = 'ROUND'
        links.new(texture.outputs['Alpha'], cutoff.inputs[0])
        links.new(cutoff.outputs[0], shader.inputs['Alpha'])
    diagnostic = np.ones_like(rgba)
    diagnostic[:, :, :3] = np.stack([ao, masks[:, :, 0], masks[:, :, 1]], axis=2)
    image_from_array(obj.name+'_ExposureMasks', diagnostic, Path(out)/(obj.name.lower()+'_ao_up_curvature.png'), True)
    diagnostic[:, :, :3] = np.stack([fade, dust, masks[:, :, 3]], axis=2)
    image_from_array(obj.name+'_FadeDustMasks', diagnostic, Path(out)/(obj.name.lower()+'_fade_dust.png'), True)
    without, _, _ = aged_linear(ao, masks, palette, debris, dust=False, crest_fade=crest_fade)
    without *= grain
    control = rgba.copy()
    control[:, :, :3] = np.where(without <= .0031308, without*12.92, 1.055*without**(1/2.4)-.055)
    control_image = image_from_array(obj.name+'_NoDustControl', control,
                                     Path(out)/(obj.name.lower()+'_no_dust_control.png'))
    contrast = np.mean(abs(colour-without), axis=2)
    shoulder = masks[:, :, 2] > .6
    return dict(base_texture=image.filepath_raw, dust_off_control=control_image.filepath_raw,
                ao_source='Cycles baked AO' if ao_node else 'unoccluded facing',
                masks='AO/up-facing/positive normal-Laplacian curvature; fade/dust/broad exposure',
                dust_mean_linear_contrast=float(contrast[dust > .1].mean()) if (dust > .1).any() else 0.,
                shoulder_dust_fraction=float(np.mean(dust[shoulder] > .1)) if shoulder.any() else None,
                aged_only=True)


def fibre_normal(source, out, rng):
    width, height = source.size
    pixels = np.empty(width*height*4, np.float32)
    source.pixels.foreach_get(pixels)
    pixels = pixels.reshape(height, width, 4)
    normal = pixels[:, :, :3]*2-1
    grain = rng.normal(0, 1, (height, width)).astype(np.float32)
    grain = (grain+np.roll(grain, 1, 0)+np.roll(grain, -1, 0))/3
    normal[:, :, 0] += (np.roll(grain, 1, 1)-np.roll(grain, -1, 1))*.18
    normal[:, :, 1] += (np.roll(grain, 1, 0)-np.roll(grain, -1, 0))*.07
    normal /= np.maximum(np.linalg.norm(normal, axis=2, keepdims=True), 1e-8)
    pixels[:, :, :3] = normal*.5+.5
    return image_from_array('FibreDust_MicrofibreNormal', pixels, Path(out)/'fibredust_microfibre_normal.png', True)


def apply_colours(out, record, palette_path):
    palette = json.loads(Path(palette_path).read_text())['colours']
    report = dict(reference=json.loads(Path(palette_path).read_text()), materials={})
    names = ['TunicBody', 'FibreDust']+[p['name'] for p in record['fallen']]
    for name in names:
        obj = bpy.data.objects[name]
        obj.data.materials[0] = obj.data.materials[0].copy()
        report['materials'][name] = bake_colour(obj, out/'textures', palette, name != 'TunicBody')
        for index, material in enumerate(list(obj.data.materials)[1:], 1):
            if material.name.startswith('WoolCutEdge'):
                rim = obj.data.materials[0].copy()
                rim.name = 'WoolCutEdge_Aged12'
                for link in list(rim.node_tree.nodes['Principled BSDF'].inputs['Normal'].links):
                    rim.node_tree.links.remove(link)
                obj.data.materials[index] = rim
    # Facings and metal get their own baked textures, never review-only overrides.
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH' or not obj.get('aged_export') or obj.name in names or obj.name == 'Hanger':
            continue
        for index, material in enumerate(list(obj.data.materials)):
            if material is None:
                continue
            if 'Brass' in material.name:
                obj.data.materials[index] = aged_brass(obj, material, out/'textures', palette)
            elif material.name.startswith('MedalEnamel'):
                obj.data.materials[index] = aged_enamel(material)
            elif obj.name.startswith(('Collar', 'ShoulderBoard', 'Placket')) and 'Fringe' not in material.name:
                obj.data.materials[index] = material.copy()
                if index == 0:
                    report['materials'][obj.name] = bake_colour(obj, out/'textures', palette)
    report['fibres'] = recolour_fibres(out/'textures', palette)
    return report


def recolour_fibres(out, palette):
    changed = []
    heap_materials = set(bpy.data.objects['HeapFibres'].data.materials)
    materials = {material for obj in bpy.context.scene.objects
                 if obj.type == 'MESH' and obj.get('aged_export')
                 for material in obj.data.materials if material is not None and
                 ('Fringe' in material.name or 'Loose pale wool' in material.name)}
    for number, mat in enumerate(sorted(materials, key=lambda m: m.name)):
        shader = mat.node_tree.nodes['Principled BSDF']
        shader.inputs['Roughness'].default_value = .98
        shader.inputs['Specular IOR Level'].default_value = .12
        alpha_nodes = [node for node in mat.node_tree.nodes if node.type == 'TEX_IMAGE' and
                       node.image and ('normal' not in node.image.name.lower())]
        source = alpha_nodes[0].image if alpha_nodes else None
        width, height = source.size if source else (64, 64)
        rgba = np.ones((height, width, 4), np.float32)
        if source:
            source.pixels.foreach_get(rgba.ravel())
        colour = np.array(palette['fibre_dust' if 'Loose pale' in mat.name else 'dusty_grey_blue']['linear'])
        srgb = np.where(colour <= .0031308, colour*12.92, 1.055*colour**(1/2.4)-.055)
        variation = .85+.15*rgba[:, :, :3].mean(2)
        rgba[:, :, :3] = srgb[None, None, :]*variation[:, :, None]
        image = image_from_array('Aged12Fibre'+str(number), rgba, out/f'aged_fibres_{number}.png')
        texture = mat.node_tree.nodes.new('ShaderNodeTexImage')
        texture.image = image
        mat.node_tree.links.new(texture.outputs['Color'], shader.inputs['Base Color'])
        if source and alpha_nodes[0].inputs['Vector'].is_linked:
            mat.node_tree.links.new(alpha_nodes[0].inputs['Vector'].links[0].from_socket, texture.inputs['Vector'])
        if source and (width, height) == (1024, 1024) and 'Surviving' not in mat.name:
            from soft_wool_atlas import bundle_alpha, heap_bundle_alpha
            rgba[:, :, 3] = heap_bundle_alpha(9521) if mat in heap_materials else bundle_alpha(9521, fine=True)
            image.unpack(method='REMOVE')
            image.pixels.foreach_set(rgba.ravel())
            image.save()
            image.reload()
            image.pack()
            cutoff = mat.node_tree.nodes.new('ShaderNodeMath')
            cutoff.operation = 'ROUND'
            mat.node_tree.links.new(texture.outputs['Alpha'], cutoff.inputs[0])
            mat.node_tree.links.new(cutoff.outputs[0], shader.inputs['Alpha'])
        changed.append(mat.name)
    return changed


def aged_enamel(source):
    """#130: vitrified enamel retains blue while brass tarnishes in dry storage."""
    mat = source.copy()
    mat.name = 'MedalEnamel_Aged'
    shader = mat.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = (.006, .019, .066, 1)
    shader.inputs['Roughness'].default_value = .38
    shader.inputs['Specular IOR Level'].default_value = .12
    return mat


def aged_brass(obj, source, out, palette):
    from bake_down import bake_uv
    if 'BakeUV' not in obj.data.uv_layers:
        bake_uv(obj)
    mat = source.copy()
    mat.name = obj.name+'_DullBrownBrass'
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    masks = raster_fields(obj, 256)
    broad = masks[:, :, 3]
    brown = np.array(palette['brass_brown']['linear'])
    oxide = brown*.32
    colour = oxide+(brown-oxide)*(.35+.65*broad[:, :, None])
    rgba = np.ones((256, 256, 4), np.float32)
    rgba[:, :, :3] = np.where(colour <= .0031308, colour*12.92, 1.055*colour**(1/2.4)-.055)
    image = image_from_array(obj.name+'_BrassAge', rgba, out/(obj.name.lower()+'_brass_aged.png'))
    tex = nodes.new('ShaderNodeTexImage')
    tex.image = image
    uv = nodes.new('ShaderNodeUVMap')
    uv.uv_map = 'BakeUV'
    links.new(uv.outputs['UV'], tex.inputs['Vector'])
    shader = nodes['Principled BSDF']
    links.new(tex.outputs['Color'], shader.inputs['Base Color'])
    shader.inputs['Metallic'].default_value = .15
    shader.inputs['Roughness'].default_value = .94
    shader.inputs['Specular IOR Level'].default_value = .12
    if obj.name == 'Medal':
        medal_brass_finish(mat)
    return mat


def medal_brass_finish(mat):
    """Retain dry brown tarnish while exposing the formed metal's satin response."""
    shader = mat.node_tree.nodes['Principled BSDF']
    shader.inputs['Metallic'].default_value = .55
    shader.inputs['Roughness'].default_value = .58
