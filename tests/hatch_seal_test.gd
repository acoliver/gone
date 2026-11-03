extends SimTestCase

const IDS: Array[StringName] = [ShipLayout.BAY_DOOR_ID, &"D14-C-000-H-FORE", &"D14-C-000-H-AFT", &"D14-C-001-H-FORE", &"D14-C-001-H-AFT"]
const PIECES := {"COAMING": "Coaming", "FRAME/LEFT": "HingeJamb", "FRAME/RIGHT": "LatchJamb", "FRAME/TOP": "Lintel", "FRAME/STOP-LEFT": "StopLeft", "FRAME/STOP-RIGHT": "StopRight", "FRAME/STOP-TOP": "StopTop", "FRAME/STOP-BOTTOM": "StopBottom"}

func test_shader_steel_seal_queries_keep_opaque_back_face_and_reflected_winding_contracts() -> void:
	var piece := HatchModel.mesh_piece(QuadMesh.new(), Transform3D.IDENTITY, 4, Surfaces.material(&"hatch_leaf"))
	var query := preload("res://tests/hatch_render_faces.gd")
	var faces := PackedVector3Array()
	query.collect(piece, Vector3.BACK, 4, faces)
	assert_int_equal(faces.size(), 6, "opaque shader steel draws the front")
	faces.clear()
	query.collect(piece, Vector3.FORWARD, 4, faces)
	assert_true(faces.is_empty(), "shader steel does not make the back seal a hatch")
	piece.basis = Basis(Vector3.RIGHT, Vector3.UP, Vector3.FORWARD)
	query.collect(piece, Vector3.BACK, 4, faces)
	assert_true(faces.is_empty(), "reflected shader steel reverses the front")
	query.collect(piece, Vector3.FORWARD, 4, faces)
	assert_int_equal(faces.size(), 6, "reflected shader steel draws its transformed front")
	piece.free()

func _mesh_faces(node: Node3D, faces: PackedVector3Array) -> void:
	var world := ShipScene._world_frame(node)
	if node is MeshInstance3D:
		_append_mesh_vertices(node.mesh, world, faces)
	if node is MultiMeshInstance3D:
		for pose: Transform3D in node.multimesh.get_meta(&"instance_poses"):
			_append_mesh_vertices(node.multimesh.mesh, world * pose, faces)
	for child: Node3D in node.get_children(): _mesh_faces(child, faces)

func _append_mesh_vertices(mesh: Mesh, pose: Transform3D, faces: PackedVector3Array) -> void:
	# Mesh.get_faces() welds through TriangleMesh and rounds small details.
	for surface: int in range(mesh.get_surface_count()):
		var arrays := mesh.surface_get_arrays(surface)
		var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var indices := PackedInt32Array()
		if arrays[Mesh.ARRAY_INDEX] != null: indices = arrays[Mesh.ARRAY_INDEX]
		if indices.is_empty():
			for vertex: Vector3 in vertices: faces.append(pose * vertex)
		else:
			for index: int in indices: faces.append(pose * vertices[index])

func _sealed(id: StringName, side: float) -> void:
	var spec := ShipLayout.authored().layout.door(id)
	var view := DoorView.build(spec)
	if OS.has_environment("GONE_SEAL_NEGATIVE_CONTROL"):
		for piece: Node3D in view.label_leaf().get_children():
			if "SealSteel" in String(piece.name): piece.visible = false
	var misses := 0
	var first := ""
	var rays := 0
	var aperture := spec.aperture()
	for eye_x: float in [-0.4, 0.0, 0.4]:
		for eye_y: float in [0.6, 1.4, 2.2]:
			var eye := spec.frame() * Vector3(eye_x, eye_y, ShipLayout.WALL / 2 + side * 2.0)
			var faces := PackedVector3Array()
			preload("res://tests/hatch_render_faces.gd").collect(view, eye, 1, faces)
			var triangles := TriangleMesh.new()
			assert_true(triangles.create_from_faces(faces), "eye-facing rendered hatch triangles form a ray-query mesh")
			for column: int in range(121):
				for row: int in range(241):
					var target := spec.frame() * Vector3(lerpf(-aperture.x / 2, aperture.x / 2, column / 120.0), aperture.y * row / 240.0, ShipLayout.WALL / 2)
					rays += 1
					if triangles.intersect_segment(eye, eye + (target - eye) * 2).is_empty():
						misses += 1
						if first == "": first = "eye=%s aperture=(%d,%d)" % [eye, column, row]
	view.free()
	print("SEAL %s face=%+d rays=%d misses=%d %s" % [id, int(side), rays, misses, first])
	assert_int_equal(misses, 0, "%s face=%+d rendered leaf/frame leaks: %s" % [id, int(side), first])

