extends SimTestCase

func test_round7_leaf_is_one_physical_description() -> void:
	var spec := ShipLayout.authored().layout.door(&"D14-C-001-H-FORE")
	var groups := HatchParts.leaf(spec)
	var found: Dictionary = {}
	for group: HatchParts.Group in groups:
		for part: HatchParts.Part in group.parts: found[String(part.id)] = part
	# The generated wheel replaces ring/flange/spokes with one whole object;
	# whole latches replace their plate/arm/grip/pivot/bolt reservations.
	assert_true(found.has("Wheel/hub"), "whole generated wheel is a physical leaf part")
	assert_true(found.has("Wheel/hazard-band"), "hazard band belongs to the rotating physical wheel")
	assert_true(found.has("StrapHinges/ForeSteel/barrel-0"), "hinge barrel is a physical part")
	assert_true(found.has("Lugs/ForeSteel/whole-2"), "all three latch dogs are physical parts")
	if not found.has("Wheel/hub"): return
	assert_float_equal(found["Wheel/hub"].radius, 0.3215, "driver-approved 643 mm wheel outside diameter")
	# Andrew's 2026-11-05 flush slab follows the ring instead of the old 255 mm corner.
	assert_float_equal(found["ForeSteel/plate"].radius, 0.24, "flush rounded face")
	assert_false(found.has("ForeSteel/brace-0"), "no old X braces behind the concept skin")

func test_round7_surround_is_collision_owned() -> void:
	var spec := ShipLayout.authored().layout.door(&"D14-C-001-H-FORE")
	var ring := 0
	var throat := 0
	var piers := 0
	for solid: ShipGeometry.SolidSpec in ShipGeometry.hatch_frame_solids(spec):
		if "/RING/" in String(solid.id): ring += 1
		if "/THROAT/" in String(solid.id): throat += 1
		if "/PIER/" in String(solid.id): piers += 1
	assert_true(ring >= 36, "rounded ring is partitioned around its empty opening")
	assert_int_equal(throat, 36, "fitted throat has 36 actual solid cells")
	assert_int_equal(piers, 0, "the continuous lower ring has no rectangular pier overlays")

func test_leaf_weather_is_promoted_and_role_owned() -> void:
	assert_true(FileAccess.file_exists("res://assets/surfaces/hatch/leaf-weather.png"), "unique procedural leaf weather ships")
	var material := Surfaces.material(&"hatch_leaf")
	assert_true(material.get_shader_parameter(&"leaf_paint") == true, "leaf role selects round7 flaking")
	assert_true(material.get_shader_parameter(&"leaf_weather") is Texture2D, "leaf mask is an imported resource")
	assert_true(not Surfaces.STEEL.code.contains("finish_chroma"), "production preserves full rust colour without a desaturation control")

func _boxes(node: Node3D, boxes: Array[AABB]) -> void:
	if node is MeshInstance3D:
		if node.mesh.has_meta(&"service_bounds"):
			var bounds: Array[AABB] = node.mesh.get_meta(&"service_bounds")
			assert_int_equal(bounds.size(), node.mesh.get_surface_count(), "every batched fitting retains its original swept bounds")
			for surface: int in range(bounds.size()):
				var vertices: PackedVector3Array = node.mesh.surface_get_arrays(surface)[Mesh.ARRAY_VERTEX]
				for vertex: Vector3 in vertices:
					assert_true(bounds[surface].grow(0.000001).has_point(vertex), "original fitting bounds enclose its actual batched vertices")
				boxes.append(Surfaces.world_frame(node) * bounds[surface])
		elif node.mesh.has_meta(&"part_ranges"):
			for part: Dictionary in preload("res://tests/hatch_mesh_ranges.gd").parts(node.mesh).values():
				boxes.append(preload("res://tests/hatch_mesh_ranges.gd").world_bounds(node.mesh, part, Surfaces.world_frame(node)))
		else:
			boxes.append(Surfaces.world_frame(node) * node.mesh.get_aabb())
	if node is MultiMeshInstance3D:
		for pose: Transform3D in node.multimesh.get_meta(&"instance_poses"):
			boxes.append(Surfaces.world_frame(node) * pose * node.multimesh.mesh.get_aabb())
	for child: Node3D in node.get_children(): _boxes(child, boxes)

