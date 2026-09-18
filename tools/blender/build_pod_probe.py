#!/usr/bin/env python3
"""Parametric stasis-pod probe builder for gone issue #45 (Blender 4.5 headless).

Builds the three pod components of the approved concept design as clean
deterministic geometry — the open shell tub, the hinged canopy lid, and the
padded couch inside — with principled materials, then exports one
selected-objects GLB for the Godot asset-pipeline smoke.

The shell and canopy are lofts of one elliptical cross-section arc along the
pod's long axis: the shell takes the arc through the bottom, the canopy the
complementary arc over the top, so the lid closes onto the rim at rotation
zero. Both ends round off following a stadium side profile. The canopy is
re-origined onto its hinge line so the open angle is a plain object rotation
(baked as a glTF node transform, never a modifier). No randomness, no time
dependence, fixed vertex order.

Usage (headless):
  Blender --background --factory-startup --python build_pod_probe.py -- \
      --output <pod.glb> [--length 2.2] [--half-width 0.45]
      [--half-height 0.425] [--lid-angle 55.0] [--rim-angle 55.0]
"""

import argparse
import math
import os
import sys

import bmesh
import bpy

# Cross-section resolution (segments along the arc) and longitudinal
# resolution (rings: 2 * CAP_STATIONS cap rings + STRAIGHT_STATIONS + 1).
SHELL_ARC_SEGMENTS = 32
CANOPY_ARC_SEGMENTS = 16
CAP_STATIONS = 18
STRAIGHT_STATIONS = 8

# Concept-design material targets: off-white composite shell, dark glass
# (opaque) canopy, dark red-brown fabric couch. Values land in the GLB
# verbatim as linear base-color inputs.
SHELL_BASE_COLOR = (0.85, 0.84, 0.82)
SHELL_ROUGHNESS = 0.45
SHELL_METALLIC = 0.0
CANOPY_BASE_COLOR = (0.03, 0.03, 0.035)
CANOPY_ROUGHNESS = 0.08
CANOPY_METALLIC = 0.1
COUCH_BASE_COLOR = (0.16, 0.07, 0.05)
COUCH_ROUGHNESS = 0.9
COUCH_METALLIC = 0.0

# Couch pads (location, size, y-tilt degrees) inside the tub interior:
# seat slab, tilted backrest under the head, slight leg-rest wedge. Pads
# intentionally overlap a few millimeters so they read as one couch.
COUCH_PADS = [
    ((0.08, 0.0, -0.32), (1.30, 0.50, 0.11), 0.0),
    ((-0.56, 0.0, -0.11), (0.44, 0.50, 0.11), -24.0),
    ((0.76, 0.0, -0.27), (0.30, 0.50, 0.09), 10.0),
]
COUCH_BEVEL_WIDTH = 0.035
COUCH_BEVEL_SEGMENTS = 4
COUCH_SMOOTH_ANGLE_DEG = 40.0


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", required=True, help="output GLB path")
    parser.add_argument("--length", type=float, default=2.2, help="pod length along X (m)")
    parser.add_argument("--half-width", type=float, default=0.45, help="cross-section half extent Y")
    parser.add_argument("--half-height", type=float, default=0.425, help="cross-section half extent Z")
    parser.add_argument("--lid-angle", type=float, default=55.0, help="canopy open angle (deg)")
    parser.add_argument("--rim-angle", type=float, default=55.0,
                        help="cockpit opening half-angle from the top (deg)")
    return parser.parse_args(argv)


