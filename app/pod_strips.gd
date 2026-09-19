class_name PodStrips
extends RefCounted
## The pods' red emissive flank strips: two constant-height belt tubes
## inlaid into the shell skin — one along the +X dome shoulder just
## below its canopy line (y 0.580), one along the -X tray wall just
## below the recess rim the canopy lid closes onto (y 0.310) — built
## once as one merged capped-tube surface and instanced under every
## pod group, so the registry transform carries them. Every waypoint
## is an authored frozen constant in pod-local meters, measured against
## the pod-v2 shell silhouette read through PodMesh.shell_transform()
## (max |x| per z window at the belt heights), each sitting 0.006 m
## inside the measured skin so the 0.012 m tube reads as an inlaid
## light bar, nominally half embedded and half proud; every waypoint
## stays within 0.011 m of the skin, so the tube touches the shell
## everywhere along its path. The +X belt stops at z -0.85 at the head
## end because the authored hanging blanket owns the shoulder beyond
## it (0.050 m clear at the worst waypoint) and runs to +0.90, where
## the shoulder's own skin dives below the belt; the -X belt spans the
## tray wall's full extent at its height. Emission follows the fixture
## lens convention (Lighting.FIXTURE_EMISSIVE, docs/dev/
## emergency-lighting.md): the strips are the pod's own always-on bay
## markings, dressing only — no lights, no colliders, no flicker, and
## no tracker of the power fade.

const STRIP_EMISSION: Color = Color(Lighting.FIXTURE_EMISSIVE, 0.0, 0.0)
const STRIP_BASE: Color = Color(0.18, 0.01, 0.01)
const STRIP_ROUGHNESS: float = 0.8
const STRIP_METALLIC: float = 0.0
const STRIP_RADIUS: float = 0.012
const RADIAL_SEGMENTS: int = 8

## The +X dome-shoulder belt at y 0.580: 19 waypoints, z -0.850 (head)
## to +0.900 (foot).
const FLANK_DOME: Array[Vector3] = [
	Vector3(0.562, 0.58, -0.85),
	Vector3(0.591, 0.58, -0.8),
	Vector3(0.62, 0.58, -0.7),
	Vector3(0.64, 0.58, -0.6),
	Vector3(0.648, 0.58, -0.5),
	Vector3(0.658, 0.58, -0.4),
	Vector3(0.66, 0.58, -0.3),
	Vector3(0.678, 0.58, -0.2),
	Vector3(0.686, 0.58, -0.1),
	Vector3(0.676, 0.58, 0.0),
	Vector3(0.684, 0.58, 0.1),
	Vector3(0.674, 0.58, 0.2),
	Vector3(0.66, 0.58, 0.3),
	Vector3(0.662, 0.58, 0.4),
	Vector3(0.65, 0.58, 0.5),
	Vector3(0.634, 0.58, 0.6),
	Vector3(0.606, 0.58, 0.7),
	Vector3(0.596, 0.58, 0.8),
	Vector3(0.536, 0.58, 0.9),
]

## The -X tray-wall belt at y 0.310: 17 waypoints, z -0.800 to +0.800.
const FLANK_TRAY: Array[Vector3] = [
	Vector3(-0.024, 0.31, -0.8),
	Vector3(-0.058, 0.31, -0.7),
	Vector3(-0.062, 0.31, -0.6),
	Vector3(-0.07, 0.31, -0.5),
	Vector3(-0.076, 0.31, -0.4),
	Vector3(-0.088, 0.31, -0.3),
	Vector3(-0.088, 0.31, -0.2),
	Vector3(-0.087, 0.31, -0.1),
	Vector3(-0.09, 0.31, 0.0),
	Vector3(-0.087, 0.31, 0.1),
	Vector3(-0.088, 0.31, 0.2),
	Vector3(-0.085, 0.31, 0.3),
	Vector3(-0.073, 0.31, 0.4),
	Vector3(-0.072, 0.31, 0.5),
	Vector3(-0.062, 0.31, 0.6),
	Vector3(-0.05, 0.31, 0.7),
	Vector3(-0.034, 0.31, 0.8),
]

static var _strips_mesh: ArrayMesh = null
static var _strip_mat: StandardMaterial3D = null

## The one merged strip mesh both flank tubes live in (the PodMesh
## static-cache pattern): one surface, one material, shared by all
## seven pods, so the whole strip pass costs one ArrayMesh and
## per-pod draw state only.
static func strips_mesh() -> ArrayMesh:
	if _strips_mesh == null:
		_strips_mesh = _build_mesh()
	return _strips_mesh

## One strip instance under a pod group: identity transform, the
## vertices are already pod-local.
static func make() -> MeshInstance3D:
	var instance := MeshInstance3D.new()
	instance.name = "PodStrips"
	instance.mesh = strips_mesh()
	return instance