func test_bay_fore_sealed() -> void: _sealed(IDS[0], -1)
func test_bay_aft_sealed() -> void: _sealed(IDS[0], 1)
func test_x0_fore_sealed() -> void: _sealed(IDS[1], -1)
func test_x0_aft_sealed() -> void: _sealed(IDS[1], 1)
func test_x6_fore_sealed() -> void: _sealed(IDS[2], -1)
func test_x6_aft_sealed() -> void: _sealed(IDS[2], 1)
func test_x30_fore_sealed() -> void: _sealed(IDS[3], -1)
func test_x30_aft_sealed() -> void: _sealed(IDS[3], 1)
func test_x36_fore_sealed() -> void: _sealed(IDS[4], -1)
func test_x36_aft_sealed() -> void: _sealed(IDS[4], 1)

func test_leaf_perimeter_is_steel_at_the_face_not_a_recessed_backing() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in IDS:
		var spec := layout.door(id)
		var view := DoorView.build(spec)
		var pose := spec.frame() * spec.hinge_frame()
		for side: int in [-1, 1]:
			var eye := pose * Vector3(spec.leaf_aperture().x / 2, 1.4, side * 2.0)
			var faces := PackedVector3Array()
			preload("res://tests/hatch_render_faces.gd").collect(view.label_leaf(), eye, 1, faces)
			var triangles := TriangleMesh.new()
			assert_true(triangles.create_from_faces(faces), "leaf has visible steel")
			for x: float in [-HatchParts.HINGE_RETURN_WIDTH + 0.001, 0.001, spec.leaf_aperture().x / 2, spec.leaf_aperture().x - 0.001]:
				for y: float in [ShipGeometry.SILL_HEIGHT + 0.001, spec.aperture().y - 0.001]:
					var target := pose * Vector3(x, y, side * ShipLayout.WALL / 2)
					var hit := triangles.intersect_segment(eye, eye + (target - eye) * 2)
					assert_true(not hit.is_empty() and hit.position.distance_to(eye) <= target.distance_to(eye) + 0.001, "leaf perimeter meets its face without a dark recess: %s face=%+d" % [id, side])
		view.free()