def reset_scene():
    """Remove the factory startup objects and any orphan data blocks."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras,
                  bpy.data.lights, bpy.data.images):
        for item in list(block):
            if item.users == 0:
                block.remove(item)


def principled(name, base_color, roughness, metallic):
    """Principled BSDF material with backface culling off (glTF doubleSided),
    so the tub interior and canopy underside stay visible in Godot."""
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = material.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*base_color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    material.use_backface_culling = False
    return material


def section_point(half_width, half_height, alpha, x, scale):
    """One cross-section vertex: azimuth alpha around the +Z top of an
    ellipse (y = a sin, z = b cos) placed at station x, shrunk by scale."""
    return (x,
            half_width * scale * math.sin(alpha),
            half_height * scale * math.cos(alpha))


def stations(length, cap_radius):
    """Longitudinal stations (x, cross-section scale) following the stadium
    side profile: straight section at full scale, quarter-circle caps that
    shrink the section toward each tip. The final tip rings stay tiny but
    non-degenerate; flat fans close them."""
    half_straight = length / 2.0 - cap_radius
    out = []
    for k in range(CAP_STATIONS - 1, 0, -1):
        psi = math.radians(90.0 * k / CAP_STATIONS)
        out.append((-half_straight - cap_radius * math.sin(psi), math.cos(psi)))
    for k in range(STRAIGHT_STATIONS + 1):
        out.append((-half_straight + 2.0 * half_straight * k / STRAIGHT_STATIONS, 1.0))
    for k in range(1, CAP_STATIONS):
        psi = math.radians(90.0 * k / CAP_STATIONS)
        out.append((half_straight + cap_radius * math.sin(psi), math.cos(psi)))
    return out


def cap_open_ring(bm, ring):
    """Close an open arc ring with a chord and a centroid triangle fan."""
    center = bm.verts.new(tuple(
        sum(vertex.co[axis] for vertex in ring) / len(ring) for axis in range(3)))
    for i in range(len(ring) - 1):
        bm.faces.new((ring[i], ring[i + 1], center))
    bm.faces.new((ring[-1], ring[0], center))


def loft_panel(name, material, alpha_start, alpha_end, arc_segments, station_list,
               half_width, half_height):
    """Loft an open elliptical-arc cross-section along X through the stations
    and close both ends with chord fans. Everything is smooth-shaded."""
    bm = bmesh.new()
    alphas = [math.radians(alpha_start + (alpha_end - alpha_start) * i / arc_segments)
              for i in range(arc_segments + 1)]
    rings = []
    for x, scale in station_list:
        rings.append([bm.verts.new(section_point(half_width, half_height, alpha, x, scale))
                      for alpha in alphas])
    for r in range(len(rings) - 1):
        for i in range(arc_segments):
            bm.faces.new((rings[r][i], rings[r + 1][i],
                          rings[r + 1][i + 1], rings[r][i + 1]))
    cap_open_ring(bm, rings[0])
    cap_open_ring(bm, rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for face in bm.faces:
        face.smooth = True
    mesh = bpy.data.meshes.new(name + "Mesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(material)
    return obj


def reorigin_hinge(obj, half_width, half_height, rim_angle_deg):
    """Move the canopy's mesh data so the -Y hinge rim line passes through the
    object origin; the object location restores world placement, so the open
    angle is a pure object rotation about that hinge."""
    rim = math.radians(rim_angle_deg)
    hinge_y = -half_width * math.sin(rim)
    hinge_z = half_height * math.cos(rim)
    for vertex in obj.data.vertices:
        vertex.co.y -= hinge_y
        vertex.co.z -= hinge_z
    obj.location = (0.0, hinge_y, hinge_z)


def smooth_by_angle(mesh):
    """Mark every face smooth and split shading across edges whose face
    angle exceeds the threshold (the padded-cushion look: rounded bevels
    shade smoothly, flat pad faces stay flat)."""
    bm = bmesh.new()
    bm.from_mesh(mesh)
    threshold = math.cos(math.radians(COUCH_SMOOTH_ANGLE_DEG))
    for edge in bm.edges:
        if len(edge.link_faces) == 2:
            edge.smooth = edge.link_faces[0].normal.dot(
                edge.link_faces[1].normal) >= threshold
        else:
            edge.smooth = False
    for face in bm.faces:
        face.smooth = True
    bm.to_mesh(mesh)
    bm.free()


def build_couch(material):
    """Three beveled pads joined into one couch object."""
    pads = []
    for location, size, tilt in COUCH_PADS:
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=location,
                                        rotation=(0.0, math.radians(tilt), 0.0))
        pad = bpy.context.active_object
        pad.scale = size
        pads.append(pad)
    bpy.ops.object.select_all(action="DESELECT")
    for pad in pads:
        pad.select_set(True)
    bpy.context.view_layer.objects.active = pads[0]
    bpy.ops.object.join()
    couch = bpy.context.active_object
    couch.name = "Couch"
    couch.data.materials.append(material)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    bevel = couch.modifiers.new("PadBevel", "BEVEL")
    bevel.width = COUCH_BEVEL_WIDTH
    bevel.segments = COUCH_BEVEL_SEGMENTS
    smooth_by_angle(couch.data)
    return couch


def mesh_stats(objects):
    """Per-object evaluated (modifier-applied) vertex and triangle counts."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    rows = []
    for obj in objects:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        rows.append((obj.name, len(mesh.vertices), len(mesh.loop_triangles)))
        evaluated.to_mesh_clear()
    return rows


