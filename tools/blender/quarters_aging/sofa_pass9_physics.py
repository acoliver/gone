"""Sofa-only filling loss and settling parameters, leaving pass 8 callable."""
import bpy


def linear_keys(obj):
    for curve in obj.animation_data.action.fcurves:
        for key in curve.keyframe_points:
            key.interpolation = 'LINEAR'


def tune(obj, mod, config, kind, pressure=.01):
    settings = mod.settings
    bending = {'seats': 1.20, 'backs': 1.20, 'throw': .12}[kind]
    if kind == 'seats':
        for frame, value in [(1, config['bending']), (200, config['bending']), (600, bending)]:
            settings.bending_stiffness_max = value
            settings.keyframe_insert(data_path='bending_stiffness_max', frame=frame)
        config['seat_bending_ramp'] = {'frames': [200, 600], 'from': config['bending'], 'to': bending}
    elif obj.vertex_groups.get('Welt'):
        settings.bending_stiffness_max = bending
        config['weighted_bending_max'] = bending
    else:
        settings.bending_stiffness = bending
    damping = 12. if kind == 'throw' else 5.
    settings.tension_damping = settings.compression_damping = settings.shear_damping = damping
    settings.bending_damping = .3
    air = settings.air_damping
    late_air = 6.
    for frame, factor in [(1, 1.), (300, 1.), (600, late_air)]:
        settings.air_damping = air*factor
        settings.keyframe_insert(data_path='air_damping', frame=frame)
    if kind == 'backs':
        settings.use_pressure = True
        # The automatic initial-volume term inflates an opened cover back to
        # its starting volume. Zero target disables that term, leaving only
        # the prescribed inward load on the cloth, not an animated collider.
        settings.use_pressure_volume = True
        settings.target_volume = 0.
        for frame, force in [(1, 0.), (40, -pressure)]:
            settings.uniform_pressure_force = force
            settings.keyframe_insert(data_path='uniform_pressure_force', frame=frame)
    linear_keys(obj)
    mod.point_cache.frame_end = 2400
    config.update(pass9_bending=bending, structural_damping=damping, bending_damping=.3,
                  late_air_multiplier=late_air, late_air_ramp_frames=[300, 600], frames=2400)
    if kind == 'backs':
        config.update(volume_loss='zero-target uniform inward pressure', vacuum_kpa=pressure,
                      vacuum_ramp_frames=[1, 40], automatic_volume_term=False)
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    return config
