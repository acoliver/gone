class_name HatchModel
extends RefCounted
## Shared presentation meshes in the portal frame. No collision geometry lives here.

const DOOR_SHADE: float = 0.38
const CONTROL_SIZE := Vector3(0.19, 0.34, 0.07)

static var _meshes: Dictionary = {}
static var _rivets: Dictionary = {}
static var _steel: StandardMaterial3D
static var _hardware: StandardMaterial3D
static var _boxes: Dictionary = {}
static var _cylinders: Dictionary = {}
static var _materials: Dictionary = {}

static func box_mesh(size: Vector3) -> BoxMesh:
	if not _boxes.has(size):
		var box := BoxMesh.new()
		box.size = size
		_boxes[size] = box
	return _boxes[size]

static func solid_mesh(solid: ShipGeometry.SolidSpec) -> Mesh:
	if solid.hatch_profile == null: return box_mesh(solid.size)
	var arrays := box_mesh(solid.size).surface_get_arrays(0)
	var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
	for index: int in range(vertices.size()):
		vertices[index] = ShipGeometry.hatch_wall_vertex(solid, vertices[index])
	var tool := SurfaceTool.new()
	tool.begin(Mesh.PRIMITIVE_TRIANGLES)
	for triangle: int in range(0, indices.size(), 3):
		var a := vertices[indices[triangle]]
		var b := vertices[indices[triangle + 1]]
		var c := vertices[indices[triangle + 2]]
		var normal := (c - a).cross(b - a).normalized()
		for vertex: Vector3 in [a, b, c]:
			tool.set_normal(normal)
			tool.add_vertex(vertex)
	return tool.commit()

static func cylinder(radius: float, height: float) -> CylinderMesh:
	var key := Vector2(radius, height)
	if not _cylinders.has(key):
		var mesh := CylinderMesh.new()
		mesh.top_radius = radius
		mesh.bottom_radius = radius
		mesh.height = height
		_cylinders[key] = mesh
	return _cylinders[key]

static func flat_grey(shade: float) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.albedo_color = Color(shade, shade, shade)
	material.roughness = 0.95
	return material

static func material(shade: float) -> StandardMaterial3D:
	if not _materials.has(shade):
		_materials[shade] = flat_grey(shade)
	return _materials[shade]

static func mesh_piece(mesh: Mesh, pose: Transform3D, mask: int, surface: Material = null) -> MeshInstance3D:
	var piece := MeshInstance3D.new()
	piece.mesh = mesh
	piece.transform = pose
	piece.layers = mask
	piece.material_override = material(DOOR_SHADE) if surface == null else surface
	return piece

static func control_panel() -> Node3D:
	var panel := Node3D.new()
	panel.add_child(mesh_piece(box_mesh(CONTROL_SIZE), Transform3D.IDENTITY, 1, material(0.12)))
	var button := cylinder(0.036, 0.025)
	var piece := mesh_piece(button, Transform3D(Basis(Vector3.RIGHT, PI / 2), Vector3(0, 0.07, 0.045)), 1, material(0.055))
	piece.name = "Button"
	panel.add_child(piece)
	var reader := mesh_piece(box_mesh(Vector3(0.12, 0.018, 0.01)), Transform3D(Basis(), Vector3(0, -0.075, 0.04)), 1, material(0.015))
	reader.name = "CardReader"
	panel.add_child(reader)
	return panel

static func leaf(spec: ShipLayout.DoorSpec, masks: Array[int]) -> Node3D:
	var root := Node3D.new()
	root.name = "Leaf"
	for name: String in ["StrapHinges", "Lugs"]:
		var group := Node3D.new()
		group.name = name
		root.add_child(group)
	for group: HatchParts.Group in HatchParts.leaf(spec):
		var parent := root
		if group.path.get_name_count() > 1:
			parent = root.get_node(NodePath(group.path.get_name(0)))
		var name := group.path.get_name(group.path.get_name_count() - 1)
		if name.ends_with("Rivets"):
			var bolts := MultiMeshInstance3D.new()
			bolts.name = name
			bolts.multimesh = _leaf_rivets(group, spec.leaf_aperture())
			bolts.material_override = hardware()
			bolts.layers = masks[group.side]
			bolts.transform = group.transform
			parent.add_child(bolts)
		else:
			var piece := mesh_piece(_leaf_mesh(group, spec.leaf_aperture()), group.transform, masks[group.side], steel() if group.steel else hardware())
			if name in ["Wheel", "ReverseWheel"]:
				var wheel := Node3D.new()
				wheel.name = name
				wheel.transform = group.transform
				piece.transform = Transform3D.IDENTITY
				wheel.add_child(piece)
				parent.add_child(wheel)
			else:
				piece.name = name
				parent.add_child(piece)
	return root

