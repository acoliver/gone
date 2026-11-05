extends SimTestCase

const IDS: Array[StringName] = [ShipLayout.BAY_DOOR_ID, &"D14-C-000-H-FORE", &"D14-C-000-H-AFT", &"D14-C-001-H-FORE", &"D14-C-001-H-AFT"]

func _rendered_parts(node: Node3D, parent: Transform3D, parts: Dictionary) -> void:
	var frame := parent * node.transform
	if node is MeshInstance3D:
		var poses: Dictionary = node.mesh.get_meta(&"part_transforms", {})
		var submitted: Dictionary = preload("res://tests/hatch_mesh_ranges.gd").parts(node.mesh)
		for id: StringName in submitted:
			assert_true(poses.has(id), "rendered range has a physical part pose: " + String(id))
			assert_false(parts.has(id), "rendered part ids are unique")
			var pose: Transform3D = poses[id]
			parts[id] = {"transform": frame * pose, "bounds": submitted[id].bounds}
	if node is MultiMeshInstance3D:
		var poses: Array = node.multimesh.get_meta(&"instance_poses")
		for index: int in range(poses.size()):
			var id := StringName("%s/%03d" % [node.name, index])
			assert_false(parts.has(id), "rivet ids are unique")
			parts[id] = {"transform": frame * poses[index], "bounds": node.multimesh.mesh.get_aabb()}
	for child: Node3D in node.get_children(): _rendered_parts(child, frame, parts)

func test_rendered_leaf_and_sight_have_identical_parts_and_local_poses() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in IDS:
		var spec := layout.door(id)
		var sight: Array = ShipGeometry.hatch_sight_boxes(spec, spec.swing_radians(0))
		assert_true(not sight.is_empty() and not sight[0] is AABB, "sight must preserve oriented physical parts, not world AABBs")
		if sight.is_empty() or sight[0] is AABB: return
		var view := DoorView.build(spec)
		var rendered: Dictionary = {}
		_rendered_parts(view.label_leaf(), Transform3D.IDENTITY, rendered)
		assert_int_equal(rendered.size(), sight.size(), "same complete physical part set: " + id)
		for box: Variant in sight:
			assert_true(rendered.has(box.id), "sight part is rendered: " + String(box.id))
			if not rendered.has(box.id): continue
			var pose: Transform3D = rendered[box.id].transform
			var expected: Transform3D = box.local_transform
			assert_true(pose.origin.distance_to(expected.origin) <= 1e-6, "same leaf-local position: " + String(box.id))
			for axis: int in range(3):
				assert_true(pose.basis[axis].distance_to(expected.basis[axis]) <= 1e-6, "same leaf-local basis: " + String(box.id))
			var bounds: AABB = rendered[box.id].bounds
			assert_true(bounds.position.distance_to(box.bounds.position) <= 1e-6 and bounds.size.distance_to(box.bounds.size) <= 1e-6, "actual mesh bounds agree with sight dimensions: " + String(box.id))
		view.free()

func _open(game: Game, id: StringName) -> void:
	var context := Doors.Context.new()
	context.rod_carried = true
	context.face_id = game.layout.door(id).face_ids()[0]
	var attempts := 1 if id == ShipLayout.BAY_DOOR_ID else HatchResistance.schedule(game.run_seed, id).weights.size()
	for attempt: int in range(attempts):
		game.doors.press(id, context)
		for tick: int in range(6): game.doors.tick()
	for tick: int in range(48): game.doors.tick()
	assert_int_equal(game.doors.snapshot(id).state, Doors.State.OPEN, "fixture opens through the real store")
	game.collision.open_door(id)