func test_render_queries_respect_visibility_layers_and_material_culling() -> void:
	var material := StandardMaterial3D.new()
	var mesh := QuadMesh.new()
	var piece := HatchModel.mesh_piece(mesh, Transform3D.IDENTITY, 4, material)
	var query := preload("res://tests/hatch_render_faces.gd")
	var faces := PackedVector3Array()
	query.collect(piece, Vector3.BACK, 4, faces)
	assert_int_equal(faces.size(), 6, "front-facing quad is drawn")
	faces.clear()
	query.collect(piece, Vector3.FORWARD, 4, faces)
	assert_true(faces.is_empty(), "back-facing quad is culled")
	material.cull_mode = BaseMaterial3D.CULL_FRONT
	query.collect(piece, Vector3.BACK, 4, faces)
	assert_true(faces.is_empty(), "front culling follows the material")
	material.cull_mode = BaseMaterial3D.CULL_DISABLED
	query.collect(piece, Vector3.FORWARD, 4, faces)
	assert_int_equal(faces.size(), 6, "double-sided material draws the back")
	faces.clear()
	piece.visible = false
	query.collect(piece, Vector3.BACK, 4, faces)
	assert_true(faces.is_empty(), "hidden geometry cannot seal a hatch")
	piece.visible = true
	query.collect(piece, Vector3.BACK, 1, faces)
	assert_true(faces.is_empty(), "camera-excluded layers cannot seal a hatch")
	material.cull_mode = BaseMaterial3D.CULL_BACK
	piece.basis = Basis(Vector3.RIGHT, Vector3.UP, Vector3.FORWARD)
	query.collect(piece, Vector3.BACK, 4, faces)
	assert_true(faces.is_empty(), "reflection reverses the front face as in the renderer")
	query.collect(piece, Vector3.FORWARD, 4, faces)
	assert_int_equal(faces.size(), 6, "reflected face draws from its transformed normal side")
	piece.free()

func test_wall_controls_are_attached_to_the_wall_and_their_buttons() -> void:
	var spec := ShipLayout.authored().layout.door(ShipLayout.BAY_DOOR_ID)
	var view := DoorView.build(spec)
	for path: String in ["ForePanel", "AftPanel"]:
		var panel: Node3D = view.get_node(NodePath(path))
		var plate: MeshInstance3D = panel.get_child(0)
		var bounds: AABB = panel.transform * plate.transform * plate.mesh.get_aabb()
		var back := bounds.end.z if path == "ForePanel" else bounds.position.z
		assert_true(absf(back - (0.0 if path == "ForePanel" else ShipLayout.WALL)) <= 1e-6, "control housing meets the wall: " + path)
	view.free()
	var switch := Hallway._build_switch()
	var plate: MeshInstance3D = switch.get_node("Plate")
	var button: MeshInstance3D = switch.get_node("Dome")
	var plate_bounds: AABB = switch.transform * plate.transform * plate.mesh.get_aabb()
	var button_bounds: AABB = switch.transform * button.transform * button.mesh.get_aabb()
	assert_true(absf(plate_bounds.end.z - ShipLayout.CORRIDOR_WIDTH / 2) <= 1e-6, "hall switch housing reaches its wall")
	assert_true(plate_bounds.intersects(button_bounds), "red dome is attached to its switch plate")
	switch.free()

func test_lintel_return_faces_the_approach_lights() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in IDS:
		var spec := layout.door(id)
		var view := DoorView.build(spec)
		var faces := PackedVector3Array()
		_mesh_faces(view.get_node("Lintel"), faces)
		var into := signf(spec.hinge_frame().origin.z - ShipLayout.WALL / 2)
		var sloped := false
		for index: int in range(0, faces.size(), 3):
			var normal := spec.frame().basis.inverse() * (faces[index + 2] - faces[index]).cross(faces[index + 1] - faces[index]).normalized()
			if normal.y < -0.5 and normal.z * into < -0.1: sloped = true
		assert_true(sloped, "lintel has an inward bevel facing the approach room, not an unlit horizontal slot: " + id)
		view.free()

func test_rendered_collar_boxes_match_collision_within_one_micrometer() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in IDS:
		var spec := layout.door(id)
		var view := DoorView.build(spec)
		var matched := 0
		for solid: ShipGeometry.SolidSpec in ShipGeometry.hatch_frame_solids(spec):
			var suffix := String(solid.id).trim_prefix("%s/" % id)
			if not PIECES.has(suffix): continue
			var faces := PackedVector3Array()
			_mesh_faces(view.get_node(NodePath(PIECES[suffix])), faces)
			var inverse := solid.transform.affine_inverse()
			var bounds := AABB(inverse * faces[0], Vector3.ZERO)
			for vertex: Vector3 in faces: bounds = bounds.expand(inverse * vertex)
			assert_true(bounds.position.distance_to(-solid.size / 2) <= 1e-6 and bounds.size.distance_to(solid.size) <= 1e-6, "rendered box matches collision: " + String(solid.id))
			matched += 1
		assert_int_equal(matched, PIECES.size(), "every shared collar box is checked")
		view.free()

