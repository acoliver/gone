class_name HatchModel
extends RefCounted
## Shared presentation meshes in the portal frame. No collision geometry lives here.

const DOOR_SHADE: float = 0.38
const CONTROL_SIZE := Vector3(0.19, 0.34, 0.07)

static var _meshes: Dictionary = {}
static var _rivets: Dictionary = {}
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
	if not solid.section.is_empty():
		var tool := SurfaceTool.new()
		tool.begin(Mesh.PRIMITIVE_TRIANGLES)
		var polygon := solid.section.duplicate()
		if Geometry2D.is_polygon_clockwise(polygon): polygon.reverse()
		var half := solid.size.z / 2
		for index: int in range(1, polygon.size() - 1):
			var a := polygon[0]
			var b := polygon[index]
			var c := polygon[index + 1]
			_triangle(tool, Vector3(a.x, a.y, -half), Vector3(c.x, c.y, -half), Vector3(b.x, b.y, -half))
			_triangle(tool, Vector3(a.x, a.y, half), Vector3(b.x, b.y, half), Vector3(c.x, c.y, half))
		for index: int in range(polygon.size()):
			var a := polygon[index]
			var b := polygon[(index + 1) % polygon.size()]
			_quad(tool, Vector3(b.x, b.y, -half), Vector3(a.x, a.y, -half), Vector3(a.x, a.y, half), Vector3(b.x, b.y, half))
		tool.generate_normals()
		tool.index()
		return tool.commit()
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

static func mesh_piece(mesh: Mesh, pose: Transform3D, mask: int, surface: Material) -> MeshInstance3D:
	var piece := MeshInstance3D.new()
	piece.mesh = mesh
	piece.transform = pose
	piece.layers = mask
	piece.material_override = surface
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

static func leaf(spec: ShipLayout.DoorSpec, masks: Array[int], bindings: Array[Surfaces.MotionBinding]) -> Node3D:
	var root := Node3D.new()
	root.name = "Leaf"
	var leaf_binding := Surfaces.MotionBinding.new(root)
	bindings.append(leaf_binding)
	var leaf_frame := Surfaces.door_frame(spec, &"LEAF")
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
			Surfaces.bind(bolts, &"hardware", leaf_frame)
			leaf_binding.pieces.append(bolts)
		else:
			var piece := mesh_piece(_leaf_mesh(group, spec.leaf_aperture()), group.transform, masks[group.side], steel() if group.steel else hardware())
			if name in ["Wheel", "ReverseWheel"]:
				var wheel := Node3D.new()
				wheel.name = name
				wheel.transform = group.transform
				piece.transform = Transform3D.IDENTITY
				wheel.add_child(piece)
				parent.add_child(wheel)
				var wheel_frame := Surfaces.door_frame(spec, &"WHEEL/FORE" if group.side == 0 else &"WHEEL/AFT")
				wheel_frame.world_from_surface *= group.transform
				wheel_frame.floor_datum = -group.transform.origin.y
				wheel_frame.bounds = group.transform.affine_inverse() * leaf_frame.bounds
				Surfaces.bind(piece, &"wheel", wheel_frame)
				var wheel_binding := Surfaces.MotionBinding.new(wheel)
				piece.material_override = null
				wheel_binding.pieces.append(piece)
				bindings.append(wheel_binding)
			else:
				piece.name = name
				parent.add_child(piece)
				Surfaces.bind(piece, &"seal" if ("SealSteel" in name or name.begins_with("BackingLap")) else (&"hatch_leaf" if group.steel else &"hardware"), leaf_frame)
				leaf_binding.pieces.append(piece)
	return root

static func _part_mesh(part: HatchParts.Part) -> Mesh:
	match part.shape:
		&"box": return box_mesh(part.size)
		&"cylinder": return cylinder(part.radius, part.size.y)
		&"torus":
			var ring := TorusMesh.new()
			ring.inner_radius = part.inner_radius
			ring.outer_radius = part.radius
			ring.rings = 64
			ring.ring_segments = 16
			var tool := SurfaceTool.new()
			tool.begin(Mesh.PRIMITIVE_TRIANGLES)
			_append(tool, ring, Transform3D(Basis.from_scale(Vector3(1, part.size.y / (part.radius - part.inner_radius), 1)), Vector3.ZERO))
			tool.index()
			return tool.commit()
		&"band":
			var tool := SurfaceTool.new()
			tool.begin(Mesh.PRIMITIVE_TRIANGLES)
			var polygon := part.contour.duplicate()
			if Geometry2D.is_polygon_clockwise(polygon): polygon.reverse()
			var triangles := Geometry2D.triangulate_polygon(polygon)
			for index: int in range(0, triangles.size(), 3):
				var a := polygon[triangles[index]]
				var b := polygon[triangles[index + 1]]
				var c := polygon[triangles[index + 2]]
				_triangle(tool, Vector3(a.x, a.y, -part.size.z / 2), Vector3(c.x, c.y, -part.size.z / 2), Vector3(b.x, b.y, -part.size.z / 2))
				_triangle(tool, Vector3(a.x, a.y, part.size.z / 2), Vector3(b.x, b.y, part.size.z / 2), Vector3(c.x, c.y, part.size.z / 2))
			for index: int in range(polygon.size()):
				var a := polygon[index]
				var b := polygon[(index + 1) % polygon.size()]
				_quad(tool, Vector3(b.x, b.y, -part.size.z / 2), Vector3(a.x, a.y, -part.size.z / 2), Vector3(a.x, a.y, part.size.z / 2), Vector3(b.x, b.y, part.size.z / 2))
			tool.generate_normals()
			tool.index()
			return tool.commit()
	assert(part.shape == &"rounded", "known physical hatch shape")
	var tool := SurfaceTool.new()
	tool.begin(Mesh.PRIMITIVE_TRIANGLES)
	_rounded(tool, Vector2(part.size.x, part.size.y), part.radius, part.size.z, Vector3.ZERO)
	tool.generate_normals()
	tool.index()
	return tool.commit()