def rim_rise(shell, canopy):
    """World-space top of the open canopy vs the shell rim, proving the lid
    angle survived into the authored scene (the far rim should lift well
    above the shell at any nonzero --lid-angle)."""
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    tops = []
    for obj in (shell, canopy):
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        tops.append(max((obj.matrix_world @ v.co for v in mesh.vertices),
                        key=lambda co: co.z).z)
        evaluated.to_mesh_clear()
    return tops[0], tops[1]


def main(argv):
    args = parse_args(argv)
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)

    reset_scene()
    shell_material = principled("ShellComposite", SHELL_BASE_COLOR,
                                SHELL_ROUGHNESS, SHELL_METALLIC)
    canopy_material = principled("CanopyGlass", CANOPY_BASE_COLOR,
                                 CANOPY_ROUGHNESS, CANOPY_METALLIC)
    couch_material = principled("CouchFabric", COUCH_BASE_COLOR,
                                COUCH_ROUGHNESS, COUCH_METALLIC)

    station_list = stations(args.length, args.half_height)
    shell = loft_panel("Shell", shell_material, args.rim_angle,
                       360.0 - args.rim_angle, SHELL_ARC_SEGMENTS, station_list,
                       args.half_width, args.half_height)
    canopy = loft_panel("Canopy", canopy_material, -args.rim_angle,
                        args.rim_angle, CANOPY_ARC_SEGMENTS, station_list,
                        args.half_width, args.half_height)
    reorigin_hinge(canopy, args.half_width, args.half_height, args.rim_angle)
    canopy.rotation_euler = (math.radians(args.lid_angle), 0.0, 0.0)
    couch = build_couch(couch_material)

    pod = [shell, canopy, couch]
    for obj in pod:
        bpy.context.scene.collection.objects.link(obj)

    rows = mesh_stats(pod)
    total_verts = sum(row[1] for row in rows)
    total_tris = sum(row[2] for row in rows)
    for name, verts, tris in rows:
        print("MESH %s verts=%d tris=%d" % (name, verts, tris))
    print("TOTAL objects=%d verts=%d tris=%d" % (len(rows), total_verts, total_tris))
    if total_tris >= 50000:
        print("FAIL mesh budget: %d tris >= 50000" % total_tris)
        sys.exit(1)

    shell_rim, canopy_rim = rim_rise(shell, canopy)
    print("RISE shell_rim=%.4f canopy_rim=%.4f rise=%.4f" % (
        shell_rim, canopy_rim, canopy_rim - shell_rim))
    expected = (2.0 * args.half_width * math.sin(math.radians(args.rim_angle))
                * math.sin(math.radians(args.lid_angle)))
    if canopy_rim - shell_rim < 0.8 * expected:
        print("FAIL rim rise %.4f < %.4f: open canopy angle lost before export" % (
            canopy_rim - shell_rim, 0.8 * expected))
        sys.exit(1)

    bpy.ops.object.select_all(action="DESELECT")
    for obj in pod:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = shell
    bpy.ops.export_scene.gltf(
        filepath=args.output,
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
        export_cameras=False,
        export_lights=False,
        export_skins=False,
        export_texcoords=False,
        export_animations=False,
        export_extras=False,
    )
    print("EXPORT path=%s bytes=%d" % (os.path.abspath(args.output),
                                       os.path.getsize(args.output)))


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