## Both flanks into one SurfaceTool under a shared vertex cursor,
## exactly how Wires merges its tube set; the one strip material is
## baked into surface 0.
static func _build_mesh() -> ArrayMesh:
	var tool := SurfaceTool.new()
	tool.begin(Mesh.PRIMITIVE_TRIANGLES)
	tool.set_material(_strip_material())
	var vertex_cursor := 0
	vertex_cursor = _append_tube(tool, FLANK_DOME, STRIP_RADIUS, vertex_cursor)
	vertex_cursor = _append_tube(tool, FLANK_TRAY, STRIP_RADIUS, vertex_cursor)
	return tool.commit()

## The one strip material, shared by every strip everywhere: full-power
## linear red emission per the fixture lens convention over the dark
## lens base (albedo is nearly irrelevant under full emission but keeps
## the strip dark where the room light catches it).
static func _strip_material() -> StandardMaterial3D:
	if _strip_mat == null:
		var material := StandardMaterial3D.new()
		material.albedo_color = STRIP_BASE
		material.roughness = STRIP_ROUGHNESS
		material.metallic = STRIP_METALLIC
		material.emission_enabled = true
		material.emission = STRIP_EMISSION
		_strip_mat = material
	return _strip_mat

## Sweep one capped tube along the sampled centerline, appending its
## vertices and triangles to the merged surface. vertex_cursor is the
## index the tube's first vertex takes (SurfaceTool assigns indices in
## add order); the return value carries the cursor past this tube. The
## cross-section frame is parallel-transported segment to segment
## (project the carried normal onto the new tangent's plane), which
## keeps the tube twist-free along the flank without needing stable
## Frenet frames on the gently curving belts.
static func _append_tube(
	tool: SurfaceTool,
	points: Array[Vector3],
	radius: float,
	vertex_cursor: int
) -> int:
	assert(points.size() >= 2, "an authored strip centerline carries at least two samples")
	var segment_tangents: Array[Vector3] = []
	for index: int in range(points.size() - 1):
		segment_tangents.append((points[index + 1] - points[index]).normalized())
	var normal := _seed_normal(segment_tangents[0])
	var ring_starts: Array[int] = []
	for index: int in range(points.size()):
		var tangent: Vector3 = segment_tangents[mini(index, segment_tangents.size() - 1)]
		if index > 0:
			normal = _transported(normal, tangent)
		var binormal := tangent.cross(normal)
		ring_starts.append(vertex_cursor)
		for segment: int in range(RADIAL_SEGMENTS):
			var angle: float = TAU * float(segment) / float(RADIAL_SEGMENTS)
			var radial := normal * cos(angle) + binormal * sin(angle)
			tool.set_normal(radial)
			tool.set_uv(Vector2(
				float(segment) / float(RADIAL_SEGMENTS),
				float(index) / float(points.size() - 1)
			))
			tool.add_vertex(points[index] + radial * radius)
		vertex_cursor += RADIAL_SEGMENTS
	for index: int in range(points.size() - 1):
		var lower: int = ring_starts[index]
		var upper: int = ring_starts[index + 1]
		for segment: int in range(RADIAL_SEGMENTS):
			var next_segment: int = (segment + 1) % RADIAL_SEGMENTS
			tool.add_index(lower + segment)
			tool.add_index(lower + next_segment)
			tool.add_index(upper + next_segment)
			tool.add_index(lower + segment)
			tool.add_index(upper + next_segment)
			tool.add_index(upper + segment)
	var bottom_center := vertex_cursor
	_append_cap(tool, points[0], ring_starts[0], bottom_center, segment_tangents[0], false)
	var top_center := vertex_cursor + 1
	_append_cap(
		tool,
		points[points.size() - 1],
		ring_starts[ring_starts.size() - 1],
		top_center,
		segment_tangents[segment_tangents.size() - 1],
		true
	)
	return vertex_cursor + 2

## One capped tube end: a center vertex plus a fan over the end ring,
## wound to face along the outward tangent.
static func _append_cap(
	tool: SurfaceTool,
	center: Vector3,
	ring: int,
	center_index: int,
	tangent: Vector3,
	forward: bool
) -> void:
	tool.set_normal(tangent if forward else -tangent)
	tool.set_uv(Vector2(0.5, 1.0 if forward else 0.0))
	tool.add_vertex(center)
	for segment: int in range(RADIAL_SEGMENTS):
		var next_segment: int = (segment + 1) % RADIAL_SEGMENTS
		if forward:
			tool.add_index(center_index)
			tool.add_index(ring + segment)
			tool.add_index(ring + next_segment)
		else:
			tool.add_index(center_index)
			tool.add_index(ring + next_segment)
			tool.add_index(ring + segment)

## A unit vector perpendicular to the first tangent, seeded off the
## world axis least aligned with it so the seed never collapses.
static func _seed_normal(tangent: Vector3) -> Vector3:
	var helper := Vector3.RIGHT if absf(tangent.y) > 0.9 else Vector3.UP
	return tangent.cross(helper).normalized()

## Carry the cross-section normal onto the next tangent's plane; the
## authored belts turn gently, so projection stays twist-free.
static func _transported(normal: Vector3, tangent: Vector3) -> Vector3:
	var carried := normal - tangent * normal.dot(tangent)
	assert(carried.length() > 1e-6, "the transported strip frame never collapses")
	return carried.normalized()