static func _leaf_mesh(group: HatchParts.Group, aperture: Vector2) -> ArrayMesh:
	var key := [group.path, aperture, group.parts[0].transform]
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
		if group.path in [NodePath("Wheel"), NodePath("ReverseWheel")]:
			result.surface_set_material(result.get_surface_count() - 1, Surfaces.tape_material() if part.shape == &"band" else Surfaces.material(&"wheel"))
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


static func steel() -> ShaderMaterial:
	return Surfaces.material(&"hatch_leaf")

static func hardware() -> ShaderMaterial:
	return Surfaces.material(&"hardware")

static func outline(size: Vector2, radius: float) -> PackedVector2Array:
	return HatchParts.outline(size, radius)

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

static func rivets(kind: StringName, aperture: Vector2) -> MultiMesh:
	var key := [kind, aperture]
	if _rivets.has(key): return _rivets[key]
	var positions: Array[Vector3] = []
	if kind == &"frame":
		var contour := outline(aperture + Vector2(0.26, 0.05), 0.30)
		for i: int in range(contour.size()):
			var a := contour[i]
			var b := contour[(i + 1) % contour.size()]
			var count := maxi(1, int(ceil(a.distance_to(b) / 0.13)))
			for n: int in range(count):
				var point := a.lerp(b, float(n) / count)
				positions.append(Vector3(point.x, point.y + (aperture.y + ShipGeometry.SILL_HEIGHT) / 2, 0.0))
	var batch := MultiMesh.new()
	batch.transform_format = MultiMesh.TRANSFORM_3D
	batch.mesh = cylinder(0.021, 0.025)
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

static func surround_faces(spec: ShipLayout.DoorSpec, masks: Array[int]) -> Node3D:
	var root := Node3D.new()
	root.name = "Frame"
	var key := [spec.aperture(), signf(spec.hinge_frame().origin.z - ShipLayout.WALL / 2), &"surround"]
	if not _meshes.has(key):
		var tools: Array[SurfaceTool] = [SurfaceTool.new(), SurfaceTool.new()]
		for tool: SurfaceTool in tools: tool.begin(Mesh.PRIMITIVE_TRIANGLES)
		for solid: ShipGeometry.SolidSpec in ShipGeometry.hatch_surround_solids(spec):
			if solid.section.is_empty(): continue
			var pose := spec.frame().affine_inverse() * solid.transform
			var arrays := solid_mesh(solid).surface_get_arrays(0)
			var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
			for triangle: int in range(0, indices.size(), 3):
				var a := pose * vertices[indices[triangle]]
				var b := pose * vertices[indices[triangle + 1]]
				var c := pose * vertices[indices[triangle + 2]]
				var normal := (c - a).cross(b - a).normalized()
				var side := (0 if normal.z < 0 else 1) if absf(normal.z) > 0.5 else (0 if spec.hinge_frame().origin.z > ShipLayout.WALL / 2 else 1)
				for vertex: Vector3 in [a, b, c]:
					tools[side].set_normal(normal)
					tools[side].add_vertex(vertex)
		var meshes: Array[ArrayMesh] = []
		for tool: SurfaceTool in tools:
			tool.index()
			meshes.append(tool.commit())
		_meshes[key] = meshes
	for side: int in range(2):
		var piece := mesh_piece(_meshes[key][side], Transform3D.IDENTITY, masks[side], Surfaces.material(&"frame"))
		piece.name = "ForeSteel" if side == 0 else "AftSteel"
		Surfaces.bind(piece, &"frame", Surfaces.door_frame(spec, &"FRAME"))
		root.add_child(piece)
		var bolts := MultiMeshInstance3D.new()
		bolts.name = "ForeRivets" if side == 0 else "AftRivets"
		bolts.multimesh = rivets(&"frame", spec.aperture())
		bolts.layers = masks[side]
		var into := signf(spec.hinge_frame().origin.z - ShipLayout.WALL / 2)
		bolts.position.z = (-0.083 if side == 0 else 0.083) if into > 0 else (0.117 if side == 0 else 0.283)
		Surfaces.bind(bolts, &"hardware", Surfaces.door_frame(spec, &"FRAME"))
		root.add_child(bolts)
	return root
