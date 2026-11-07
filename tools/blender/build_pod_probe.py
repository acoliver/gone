#!/usr/bin/env python3
"""Deterministic smooth stasis pod for gone #88, built with Blender 4.5.

Loft a capsule tub and hinged glass canopy, add beveled fabric pads, pillow
and restraints, then bake one three-material mesh into pod-local meters.
Godot uses +Z foot, -Z head, +Y up; Blender's exporter maps (X, Y, Z) to
(X, Z, -Y). No textures, randomness, lights or collision geometry.

Blender --background --factory-startup --python tools/blender/build_pod_probe.py \
    -- --output assets/props/probe/pod-probe.glb
"""

import argparse
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

SHELL_ARC_SEGMENTS = 32
CANOPY_ARC_SEGMENTS = 24
CAP_STATIONS = 18
STRAIGHT_STATIONS = 24


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", required=True)
    parser.add_argument("--length", type=float, default=2.2)
    parser.add_argument("--half-width", type=float, default=0.45)
    parser.add_argument("--half-height", type=float, default=0.425)
    parser.add_argument("--height", type=float, default=0.8)
    parser.add_argument("--lid-angle", type=float, default=55.0)
    parser.add_argument("--rim-angle", type=float, default=55.0)
    args = parser.parse_args(argv)
    if min(args.half_width, args.half_height, args.height) <= 0:
        parser.error("pod extents must be positive")
    if args.length <= 2 * args.half_height:
        parser.error("length must exceed the two rounded caps")
    if not 0 < args.lid_angle < 90 or not 0 < args.rim_angle < 90:
        parser.error("lid and rim angles must lie between 0 and 90 degrees")
    return args


def reset_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for blocks in (bpy.data.meshes, bpy.data.materials, bpy.data.images):
        for item in list(blocks):
            if item.users == 0:
                blocks.remove(item)


def principled(name, color, roughness, coat=0.0):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = material.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["Coat Weight"].default_value = coat
    bsdf.inputs["Coat Roughness"].default_value = 0.08
    material.use_backface_culling = True
    return material


def stations(length, cap_radius):
    """Stadium profile with shared arc rings and small, closed tip fans."""
    half_straight = length / 2 - cap_radius
    out = []
    for k in range(CAP_STATIONS - 1, 0, -1):
        psi = math.pi / 2 * k / CAP_STATIONS
        out.append((-half_straight - cap_radius * math.sin(psi), math.cos(psi)))
    for k in range(STRAIGHT_STATIONS + 1):
        out.append((-half_straight + 2 * half_straight * k / STRAIGHT_STATIONS, 1.0))
    for k in range(1, CAP_STATIONS):
        psi = math.pi / 2 * k / CAP_STATIONS
        out.append((half_straight + cap_radius * math.sin(psi), math.cos(psi)))
    return out


def cap_open_ring(bm, ring):
    center = bm.verts.new(sum((v.co for v in ring), Vector()) / len(ring))
    for index in range(len(ring)):
        bm.faces.new((ring[index], ring[(index + 1) % len(ring)], center))


