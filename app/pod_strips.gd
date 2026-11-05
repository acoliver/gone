class_name PodStrips
extends RefCounted
## Two red status belts shared by all pods, with no lights or colliders.
## Frozen pod-local waypoints were measured by intersecting pod-v3's
## triangles at y 0.580 on the canopy shoulder and y 0.310 on the tray.
## Centers sit 0.006 m inside the skin; the tube radius is 0.012 m.
## The head end still stops at -0.850 to clear the blanket collider.
## Emission follows Lighting.FIXTURE_EMISSIVE and remains always on.

const STRIP_EMISSION: Color = Color(Lighting.FIXTURE_EMISSIVE, 0.0, 0.0)
const STRIP_BASE: Color = Color(0.18, 0.01, 0.01)
const STRIP_ROUGHNESS: float = 0.8
const STRIP_METALLIC: float = 0.0
const STRIP_RADIUS: float = 0.012
const RADIAL_SEGMENTS: int = 8

## The +X dome-shoulder belt at y 0.580: 19 waypoints, z -0.850 (head)
## to +0.900 (foot).
const FLANK_DOME: Array[Vector3] = [
	Vector3(0.331, 0.58, -0.85),
	Vector3(0.351, 0.58, -0.80),
	Vector3(0.369, 0.58, -0.70),
	Vector3(0.370, 0.58, -0.60),
	Vector3(0.370, 0.58, -0.50),
	Vector3(0.370, 0.58, -0.40),
	Vector3(0.370, 0.58, -0.30),
	Vector3(0.370, 0.58, -0.20),
	Vector3(0.370, 0.58, -0.10),
	Vector3(0.370, 0.58, 0.00),
	Vector3(0.370, 0.58, 0.10),
	Vector3(0.370, 0.58, 0.20),
	Vector3(0.370, 0.58, 0.30),
	Vector3(0.370, 0.58, 0.40),
	Vector3(0.370, 0.58, 0.50),
	Vector3(0.370, 0.58, 0.60),
	Vector3(0.369, 0.58, 0.70),
	Vector3(0.351, 0.58, 0.80),
	Vector3(0.303, 0.58, 0.90),
]

## The -X tray-wall belt at y 0.310: 17 waypoints, z -0.800 to +0.800.
const FLANK_TRAY: Array[Vector3] = [
	Vector3(-0.418, 0.31, -0.80),
	Vector3(-0.437, 0.31, -0.70),
	Vector3(-0.438, 0.31, -0.60),
	Vector3(-0.438, 0.31, -0.50),
	Vector3(-0.438, 0.31, -0.40),
	Vector3(-0.438, 0.31, -0.30),
	Vector3(-0.438, 0.31, -0.20),
	Vector3(-0.438, 0.31, -0.10),
	Vector3(-0.438, 0.31, 0.00),
	Vector3(-0.438, 0.31, 0.10),
	Vector3(-0.438, 0.31, 0.20),
	Vector3(-0.438, 0.31, 0.30),
	Vector3(-0.438, 0.31, 0.40),
	Vector3(-0.438, 0.31, 0.50),
	Vector3(-0.438, 0.31, 0.60),
	Vector3(-0.437, 0.31, 0.70),
	Vector3(-0.418, 0.31, 0.80),
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
