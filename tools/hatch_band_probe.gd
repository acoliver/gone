class_name HatchBandProbe
extends RefCounted
## Two-sided ray diagnostics preserve winding and part identity, including culled faces.

const EYE := Vector3(0, 1.28, -3.65)
const KEY := Vector3(1.1, 2.9, -1.5)
const VIEWPORT := Vector2(1199, 1312)
var faces := PackedVector3Array()
var provenance: Array[Dictionary] = []
var triangles := TriangleMesh.new()
var production_key := Vector3.ZERO

static func from_hatch() -> HatchBandProbe:
	var probe := HatchBandProbe.new()
	var source := ShipLayout.authored().layout.door(&"D14-C-001-H-FORE")
	var spec := ShipLayout.DoorSpec.new(source.id(), source.deck_number(), source.kind(), source.policy(), Transform3D.IDENTITY, source.aperture(), source.spaces(), source.face_ids(), source.owner_id(), source.animation(), source.has_wheel())
	var view := DoorView.build(spec)
	probe.collect(view)
	var lamp: Node3D = view.get_node("ForeServices/Lamp")
	probe.production_key = Surfaces.world_frame(lamp) * Vector3(0, 0, -0.20)
	view.free()
	probe.build()
	return probe

func add_triangle(a: Vector3, b: Vector3, c: Vector3, node: String, part: String) -> void:
	faces.append_array(PackedVector3Array([a, b, c]))
	provenance.append({"node": node, "part": part, "normal": (c - a).cross(b - a).normalized()})

func collect(node: Node3D, path: String = "") -> void:
	path += "/" + String(node.name)
	if node is MeshInstance3D:
		_append(node.mesh, Surfaces.world_frame(node), path)
	elif node is MultiMeshInstance3D:
		var poses: Array = node.multimesh.get_meta(&"instance_poses")
		for index: int in range(poses.size()): _append(node.multimesh.mesh, Surfaces.world_frame(node) * poses[index], path + "/%d" % index)
	for child: Node3D in node.get_children(): collect(child, path)

func _append(mesh: Mesh, pose: Transform3D, path: String) -> void:
	var ranges: Dictionary = mesh.get_meta(&"part_ranges", mesh.get_meta(&"hatch_reservations", {}))
	for surface: int in range(mesh.get_surface_count()):
		var arrays := mesh.surface_get_arrays(surface)
		var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var indices := PackedInt32Array() if arrays[Mesh.ARRAY_INDEX] == null else arrays[Mesh.ARRAY_INDEX] as PackedInt32Array
		var uvs := PackedVector2Array() if arrays[Mesh.ARRAY_TEX_UV] == null else arrays[Mesh.ARRAY_TEX_UV] as PackedVector2Array
		if indices.is_empty():
			for index: int in range(vertices.size()): indices.append(index)
		for index: int in range(0, indices.size(), 3):
			var part := "surface-%d" % surface
			for id: Variant in ranges:
				var row: Dictionary = ranges[id]
				if index >= row.index_start and index < row.index_start + row.index_count:
					part = String(id)
					break
			add_triangle(pose * vertices[indices[index]], pose * vertices[indices[index + 1]], pose * vertices[indices[index + 2]], path, part)
			provenance[-1].normal *= signf(pose.basis.determinant())
			if not uvs.is_empty(): provenance[-1].uvs = [uvs[indices[index]], uvs[indices[index + 1]], uvs[indices[index + 2]]]

func build() -> void:
	assert(triangles.create_from_faces(faces), "nonempty submitted triangles")

func cast(origin: Vector3, direction: Vector3, distance: float = 20.0) -> Dictionary:
	var hit := triangles.intersect_segment(origin, origin + direction.normalized() * distance)
	if hit.is_empty(): return {}
	var row: Dictionary = provenance[int(hit.face_index)].duplicate()
	row.position = hit.position
	if row.has("uvs"):
		var index := int(hit.face_index) * 3
		var bary := Geometry3D.get_triangle_barycentric_coords(hit.position, faces[index], faces[index + 1], faces[index + 2])
		row.uv = row.uvs[0] * bary.x + row.uvs[1] * bary.y + row.uvs[2] * bary.z
	return row

func camera_hit(pixel: Vector2, key: Vector3 = KEY) -> Dictionary:
	var scale := tan(deg_to_rad(46.0 / 2)) * 2 / VIEWPORT.y
	var direction := Vector3(-(pixel.x - VIEWPORT.x / 2) * scale, -(pixel.y - VIEWPORT.y / 2) * scale, 1).normalized()
	var hit := cast(EYE, direction)
	if hit.is_empty(): return hit
	var to_key: Vector3 = key - hit.position
	hit.camera_dot = hit.normal.dot(-direction)
	hit.key_dot = hit.normal.dot(to_key.normalized())
	var shadow := cast(hit.position + to_key.normalized() * 0.0002, to_key, to_key.length() - 0.0004)
	hit.blocker = "" if shadow.is_empty() else shadow.node + ":" + shadow.part
	return hit