func test_prop_clearance_collects_each_multimesh_instance_in_world_space() -> void:
	var root := Node3D.new()
	root.position = Vector3(7, 3, -2)
	var rivets := MultiMeshInstance3D.new()
	rivets.position = Vector3(1, 2, 3)
	root.add_child(rivets)
	var batch := MultiMesh.new()
	batch.transform_format = MultiMesh.TRANSFORM_3D
	batch.mesh = BoxMesh.new()
	batch.instance_count = 2
	var poses: Array[Transform3D] = [Transform3D(Basis(), Vector3(-0.5, 0, 0)), Transform3D(Basis(Vector3.UP, 0.4), Vector3(0.5, 0.25, 0))]
	batch.set_meta(&"instance_poses", poses)
	for index: int in range(poses.size()): batch.set_instance_transform(index, poses[index])
	rivets.multimesh = batch
	var boxes: Array[AABB] = []
	_boxes(root, boxes)
	var expected: Array[AABB] = []
	for pose: Transform3D in poses:
		expected.append(Surfaces.world_frame(rivets) * pose * batch.mesh.get_aabb())
	assert_true(boxes == expected, "prop-clearance collector includes each rivet with its instance and ancestor transforms")
	root.free()

func test_services_clear_walk_band_leaf_swing_labels_and_switch() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in [ShipLayout.BAY_DOOR_ID, &"D14-C-000-H-FORE", &"D14-C-000-H-AFT", &"D14-C-001-H-FORE", &"D14-C-001-H-AFT"]:
		var spec := layout.door(id)
		var view := DoorView.build(spec)
		var props: Array[AABB] = []
		for path: String in ["ForeServices", "AftServices", "ForePanel", "AftPanel"]: _boxes(view.get_node(path), props)
		for prop: AABB in props:
			var local := spec.frame().affine_inverse() * prop
			var walk := AABB(Vector3(-0.60, 0.08, -1), Vector3(1.20, 2.32, 2))
			assert_false(local.intersects(walk), "service hardware stays outside the walk band: %s %s" % [id, local])
		var degrees: Array[float] = []
		for degree: int in range(131): degrees.append(float(degree))
		for seed: int in [0, 7, -913]: degrees.append(absf(rad_to_deg(spec.swing_radians(seed))))
		for degree: float in degrees:
			view.get_node("Hinge").basis = Basis(Vector3.UP, signf(spec.swing_radians()) * deg_to_rad(degree))
			var moving: Array[AABB] = []
			_boxes(view.label_leaf(), moving)
			assert_true(moving.size() > 50, "prop clearance includes steel, wheel, latches, straps and individual rivets")
			for prop: AABB in props:
				for part: AABB in moving:
					var contact := prop.intersection(part)
					if contact.size.x > 0.001 and contact.size.y > 0.001 and contact.size.z > 0.001:
						assert_true(false, "%s service touches leaf at degree %.6f: %s" % [id, degree, contact])
						view.free()
						return
		for seed: int in [0, 7, -913]:
			var hinge := spec.hinge_frame()
			hinge.basis = Basis(Vector3.UP, spec.swing_radians(seed))
			for face_id: StringName in spec.face_ids():
				var frame := spec.frame() * hinge * layout.face(face_id).leaf_label_frame(spec)
				for prop: AABB in props:
					var hit := Interactions.segment_hit(frame.origin + frame.basis.z * 0.3, frame.origin, prop)
					assert_false(hit >= 0 and hit < 1.0 - 0.00001, "props do not block exposed label sight: " + String(face_id))
		if id == ShipLayout.BAY_DOOR_ID:
			var target := layout.anchor(&"D14-HALL-SWITCH").origin
			for prop: AABB in props:
				assert_false(Interactions.segment_hit(target - Vector3(0, 0, 1), target, prop) >= 0, "hatch props do not block the hall switch")
		view.free()

func test_surround_cell_mesh_bounds_equal_the_collision_boxes() -> void:
	var spec := ShipLayout.authored().layout.door(&"D14-C-001-H-FORE")
	for solid: ShipGeometry.SolidSpec in ShipGeometry.hatch_surround_solids(spec):
		var bounds := HatchModel.solid_mesh(solid).get_aabb()
		assert_true(bounds.position.distance_to(-solid.size / 2) <= 1e-6 and bounds.size.distance_to(solid.size) <= 1e-6, "fixed surround mesh and collision share dimensions: " + String(solid.id))

