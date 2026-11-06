class_name PodStrips
extends RefCounted
## Two red status belts shared by all pods, with no lights or colliders.
## #88: both base flanks use the same measured Y=0.280 m belt.
## Centers are 24 mm outward from ray-intersected skin, leaving the
## 12 mm tube outside the curved tub in every lid state.
## Emission follows Lighting.FIXTURE_EMISSIVE and remains always on.

const STRIP_EMISSION: Color = Color(Lighting.FIXTURE_EMISSIVE, 0.0, 0.0)
const STRIP_BASE: Color = Color(0.18, 0.01, 0.01)
const STRIP_ROUGHNESS: float = 0.8
const STRIP_METALLIC: float = 0.0
const STRIP_RADIUS: float = 0.012
const RADIAL_SEGMENTS: int = 8

## Measured +X base flank (#88).
const FLANK_DOME: Array[Vector3] = [
	Vector3(0.3772, 0.28, -0.85),
	Vector3(0.3918, 0.28, -0.80),
	Vector3(0.4150, 0.28, -0.70),
	Vector3(0.4326, 0.28, -0.60),
	Vector3(0.4465, 0.28, -0.50),
	Vector3(0.4566, 0.28, -0.40),
	Vector3(0.4640, 0.28, -0.30),
	Vector3(0.4690, 0.28, -0.20),
	Vector3(0.4721, 0.28, -0.10),
	Vector3(0.4733, 0.28, 0.00),
	Vector3(0.4721, 0.28, 0.10),
	Vector3(0.4692, 0.28, 0.20),
	Vector3(0.4642, 0.28, 0.30),
	Vector3(0.4567, 0.28, 0.40),
	Vector3(0.4465, 0.28, 0.50),
	Vector3(0.4331, 0.28, 0.60),
	Vector3(0.4150, 0.28, 0.70),
	Vector3(0.3918, 0.28, 0.80),
	Vector3(0.3599, 0.28, 0.90),
]

## #88: re-sampled -X skin at the +X belt height, with the same 24 mm stand-off.
const FLANK_TRAY: Array[Vector3] = [
	Vector3(-0.3921, 0.28, -0.80),
	Vector3(-0.4153, 0.28, -0.70),
	Vector3(-0.4333, 0.28, -0.60),
	Vector3(-0.4466, 0.28, -0.50),
	Vector3(-0.4568, 0.28, -0.40),
	Vector3(-0.4643, 0.28, -0.30),
	Vector3(-0.4694, 0.28, -0.20),
	Vector3(-0.4725, 0.28, -0.10),
	Vector3(-0.4736, 0.28, 0.00),
	Vector3(-0.4725, 0.28, 0.10),
	Vector3(-0.4694, 0.28, 0.20),
	Vector3(-0.4643, 0.28, 0.30),
	Vector3(-0.4568, 0.28, 0.40),
	Vector3(-0.4466, 0.28, 0.50),
	Vector3(-0.4333, 0.28, 0.60),
	Vector3(-0.4153, 0.28, 0.70),
	Vector3(-0.3921, 0.28, 0.80),
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