static func _part_mesh(part: HatchParts.Part) -> Mesh:
	match part.shape:
		&"box": return box_mesh(part.size)
		&"cylinder": return cylinder(part.radius, part.size.y)
		&"torus":
			var ring := TorusMesh.new()
			ring.inner_radius = part.inner_radius
			ring.outer_radius = part.radius
			ring.rings = 32
			ring.ring_segments = 8
			return ring
	assert(part.shape == &"rounded", "known physical hatch shape")
	var tool := SurfaceTool.new()
	tool.begin(Mesh.PRIMITIVE_TRIANGLES)
	_rounded(tool, Vector2(part.size.x, part.size.y), part.radius, part.size.z, Vector3.ZERO)
	tool.generate_normals()
	tool.index()
	return tool.commit()

static func _leaf_mesh(group: HatchParts.Group, aperture: Vector2) -> ArrayMesh:
	var key := [group.path, aperture]
	if _meshes.has(key): return _meshes[key]
	var result := ArrayMesh.new()
	var poses: Dictionary = {}
	for part: HatchParts.Part in group.parts:
		var tool := SurfaceTool.new()
		tool.begin(Mesh.PRIMITIVE_TRIANGLES)
		_append(tool, _part_mesh(part), part.transform)
		tool.index()
		tool.commit(result)
		result.surface_set_name(result.get_surface_count() - 1, String(part.id))
		poses[part.id] = part.transform
	result.set_meta(&"part_transforms", poses)
	_meshes[key] = result
	return result

static func _leaf_rivets(group: HatchParts.Group, aperture: Vector2) -> MultiMesh:
	var key := [group.path, aperture]
	if _rivets.has(key): return _rivets[key]
	var batch := MultiMesh.new()
	batch.transform_format = MultiMesh.TRANSFORM_3D
	batch.mesh = _part_mesh(group.parts[0])
	batch.instance_count = group.parts.size()
	var poses: Array[Transform3D] = []
	for index: int in range(group.parts.size()):
		var pose := group.parts[index].transform
		batch.set_instance_transform(index, pose)
		poses.append(pose)
	batch.set_meta(&"instance_poses", poses)
	_rivets[key] = batch
	return batch


static func steel() -> StandardMaterial3D:
	if _steel == null:
		_steel = flat_grey(0.34)
		_steel.albedo_color = Color(0.33, 0.36, 0.35)
		_steel.metallic = 0.55
		_steel.roughness = 0.78
	return _steel

static func hardware() -> StandardMaterial3D:
	if _hardware == null:
		_hardware = flat_grey(0.20)
		_hardware.metallic = 0.75
		_hardware.roughness = 0.67
	return _hardware

static func outline(size: Vector2, radius: float) -> PackedVector2Array:
	var points := PackedVector2Array()
	for corner: int in range(4):
		var center := Vector2((size.x / 2 - radius) * (1 if corner in [0, 3] else -1), (size.y / 2 - radius) * (1 if corner < 2 else -1))
		for segment: int in range(9):
			var angle := (corner + segment / 8.0) * PI / 2
			points.append(center + Vector2(cos(angle), sin(angle)) * radius)
	return points

static func _triangle(tool: SurfaceTool, a: Vector3, b: Vector3, c: Vector3) -> void:
	for point: Vector3 in [a, c, b]: tool.add_vertex(point)

static func _quad(tool: SurfaceTool, a: Vector3, b: Vector3, c: Vector3, d: Vector3) -> void:
	_triangle(tool, a, b, c)
	_triangle(tool, a, c, d)

static func _rounded(tool: SurfaceTool, size: Vector2, radius: float, depth: float, center: Vector3) -> void:
	# Two inset contours bevel the perimeter rather than leaving a sharp slab edge.
	var outer := outline(size, radius)
	var inset := outline(size - Vector2.ONE * 0.025, radius - 0.0125)
	for i: int in range(outer.size()):
		var j := (i + 1) % outer.size()
		for side: float in [-1, 1]:
			var a := center + Vector3(inset[i].x, inset[i].y, side * depth / 2)
			var b := center + Vector3(inset[j].x, inset[j].y, side * depth / 2)
			var c := center + Vector3(outer[i].x, outer[i].y, side * (depth / 2 - 0.0125))
			var d := center + Vector3(outer[j].x, outer[j].y, side * (depth / 2 - 0.0125))
			tool.set_smooth_group(-1)
			if side < 0:
				_triangle(tool, center + Vector3(0, 0, -depth / 2), b, a)
				tool.set_smooth_group(0)
				_quad(tool, a, b, d, c)
			else:
				_triangle(tool, center + Vector3(0, 0, depth / 2), a, b)
				tool.set_smooth_group(0)
				_quad(tool, b, a, c, d)
		_quad(tool, center + Vector3(outer[i].x, outer[i].y, -depth / 2 + 0.0125), center + Vector3(outer[j].x, outer[j].y, -depth / 2 + 0.0125), center + Vector3(outer[j].x, outer[j].y, depth / 2 - 0.0125), center + Vector3(outer[i].x, outer[i].y, depth / 2 - 0.0125))

