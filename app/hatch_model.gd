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
	if solid.hatch_profile != null and not solid.section.is_empty(): return _wall_mesh(solid)
	if not solid.section.is_empty():
		var tool := SurfaceTool.new()
		tool.begin(Mesh.PRIMITIVE_TRIANGLES)
		var polygon := solid.section.duplicate()
		if Geometry2D.is_polygon_clockwise(polygon): polygon.reverse()
		var half := solid.size.z / 2
		# Concave opening edges need polygon triangulation, not a fan.
		tool.set_smooth_group(-1)
		var triangles := Geometry2D.triangulate_polygon(polygon)
		for index: int in range(0, triangles.size(), 3):
			var a := polygon[triangles[index]]
			var b := polygon[triangles[index + 1]]
			var c := polygon[triangles[index + 2]]
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

static func _wall_mesh(solid: ShipGeometry.SolidSpec) -> Mesh:
	var tool := SurfaceTool.new()
	tool.begin(Mesh.PRIMITIVE_TRIANGLES)
	var depth := -ShipGeometry.HATCH_RING_REAR
	var face := ShipGeometry.SolidSpec.new(Vector3.ZERO, Vector3(solid.size.x, solid.size.y, depth))
	var into := signf(solid.hatch_profile.hinge_frame().origin.z - ShipLayout.WALL / 2)
	for side: int in [-1, 1]:
		face.section = solid.wall_seat_section if side * into > 0 else solid.section
		_append(tool, solid_mesh(face), Transform3D(Basis(), Vector3(0, 0, side * (ShipLayout.WALL + depth) / 2)))
	# Both wall mouths follow the ring. The hidden rectangular cavity between
	# them still clears the moving seals and retains its sloping lintel.
	var arrays := box_mesh(solid.size).surface_get_arrays(0)
	var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
	for index: int in range(vertices.size()): vertices[index] = ShipGeometry.hatch_wall_vertex(solid, vertices[index])
	for triangle: int in range(0, indices.size(), 3):
		var a := vertices[indices[triangle]]
		var b := vertices[indices[triangle + 1]]
		var c := vertices[indices[triangle + 2]]
		var normal := (c - a).cross(b - a).normalized()
		if absf(normal.z) > 0.5: continue
		for vertex: Vector3 in [a, b, c]:
			tool.set_normal(normal)
			tool.add_vertex(vertex)
	tool.index()
	return tool.commit()

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
	var variant := HatchAsset.variant(spec)
	for side: int in range(2):
		var piece := mesh_piece(HatchAsset.leaf_mesh(variant, side), Transform3D.IDENTITY, masks[side], Surfaces.material(&"modelled_hatch"))
		piece.name = "ForeSteel" if side == 0 else "AftSteel"
		root.add_child(piece)
		Surfaces.bind(piece, &"modelled_hatch", leaf_frame)
		leaf_binding.pieces.append(piece)
	for group: Dictionary in variant.groups:
		if group.path not in ["Wheel", "ReverseWheel"] and not String(group.path).ends_with("Rivets"): continue
		var parent := root
		var name := String(group.path)
		var pose := HatchAsset.pose(group.transform)
		var side := int(group.side)
		if name.ends_with("Rivets"):
			var bolts := MultiMeshInstance3D.new()
			bolts.name = name
			bolts.multimesh = HatchAsset.leaf_rivets(int(variant.index), group)
			bolts.layers = masks[side]
			bolts.transform = pose
			parent.add_child(bolts)
			Surfaces.bind(bolts, &"modelled_hatch", leaf_frame)
			leaf_binding.pieces.append(bolts)
		else:
			var piece := mesh_piece(HatchAsset.group_mesh(int(variant.index), group), pose, masks[side], Surfaces.material(&"modelled_hatch"))
			if name in ["Wheel", "ReverseWheel"]:
				var wheel := Node3D.new()
				wheel.name = name
				wheel.transform = pose
				piece.transform = Transform3D.IDENTITY
				wheel.add_child(piece)
				parent.add_child(wheel)
				var wheel_frame := Surfaces.door_frame(spec, &"WHEEL/FORE" if side == 0 else &"WHEEL/AFT")
				wheel_frame.world_from_surface *= pose
				wheel_frame.floor_datum = -pose.origin.y
				wheel_frame.bounds = pose.affine_inverse() * leaf_frame.bounds
				Surfaces.bind(piece, &"modelled_hatch", wheel_frame)
				var wheel_binding := Surfaces.MotionBinding.new(wheel)
				wheel_binding.pieces.append(piece)
				bindings.append(wheel_binding)
			else:
				piece.name = name
				parent.add_child(piece)
				Surfaces.bind(piece, &"modelled_hatch", leaf_frame)
				leaf_binding.pieces.append(piece)
	return root