func _assert_outward_caps(mesh: Mesh, depth: float) -> void:
	var arrays := mesh.surface_get_arrays(0)
	var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
	var count := 0
	for triangle: int in range(0, indices.size(), 3):
		var a := vertices[indices[triangle]]
		var b := vertices[indices[triangle + 1]]
		var c := vertices[indices[triangle + 2]]
		if absf(a.z - b.z) > 1e-6 or absf(a.z - c.z) > 1e-6: continue
		assert_true(absf(absf(a.z) - depth / 2) < 1e-6, "cap is on the extrusion boundary")
		var normal := (c - a).cross(b - a).normalized()
		assert_true(normal.z * a.z > 0, "opaque extrusion caps face outward, not into the metal")
		count += 1
	assert_true(count >= 4, "both end caps are present")

func test_surround_and_band_caps_have_outward_winding() -> void:
	var spec := ShipLayout.authored().layout.door(&"D14-C-001-H-FORE")
	for solid: ShipGeometry.SolidSpec in ShipGeometry.hatch_surround_solids(spec):
		if not solid.section.is_empty(): _assert_outward_caps(HatchModel.solid_mesh(solid), solid.size.z)
	for group: HatchParts.Group in HatchParts.leaf(spec):
		for part: HatchParts.Part in group.parts:
			if part.shape == &"band": _assert_outward_caps(HatchModel._part_mesh(part), part.size.z)

func test_hatch_lamps_reuse_existing_circuit_keys_and_follow_switching() -> void:
	var game := Game.new(0)
	var root := Node3D.new()
	var scene := ShipScene.build_into(root, game, false)
	assert_int_equal(scene.hallway.lights().size(), 8, "hallway emergency key inventory is unchanged")
	assert_int_equal(scene.lighting.lights().size(), 8, "bay emergency key inventory is unchanged")
	var moved := 0
	for light: OmniLight3D in scene.hallway.lights() + scene.lighting.lights():
		if not light.get_parent().has_meta(&"hatch_lamp"): continue
		moved += 1
		assert_false(light.get_parent().get_node("Lens").visible, "old fixture lens is not duplicated")
		var bay_doorway := light.get_parent() == scene.lighting.fixture(ShipLayout.BAY_HATCH_KEY_ID)
		assert_float_equal(light.omni_range, 5.5 if bay_doorway else 2.5, "only the bay hatch key has the longer doorway spill")
	assert_int_equal(moved, 4, "two bay faces and two section-end faces reuse four existing keys")
	var bay_lens: MeshInstance3D = scene.hatch.view.get_node("AftServices/Lamp/Lens")
	var hall_lens: MeshInstance3D = scene.hatch.view.get_node("ForeServices/Lamp/Lens")
	assert_true(bay_lens.material_override == scene.lighting.lens_material(), "bay cage follows the bay circuit")
	assert_true(hall_lens.material_override == scene.hallway.lens_material(), "hall cage follows the hallway circuit")
	assert_true(hall_lens.material_override.emission == Color.BLACK, "unpowered hall lens is dark")
	game.light_hallway()
	scene.hallway.process_frame(Sim.LOGICAL_TICK_SECS * Lighting.FIXTURE_SETTLE_TICKS)
	assert_true(hall_lens.material_override.emission.r > 0, "cage lens lights with its existing circuit")
	root.free()

func test_threshold_keeps_authored_opening_walk_at_the_coaming_height() -> void:
	var game := Game.new(0)
	var player := Player.build(game, null)
	player.scripted = true
	player.adapter = InputPlane.ScriptedAdapter.new()
	player._ready()
	game.wake_state.mark_ready()
	var route := HarnessRoute.new(player, 5400)
	var scenario: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://scenarios/power-room.json"))
	route.replay_prefix(scenario.actions, 1256)
	assert_true(absf(player.motion.capsule().foot.y - 0.385) < 1e-6, "rounded frame must not lift the standing capsule above the unchanged 80mm coaming")
	player.free()

func _steel_instances(node: Node) -> int:
	var count := 0
	if node is MeshInstance3D and node.material_override is ShaderMaterial and node.material_override.shader == Surfaces.STEEL:
		count += 1
	for child: Node in node.get_children(): count += _steel_instances(child)
	return count

func test_services_batch_steel_without_consuming_one_shader_slot_per_fitting() -> void:
	var view := DoorView.build(ShipLayout.authored().layout.door(&"D14-C-001-H-FORE"))
	var count := 0
	for path: String in ["ForeServices", "AftServices", "ForePanel", "AftPanel"]:
		count += _steel_instances(view.get_node(path))
	assert_true(count <= 32, "service steel must fit the existing instance-uniform buffer across streamed rooms, not allocate one instance per clamp")
	view.free()