static func _ring(tool: SurfaceTool, aperture: Vector2) -> void:
	var inner := outline(aperture - Vector2(0, ShipGeometry.SILL_HEIGHT), 0.21)
	var outer := outline(aperture + Vector2(0.34, 0.22), 0.38)
	var center := Vector3(0, (aperture.y + ShipGeometry.SILL_HEIGHT) / 2, 0)
	for i: int in range(inner.size()):
		var j := (i + 1) % inner.size()
		var a := center + Vector3(inner[i].x, inner[i].y, 0.06)
		var b := center + Vector3(inner[j].x, inner[j].y, 0.06)
		var c := center + Vector3(outer[i].x, outer[i].y, -0.045)
		var d := center + Vector3(outer[j].x, outer[j].y, -0.045)
		_quad(tool, a, b, d, c)
		# The shared collar owns the return; duplicate curved sleeves expose the far room's mask.
		_quad(tool, c, d, d + Vector3(0, 0, 0.145), c + Vector3(0, 0, 0.145))

static func _append(tool: SurfaceTool, source: Mesh, pose: Transform3D) -> void:
	# Keep one nonindexed triangle stream: mixing add_vertex with append_from's
	# indexed primitive surfaces would silently discard the hand-built leaf.
	var arrays := source.surface_get_arrays(0)
	var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
	var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
	assert(not indices.is_empty(), "shared primitive mesh must supply indexed triangles")
	var normal_basis := pose.basis.inverse().transposed()
	for index: int in indices:
		tool.set_normal((normal_basis * normals[index]).normalized())
		tool.add_vertex(pose * vertices[index])

static func mesh(kind: StringName, aperture: Vector2) -> ArrayMesh:
	var key := [kind, aperture]
	if _meshes.has(key): return _meshes[key]
	var tool := SurfaceTool.new()
	tool.begin(Mesh.PRIMITIVE_TRIANGLES)
	if kind == &"frame":
		_ring(tool, aperture)
	else:
		assert(kind == &"hinges", "frame and fixed hinges are presentation-only")
		for height: float in [0.48, aperture.y - 0.40]:
			_append(tool, cylinder(0.085, 0.28), Transform3D(Basis(), Vector3(0, height, 0)))
	tool.generate_normals()
	tool.index()
	var result := tool.commit()
	_meshes[key] = result
	return result

static func rivets(kind: StringName, aperture: Vector2) -> MultiMesh:
	var key := [kind, aperture]
	if _rivets.has(key): return _rivets[key]
	var positions: Array[Vector3] = []
	if kind == &"frame":
		var contour := outline(aperture + Vector2(0.17, 0.05), 0.29)
		for i: int in range(contour.size()):
			var a := contour[i]
			var b := contour[(i + 1) % contour.size()]
			var count := maxi(1, int(ceil(a.distance_to(b) / 0.11)))
			for n: int in range(count):
				var point := a.lerp(b, float(n) / count)
				positions.append(Vector3(point.x, point.y + (aperture.y + ShipGeometry.SILL_HEIGHT) / 2, -0.005))
	var batch := MultiMesh.new()
	batch.transform_format = MultiMesh.TRANSFORM_3D
	batch.mesh = cylinder(0.018, 0.012)
	batch.instance_count = positions.size()
	var poses: Array[Transform3D] = []
	for i: int in range(positions.size()):
		var pose := Transform3D(Basis(Vector3.RIGHT, PI / 2), positions[i])
		batch.set_instance_transform(i, pose)
		poses.append(pose)
	# The headless dummy renderer does not retain MultiMesh instance buffers.
	batch.set_meta(&"instance_poses", poses)
	_rivets[key] = batch
	return batch

static func add_faces(parent: Node3D, kind: StringName, aperture: Vector2, masks: Array[int], leaf_space: bool) -> void:
	for side: int in range(2):
		var pose := Transform3D.IDENTITY
		if leaf_space:
			pose.origin.z = -0.05 if side == 0 else 0.05
		else:
			pose.origin.z = 0 if side == 0 else ShipLayout.WALL
		if side == 1:
			# Reflect depth only; rotating the face would put its hinges on the latch jamb.
			pose.basis = Basis(Vector3.RIGHT, Vector3.UP, Vector3.FORWARD)
		var prefix := "Fore" if side == 0 else "Aft"
		var piece := mesh_piece(mesh(kind, aperture), pose, masks[side], steel() if kind in [&"frame", &"leaf"] else hardware())
		piece.name = prefix + "Steel"
		parent.add_child(piece)
		if kind in [&"frame", &"leaf"]:
			var bolts := MultiMeshInstance3D.new()
			bolts.name = prefix + "Rivets"
			bolts.multimesh = rivets(kind, aperture)
			bolts.material_override = hardware()
			bolts.layers = masks[side]
			bolts.transform = pose
			parent.add_child(bolts)