func test_every_seeded_open_hatch_resolves_from_each_exposed_face_and_refuses_back_and_wall() -> void:
	for seed: int in [0, 7, -913]:
		var game := Game.new(seed)
		var root := Node3D.new()
		var scene := ShipScene.build_into(root, game, false)
		scene.prepare_near(Vector3(26, 0, 0))
		scene.prepare_near(Vector3(10, 0, 0))
		for id: StringName in IDS:
			_open(game, id)
			var spec := game.layout.door(id)
			for view: DoorView in scene.door_views: view.present(game.doors.snapshot(view.door_id()))
			var hinge := spec.hinge_frame()
			hinge.basis = Basis(Vector3.UP, spec.swing_radians(seed))
			for face_id: StringName in spec.face_ids():
				var face := game.layout.face(face_id)
				var local := face.leaf_label_frame(spec)
				if seed == 0 and id == &"D14-C-001-H-FORE" and face_id == spec.face_ids()[0]:
					assert_true(absf(rad_to_deg(spec.swing_radians(seed)) + 117.919218) < 1e-6, "review rest-angle fixture")
					# Andrew's Round 11 clear panel raises the label above the wheel by 36 mm.
					assert_true(local.origin.distance_to(Vector3(0.62, 1.86, -0.26)) < 1e-6, "clear-panel flush-slab label-local fixture")
				var frame := spec.frame() * hinge * local
				var normal := frame.basis.z
				var wall_boxes := ShipGeometry.deck_static_solids(game.layout, 14)
				var eye := Vector3.INF
				# Some exposed faces point toward a nearby wall. Require a clear static ray.
				for distance: float in [1.5, 1.0, 0.75, 0.5, 0.3]:
					var candidate := frame.origin + normal * distance
					var clear := true
					for solid: ShipGeometry.SolidSpec in wall_boxes:
						var box := ShipGeometry.box_aabb(solid)
						var bounds := AABB(box.min_corner(), box.max_corner() - box.min_corner())
						var hit := Interactions.segment_hit(candidate, frame.origin, bounds)
						if bounds.has_point(candidate) or (hit >= 0 and hit < 1.0 - 0.00001):
							clear = false
							break
					if clear:
						eye = candidate
						break
				assert_true(eye.is_finite(), "front viewpoint and ray clear static geometry: " + String(face_id))
				if not eye.is_finite():
					root.free()
					return
				if seed == 0 and id == &"D14-C-001-H-FORE" and face_id == spec.face_ids()[0]:
					assert_true(absf(eye.distance_to(frame.origin) - 1.5) < 1e-6, "review eye is 1.5m along the exposed normal")
				game.label_attention.load_face(face_id)
				for tick: int in range(168): scene.tick_attention(eye, -normal)
				assert_float_equal(game.label_attention.state(face_id).perceive, 1, "exposed opened label resolves: %s seed %d" % [face_id, seed])
				for tick: int in range(21): scene.tick_attention(frame.origin - normal * 0.5, normal)
				assert_float_equal(game.label_attention.state(face_id).perceive, 0, "view through the back of the leaf is refused")
				var wall := AABB(eye.lerp(frame.origin, 0.5) - Vector3.ONE * 0.05, Vector3.ONE * 0.1)
				var hit := Interactions.segment_hit(eye, frame.origin, wall)
				assert_true(hit >= 0 and hit < 1.0 - 0.00001, "wall fixture crosses the otherwise readable ray")
				var snapshot := game.doors.snapshot(id)
				var parts := ShipGeometry.hatch_sight_boxes(spec, snapshot.open_radians, snapshot.wheel_angle)
				var blocked_by_leaf := false
				for part: ShipGeometry.SightBox in parts:
					var leaf_hit := Interactions.segment_hit(part.inverse * (frame.origin - normal * 0.5), part.inverse * frame.origin, part.bounds)
					if leaf_hit >= 0 and leaf_hit < 1.0 - 0.00001: blocked_by_leaf = true
				assert_true(blocked_by_leaf, "oriented physical leaf blocks the segment from behind")
				for tick: int in range(168): game.label_attention.tick(14, eye, -normal, [wall], parts)
				assert_float_equal(game.label_attention.state(face_id).perceive, 0, "wall occlusion remains refused: " + String(face_id))
		root.free()