static func _part_mesh(part: HatchParts.Part) -> Mesh:
	match part.shape:
		&"box": return box_mesh(part.size)
		&"cylinder": return cylinder(part.radius, part.size.y)
		&"band", &"section":
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
	assert(part.shape == &"rounded", "supported service or primitive-probe shape")
	var tool := SurfaceTool.new()
	tool.begin(Mesh.PRIMITIVE_TRIANGLES)
	_rounded(tool, Vector2(part.size.x, part.size.y), part.radius, part.size.z, Vector3.ZERO)
	tool.generate_normals()
	tool.index()
	return tool.commit()

static func outline(size: Vector2, radius: float) -> PackedVector2Array:
	return HatchParts.outline(size, radius)

static func _triangle(tool: SurfaceTool, a: Vector3, b: Vector3, c: Vector3) -> void:
	for point: Vector3 in [a, c, b]: tool.add_vertex(point)

static func _quad(tool: SurfaceTool, a: Vector3, b: Vector3, c: Vector3, d: Vector3) -> void:
	_triangle(tool, a, b, c)
	_triangle(tool, a, c, d)

static func _rounded(tool: SurfaceTool, size: Vector2, radius: float, depth: float, center: Vector3) -> void:
	# Two inset contours bevel the perimeter rather than leaving a sharp slab edge.
	var bevel := minf(0.0125, minf(depth, minf(size.x, size.y)) / 4)
	bevel = minf(bevel, radius / 2)
	var outer := outline(size, radius)
	var inset := outline(size - Vector2.ONE * bevel * 2, radius - bevel)
	for i: int in range(outer.size()):
		var j := (i + 1) % outer.size()
		for side: float in [-1, 1]:
			var a := center + Vector3(inset[i].x, inset[i].y, side * depth / 2)
			var b := center + Vector3(inset[j].x, inset[j].y, side * depth / 2)
			var c := center + Vector3(outer[i].x, outer[i].y, side * (depth / 2 - bevel))
			var d := center + Vector3(outer[j].x, outer[j].y, side * (depth / 2 - bevel))
			tool.set_smooth_group(-1)
			if side < 0:
				_triangle(tool, center + Vector3(0, 0, -depth / 2), b, a)
				tool.set_smooth_group(0)
				_quad(tool, a, b, d, c)
			else:
				_triangle(tool, center + Vector3(0, 0, depth / 2), a, b)
				tool.set_smooth_group(0)
				_quad(tool, b, a, c, d)
		_quad(tool, center + Vector3(outer[i].x, outer[i].y, -depth / 2 + bevel), center + Vector3(outer[j].x, outer[j].y, -depth / 2 + bevel), center + Vector3(outer[j].x, outer[j].y, depth / 2 - bevel), center + Vector3(outer[i].x, outer[i].y, depth / 2 - bevel))

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
	var poses: Array[Transform3D] = []
	if kind == &"frame": poses = ShipGeometry.hatch_frame_rivet_stations(aperture)
	var batch := MultiMesh.new()
	batch.transform_format = MultiMesh.TRANSFORM_3D
	batch.mesh = cylinder(ShipGeometry.HATCH_RIVET_RADIUS, ShipGeometry.HATCH_RIVET_DEPTH)
	batch.instance_count = poses.size()
	for i: int in range(poses.size()):
		batch.set_instance_transform(i, poses[i])
	# The headless dummy renderer does not retain MultiMesh instance buffers.
	batch.set_meta(&"instance_poses", poses)
	_rivets[key] = batch
	return batch

static func surround_faces(spec: ShipLayout.DoorSpec, masks: Array[int]) -> Node3D:
	var root := Node3D.new()
	root.name = "Frame"
	var variant := HatchAsset.variant(spec)
	for side: int in range(2):
		var piece := mesh_piece(HatchAsset.surround_mesh(variant, side), Transform3D.IDENTITY, masks[side], Surfaces.material(&"modelled_hatch"))
		piece.name = "ForeSteel" if side == 0 else "AftSteel"
		Surfaces.bind(piece, &"modelled_hatch", Surfaces.door_frame(spec, &"FRAME"))
		root.add_child(piece)
		var bolts := MultiMeshInstance3D.new()
		bolts.name = "ForeRivets" if side == 0 else "AftRivets"
		bolts.multimesh = HatchAsset.frame_rivets(variant, side)
		bolts.layers = masks[side]
		Surfaces.bind(bolts, &"modelled_hatch", Surfaces.door_frame(spec, &"FRAME"))
		root.add_child(bolts)
	return root