def loft_panel(name, material, alpha_start, alpha_end, segments, station_list,
               half_width, half_height, thickness):
    """Welded quad loft; solidify closes the visible rim with a crisp edge."""
    bm = bmesh.new()
    alphas = [math.radians(alpha_start + (alpha_end - alpha_start) * i / segments)
              for i in range(segments + 1)]
    rings = []
    for x, scale in station_list:
        rings.append([bm.verts.new((x, half_width * scale * math.sin(alpha),
                                    half_height * scale * math.cos(alpha)))
                      for alpha in alphas])
    for lower, upper in zip(rings, rings[1:]):
        for i in range(segments):
            bm.faces.new((lower[i], upper[i], upper[i + 1], lower[i + 1]))
    cap_open_ring(bm, rings[0])
    cap_open_ring(bm, rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    for face in bm.faces:
        face.smooth = True
    mesh = bpy.data.meshes.new(name + "Mesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    mesh.materials.append(material)
    solidify = obj.modifiers.new("MoldedRim", "SOLIDIFY")
    solidify.thickness = thickness
    solidify.offset = -1.0
    solidify.use_even_offset = True
    return obj


def padded_box(name, location, size, tilt, material, bevel_width=0.035):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location,
                                    rotation=(0, math.radians(tilt), 0))
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    bevel = obj.modifiers.new("PadBevel", "BEVEL")
    bevel.width = bevel_width
    bevel.segments = 4
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    weighted = obj.modifiers.new("PadNormals", "WEIGHTED_NORMAL")
    weighted.keep_sharp = True
    return obj


def bake_pod_frame(objects, args):
    """Bake modifiers/hinge, then fit the full assembly to the frozen envelope.

    Width and length stay centered; height starts on the deck. This fit is
    authored once in Blender, never recomputed or distorted at runtime.
    """
    bpy.context.view_layer.update()
    for obj in objects:
        bpy.context.view_layer.objects.active = obj
        for modifier in list(obj.modifiers):
            bpy.ops.object.modifier_apply(modifier=modifier.name)
        obj.data.transform(obj.matrix_world)
        obj.matrix_world.identity()
    points = [v.co for obj in objects for v in obj.data.vertices]
    lo = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    hi = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    scale = Vector((args.length / (hi.x - lo.x),
                    2 * args.half_width / (hi.y - lo.y),
                    args.height / (hi.z - lo.z)))
    for obj in objects:
        for vertex in obj.data.vertices:
            p = vertex.co
            # Rotate long X onto Blender Y; export maps it onto Godot -Z.
            vertex.co = (-(p.y - (hi.y + lo.y) / 2) * scale.y,
                         (p.x - (hi.x + lo.x) / 2) * scale.x,
                         (p.z - lo.z) * scale.z)
        obj.data.update()


def main(argv):
    args = parse_args(argv)
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    reset_scene()
    plastic = principled("ShellPlastic", (0.96, 0.96, 0.96), 0.12, 1.0)
    glass = principled("CanopyGlass", (0.025, 0.035, 0.045), 0.06)
    fabric = principled("CouchFabric", (0.09, 0.12, 0.14), 0.9)
    profile = stations(args.length, args.half_height)
    shell = loft_panel("Shell", plastic, args.rim_angle, 360 - args.rim_angle,
                       SHELL_ARC_SEGMENTS, profile, args.half_width,
                       args.half_height, 0.018)
    canopy = loft_panel("Canopy", glass, -args.rim_angle, args.rim_angle,
                        CANOPY_ARC_SEGMENTS, profile, args.half_width,
                        args.half_height, 0.008)
    rim = math.radians(args.rim_angle)
    hinge = Vector((0, -args.half_width * math.sin(rim),
                    args.half_height * math.cos(rim)))
    for vertex in canopy.data.vertices:
        vertex.co -= hinge
    canopy.location = hinge
    canopy.rotation_euler.x = math.radians(args.lid_angle)
    pads = [
        padded_box("Seat", (0, 0, -0.23), (1.45, 0.50, 0.11), 0, fabric),
        padded_box("Backrest", (0.60, 0, -0.14), (0.45, 0.50, 0.11), -20, fabric),
        padded_box("Pillow", (0.77, 0, -0.04), (0.23, 0.39, 0.12), -20, fabric),
        padded_box("Footrest", (-0.79, 0, -0.24), (0.24, 0.47, 0.10), 10, fabric),
    ]
    for x in (-0.35, 0.29):
        pads.append(padded_box("Restraint", (x, 0, -0.16), (0.065, 0.52, 0.025),
                               0, fabric, 0.008))
    objects = [shell, canopy, *pads]
    bpy.context.view_layer.update()
    shell_rim = max((shell.matrix_world @ v.co).z for v in shell.data.vertices)
    canopy_rim = max((canopy.matrix_world @ v.co).z for v in canopy.data.vertices)
    rise = canopy_rim - shell_rim
    expected = 2 * args.half_width * math.sin(rim) * math.sin(math.radians(args.lid_angle))
    print("RISE shell_rim=%.4f canopy_rim=%.4f rise=%.4f" % (shell_rim, canopy_rim, rise))
    if rise < 0.8 * expected:
        raise RuntimeError("canopy open transform lost")
    bake_pod_frame(objects, args)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = shell
    bpy.ops.object.join()
    pod = bpy.context.active_object
    pod.name = "Pod"
    pod.data.calc_loop_triangles()
    triangles = len(pod.data.loop_triangles)
    print("TOTAL objects=1 verts=%d tris=%d materials=%s" % (
        len(pod.data.vertices), triangles, [m.name for m in pod.data.materials]))
    if triangles >= 20000:
        raise RuntimeError("pod must remain below 20000 triangles")
    bpy.ops.export_scene.gltf(
        filepath=args.output, export_format="GLB", use_selection=True,
        export_apply=True, export_yup=True, export_cameras=False,
        export_lights=False, export_skins=False, export_texcoords=False,
        export_animations=False, export_extras=False,
    )
    print("EXPORT path=%s bytes=%d" % (os.path.abspath(args.output), os.path.getsize(args.output)))


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
