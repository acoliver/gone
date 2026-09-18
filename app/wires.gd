class_name Wires
extends Node3D
## The authored hanging-wire meshes under the torn ceiling: one merged
## tube surface swept along every authored centerline in
## Placement.hanging_wires (looped bundles, dangling strands, frayed
## offshoots) with one shared dark insulation material, so the whole
## damage dressing costs a single draw call. The tubes follow the sag
## curves through parallel-transport frames, so no cross-section twists
## through the catenaries and the torn ends stay capped. Dressing only:
## no colliders, no sim role, and every surface point stays above the
## authored clearance floor.

const WIRE_ALBEDO: Color = Color(0.16, 0.14, 0.13)
const WIRE_ROUGHNESS: float = 0.35
const WIRE_METALLIC: float = 0.45
const RADIAL_SEGMENTS: int = 8

static func build() -> Wires:
	var wires := Wires.new()
	wires.name = "HangingWires"
	var tool := SurfaceTool.new()
	tool.begin(Mesh.PRIMITIVE_TRIANGLES)
	var vertex_cursor := 0
	for wire: Placement.HangingWire in Placement.hanging_wires():
		vertex_cursor = _append_tube(tool, wire.points, wire.radius, vertex_cursor)
	var surface := MeshInstance3D.new()
	surface.name = "WireSurface"
	surface.mesh = tool.commit()
	surface.material_override = _wire_material()
	wires.add_child(surface)
	return wires

## Warm dark-grey insulation with low roughness and a real metallic
## sheen, so the red emergency light and the spark strobes glint off
## the cables instead of swallowing them. No emission: the mood stays
## dark and the wires only ever return the room's own light.
static func _wire_material() -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.albedo_color = WIRE_ALBEDO
	material.roughness = WIRE_ROUGHNESS
	material.metallic = WIRE_METALLIC
	return material

## Sweep one capped tube along the sampled centerline, appending its
## vertices and triangles to the merged surface. vertex_cursor is the
## index the tube's first vertex takes (SurfaceTool assigns indices in
## add order); the return value carries the cursor past this tube. The
## cross-section frame is parallel-transported segment to segment
## (project the carried normal onto the new tangent's plane), which
## keeps the tube twist-free through the sag without needing stable
## Frenet frames on the mostly vertical hanging curves.
static func _append_tube(
	tool: SurfaceTool,
	points: Array[Vector3],
	radius: float,
	vertex_cursor: int
) -> int:
	assert(points.size() >= 2, "an authored wire centerline carries at least two samples")
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
## authored curves turn gently, so projection stays twist-free.
static func _transported(normal: Vector3, tangent: Vector3) -> Vector3:
	var carried := normal - tangent * normal.dot(tangent)
	assert(carried.length() > 1e-6, "the transported wire frame never collapses")
	return carried.normalized()
