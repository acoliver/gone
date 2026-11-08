"""Co-scaled wool dynamics and a gradual release of the damaged shoulder."""
import bpy
import numpy as np


MASS_SCALE = .05


def slow_wool(mod):
    settings = mod.settings
    for field in ('mass', 'tension_stiffness', 'compression_stiffness', 'shear_stiffness',
                  'bending_stiffness', 'tension_stiffness_max', 'compression_stiffness_max',
                  'shear_stiffness_max', 'bending_stiffness_max', 'sewing_force_max'):
        setattr(settings, field, getattr(settings, field)*MASS_SCALE)
    settings.tension_damping = settings.compression_damping = settings.shear_damping = 5.
    settings.bending_damping = .5
    settings.air_damping = 10.
    settings.quality = 30
    mod.collision_settings.collision_quality = 6
    mod.collision_settings.distance_min = .002
    mod.collision_settings.self_distance_min = .002
    return dict(mass_and_spring_scale=MASS_SCALE, vertex_mass_kg=settings.mass,
                terminal_speed_model_m_s=100*settings.mass*9.81/10,
                contact_distance_m=.002, quality=30, air_damping=10.)


def release_pins(body, mod):
    pins = body.vertex_groups[mod.settings.vertex_group_mass]
    temporary = body.vertex_groups.new(name='Releasing shoulder stitches')
    ids = [v.index for v in body.data.vertices
           if .10 < v.co.x < .29 and v.co.z > -.24 and abs(v.co.y) < .025]
    if not ids:
        raise ValueError('No temporary damaged-shoulder holds')
    pins.add(ids, 1., 'REPLACE')
    temporary.add(ids, 1., 'REPLACE')
    release = body.modifiers.new('150 frame shoulder release', 'VERTEX_WEIGHT_MIX')
    release.vertex_group_a = pins.name
    release.vertex_group_b = temporary.name
    release.mix_mode = 'SUB'
    release.mix_set = 'B'
    release.mask_constant = 0.
    release.keyframe_insert(data_path='mask_constant', frame=1)
    release.mask_constant = 1.
    release.keyframe_insert(data_path='mask_constant', frame=151)
    bpy.context.view_layer.objects.active = body
    while body.modifiers.find(release.name) > 0:
        bpy.ops.object.modifier_move_up(modifier=release.name)
    return dict(temporary_vertices=len(ids), start_frame=1, end_frame=151,
                method='subtract animated temporary group from retained pin weights before Cloth')