func test_wall_returns_use_the_approach_mask_and_stops_have_no_horizontal_slot() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in IDS:
		var spec := layout.door(id)
		var into := signf(spec.hinge_frame().origin.z - ShipLayout.WALL / 2)
		var approach := 1 if into > 0 else 16
		for solid: ShipGeometry.SolidSpec in ShipGeometry.hatch_wall_solids(spec):
			var wall := DoorView.split_surface(solid, spec.frame(), 1, 16)
			for mesh: MeshInstance3D in wall.get_children():
				var faces := PackedVector3Array()
				_append_mesh_vertices(mesh.mesh, mesh.transform, faces)
				for triangle: int in range(0, faces.size(), 3):
					var normal := (faces[triangle + 2] - faces[triangle]).cross(faces[triangle + 1] - faces[triangle]).normalized()
					if absf(normal.z) < 0.5:
						assert_int_equal(mesh.layers, approach, "wall return must not expose the far room's lighting: " + solid.id)
			wall.free()
		var view := DoorView.build(spec)
		var faces := PackedVector3Array()
		_mesh_faces(view.get_node("StopTop"), faces)
		var bevel := false
		for triangle: int in range(0, faces.size(), 3):
			var normal := spec.frame().basis.inverse() * (faces[triangle + 2] - faces[triangle]).cross(faces[triangle + 1] - faces[triangle]).normalized()
			if normal.y < -0.1 and normal.z * into < -0.1: bevel = true
		assert_true(bevel, "top stop must face the approach light rather than form a black horizontal slot: " + id)
		view.free()

func test_seal_box_faces_keep_flat_normals() -> void:
	var spec := ShipLayout.authored().layout.door(ShipLayout.BAY_DOOR_ID)
	var view := DoorView.build(spec)
	for piece: Node3D in view.label_leaf().get_children():
		if not "SealSteel" in String(piece.name): continue
		for surface: int in range(piece.mesh.get_surface_count()):
			var arrays: Array = piece.mesh.surface_get_arrays(surface)
			var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
			var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
			for triangle: int in range(0, indices.size(), 3):
				var a := vertices[indices[triangle]]
				var b := vertices[indices[triangle + 1]]
				var c := vertices[indices[triangle + 2]]
				var normal := (c - a).cross(b - a).normalized()
				for corner: int in range(3):
					assert_true(normals[indices[triangle + corner]].dot(normal) > 0.999999, "flat seal faces must not smooth across their square edges: " + piece.name)
	view.free()

func test_rounded_leaf_faces_do_not_bend_their_normals_into_the_bevel() -> void:
	var spec := ShipLayout.authored().layout.door(ShipLayout.BAY_DOOR_ID)
	for group: HatchParts.Group in HatchParts.leaf(spec):
		for part: HatchParts.Part in group.parts:
			if part.shape != &"rounded": continue
			var mesh := HatchModel._part_mesh(part)
			var arrays := mesh.surface_get_arrays(0)
			var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
			var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
			for triangle: int in range(0, indices.size(), 3):
				var a := vertices[indices[triangle]]
				var b := vertices[indices[triangle + 1]]
				var c := vertices[indices[triangle + 2]]
				if absf(absf(a.z) - part.size.z / 2) > 1e-6 or absf(b.z - a.z) > 1e-6 or absf(c.z - a.z) > 1e-6: continue
				var facing := Vector3(0, 0, signf(a.z))
				for corner: int in range(3):
					assert_true(normals[indices[triangle + corner]].dot(facing) > 0.999999, "flat steel face keeps its normal at the bevel: " + part.id)
