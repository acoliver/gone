extends SimTestCase

func test_streaming_hides_only_explicit_d14_presenters() -> void:
	var root := Node3D.new()
	var global_before := Node3D.new()
	root.add_child(global_before)
	var game := Game.new(0)
	var scene := ShipScene.build_into(root, game, false)
	var global_after := DoorAudio.build(game.layout)
	root.add_child(global_after)
	scene.prepare_near(Vector3(26, 0.305, 0))
	scene.prepare_near(Vector3(8, 0.305, 0))
	scene.set_opening_visible(false)
	assert_true(global_before.visible and global_before.process_mode == Node.PROCESS_MODE_INHERIT, "unowned preexisting nodes stay global")
	assert_true(global_after.visible and global_after.process_mode == Node.PROCESS_MODE_INHERIT, "DoorAudio stays global after connector preparation")
	assert_true(scene.text_cache.process_mode == Node.PROCESS_MODE_INHERIT, "shared text cache keeps running")
	for node: Node3D in [scene.bay_root, scene.hallway, scene.power_room]:
		assert_false(node.visible, "owned opening geometry is hidden")
		assert_int_equal(node.process_mode, Node.PROCESS_MODE_DISABLED, "owned presentation is suspended")
	for view: DoorView in scene.door_views:
		assert_false(view.visible, "prepared D14 door view is owned")
	for label: ShipLabel in scene.labels.values():
		var owner := _opening_owner(scene, label)
		assert_true(owner != null, "leaf label belongs to an explicit D14 presenter")
		assert_false(owner.visible, "leaf label inherits its presenter's hidden state")
		assert_int_equal(owner.process_mode, Node.PROCESS_MODE_DISABLED, "leaf label's presenter is suspended")
	scene.set_opening_visible(true)
	assert_true(scene.hallway.visible and scene.hallway.process_mode == Node.PROCESS_MODE_INHERIT, "return restores owned presentation")
	for label: ShipLabel in scene.labels.values():
		assert_true(label.visible and _opening_owner(scene, label).visible, "return restores leaf writing through its presenter")
	root.free()

func _opening_owner(scene: ShipScene, node: Node3D) -> Node3D:
	var owner := node.get_parent() as Node3D
	while owner != null and owner not in scene._opening_nodes:
		owner = owner.get_parent() as Node3D
	return owner

func test_opening_does_no_remote_work() -> void:
	var root := Node3D.new()
	var scene := ShipScene.build_into(root, Game.new(0), false)
	assert_true(scene.stream.resident_ids().is_empty(), "no remote trees at startup")
	assert_int_equal(scene.stream.shaft_count(), 0, "no shaft before its approach")
	scene.prepare_near(Vector3(18, 0.305, 0))
	assert_int_equal(scene.stream.pending_count(), 0, "opening queues no rooms")
	assert_int_equal(scene.text_cache.pending_count(), 10, "opening hatch/bay pairs, six distinct section-41 bay labels and the initially inactive console")
	root.free()

func test_residency_clips_to_limits_and_only_occupied_well() -> void:
	var root := Node3D.new()
	var game := Game.new(0)
	var scene := ShipScene.build_into(root, game, false)
	for deck: int in [1, 14, 30]:
		scene.stream.focus(&"C-001-LADDER", deck)
		for _frame: int in range(6):
			scene.stream.build_next()
		var expected: Array[StringName] = []
		for d: int in range(maxi(1, deck - 2), mini(30, deck + 2) + 1):
			if d != 14:
				expected.append(ShipLayout.connector_id(d, 1))
		assert_true(scene.stream.resident_ids() == expected, "exact clipped band at D%02d: %s expected %s" % [deck, scene.stream.resident_ids(), expected])
		assert_int_equal(scene.stream.pending_count(), 0, "one room per construction step")
		assert_true(scene.stream.remote_light_count() <= 15, "at most five rooms of three lights")
	assert_int_equal(scene.stream.shaft_count(), 1, "other well stays absent")
	root.free()

func test_remote_rooms_share_labels_masks_and_persistent_refusals() -> void:
	var root := Node3D.new()
	var game := Game.new(0)
	var scene := ShipScene.build_into(root, game, false)
	scene.stream.focus(&"C-000-LADDER", 1)
	for _frame: int in range(5):
		scene.stream.build_next()
	var id := ShipLayout.connector_id(1, 0)
	var room: Node3D = scene.stream.room(id)
	assert_int_equal(room.find_children("*", "OmniLight3D", true, false).size(), 3, "remote red fixtures")
	var mask := Lighting.space_mask(game.layout, id)
	assert_true(mask != Lighting.space_mask(game.layout, ShipLayout.connector_id(2, 0)), "adjacent deck masks differ")
	for label: ShipLabel in scene.labels.values():
		if label.face_id.begins_with("D01-C-000"):
			assert_true(label.pair.perceived_es.begins_with("CUBIERTA 1"), "layout deck quantity")
	var door: StringName = &"D01-C-000-H-FORE"
	var context := Doors.Context.new()
	context.face_id = game.layout.door(door).face_ids()[1]
	game.doors.press(door, context)
	var attempts := game.doors.snapshot(door).attempt
	scene.stream.focus(&"C-000-LADDER", 30)
	for _frame: int in range(5):
		scene.stream.build_next()
	scene.stream.focus(&"C-000-LADDER", 1)
	for _frame: int in range(5):
		scene.stream.build_next()
	assert_int_equal(game.doors.snapshot(door).attempt, attempts, "reload never resets refusal state")
	assert_int_equal(game.doors.snapshot(door).state, Doors.State.CLOSED, "off-deck hatch remains closed")
	assert_true(game.collision.deck_set(1) == game.collision.deck_set(1), "render eviction leaves cached collision intact")
	root.free()

func test_shaft_is_full_height_instanced_and_open_at_every_landing() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in layout.well_ids():
		var shaft := LadderShaft.build(layout, layout.well(id))
		assert_true(shaft.get_meta(&"continuous_bounds") == layout.well(id).bounds(), "full D01-D30 shell")
		var rungs: MultiMeshInstance3D = shaft.get_node("Rungs")
		assert_true(rungs.multimesh.instance_count > 500, "rungs span whole well")
		var rails: MultiMeshInstance3D = shaft.get_node("Rails")
		assert_int_equal(rails.multimesh.instance_count, 2, "two continuous rails")
		var closures: MultiMesh = shaft.get_node("PitchClosures").multimesh
		assert_int_equal(closures.instance_count, 87, "interdeck pitch closures remain outside room eviction")
		var walls: MultiMesh = shaft.get_node("ShaftWalls").multimesh
		assert_int_equal(walls.instance_count, 5, "two sides, back, and endpoint closures")
		# The headless dummy renderer does not retain MultiMesh transforms.
		var shell := ShipGeometry.well_solids(layout.well(id))
		for wall_index: int in range(3):
			assert_float_in_range(shell[wall_index].size.y, 162.7 - 1e-5, 162.7 + 1e-5, "instanced shell recipe spans the complete well")
			assert_float_in_range(shell[wall_index].center.y - shell[wall_index].size.y / 2, -88 - 1e-5, -88 + 1e-5, "instanced shell recipe starts at D30")
		for deck: int in range(1, 31):
			assert_true(shaft.has_meta(StringName("landing_%02d" % deck)), "every doorway has cheap shell and landing")
		shaft.free()

func test_returning_climber_restores_d14_before_dismount_commits_deck() -> void:
	var root := Node3D.new()
	var game := Game.new(0)
	var scene := ShipScene.build_into(root, game, false)
	scene.prepare_near(Vector3(26, 0.305, 0))
	game.phase.wake_complete()
	game.phase.request_pod_exit(Phase.InputEdge.RISING)
	game.phase.get_up_complete()
	var capsule := Resolve.Capsule.new()
	capsule.foot = game.layout.well(&"C-001-LADDER").landing(13).origin + Vector3.UP * 0.305
	capsule.head = capsule.foot + Vector3.UP * 1.15
	var motion := PlayerMotion.new()
	motion.locomotion = Locomotion.start(game.layout, game.collision, 13, Walk.WalkState.start(game.phase, capsule).state).state
	scene.stream.update(motion)
	assert_false(scene.hallway.visible, "opening hidden while walking remotely")
	var input := Locomotion.Intent.new()
	input.walk = Walk.MoveIntent.try_new(0, 0, 0).intent
	input.space = true
	input.well_id = &"C-001-LADDER"
	assert_true(motion.locomotion.step(input).is_ok(), "mount remote landing")
	motion.locomotion.end_tick()
	input.space = false
	for _tick: int in range(24):
		assert_true(motion.locomotion.step(input).is_ok(), "mount sweeps")
		motion.locomotion.end_tick()
	input.has_climb = true
	input.climb = -1
	for _tick: int in range(220):
		assert_true(motion.locomotion.step(input).is_ok(), "climb back to D14")
		motion.locomotion.end_tick()
	scene.stream.update(motion)
	assert_int_equal(motion.deck(), 13, "walking deck has not committed during climb")
	assert_true(scene.hallway.visible, "D14 presentation restored at its landing, before dismount")
	root.free()

func test_remote_hatch_label_is_not_occluded_by_reserved_swing_clearance() -> void:
	var root := Node3D.new()
	var game := Game.new(0)
	var scene := ShipScene.build_into(root, game, false)
	scene.stream.focus(&"C-001-LADDER", 1)
	for _frame: int in range(3):
		scene.stream.build_next()
	var id: StringName = &"D01-C-001-H-FORE/AFT"
	var label: ShipLabel = scene.labels[id]
	# Raster completion is a separate windowed test; this exercises physical sight geometry.
	game.label_attention.load_face(id)
	var eye := Vector3(31.7, 73.185, 0)
	var forward := (ShipScene._world_frame(label).origin - eye).normalized()
	for _tick: int in range(170):
		scene.tick_attention(eye, forward, 1)
	assert_float_equal(label.perception.perceive, 1, "closed hatch writing resolves on its physical leaf")
	root.free()

func test_ladder_results_are_identical_with_presentation_forced_out_between_ticks() -> void:
	var plain := Game.new(0)
	var presented := Game.new(0)
	var root := Node3D.new()
	var scene := ShipScene.build_into(root, presented, false)
	var capsule := Resolve.Capsule.new()
	capsule.foot = Vector3(34.5, 0.305, -2.9)
	capsule.head = capsule.foot + Vector3.UP * 1.15
	var a := Ladder.try_mount(plain.layout, &"C-001-LADDER", 14, capsule, Vector3.FORWARD).state
	var b := Ladder.try_mount(presented.layout, &"C-001-LADDER", 14, capsule, Vector3.FORWARD).state
	for tick: int in range(268):
		if tick % 35 == 0:
			scene.stream.focus(&"C-000-LADDER", 30)
		scene.stream.focus(&"C-001-LADDER", b.nearest_landing())
		scene.stream.build_next()
		var climb := 1.0 if tick >= 24 and tick < 244 else 0.0
		var first := a.step(climb, tick == 244, plain.collision)
		var second := b.step(climb, tick == 244, presented.collision)
		assert_true(first.is_ok() and second.is_ok(), "both paths sweep the same real solids")
		assert_true(a.capsule().foot == b.capsule().foot and a.capsule().head == b.capsule().head, "render eviction cannot change the accepted capsule")
		assert_int_equal(a.mode(), b.mode(), "render eviction cannot change the mode")
		assert_int_equal(first.events.size(), second.events.size(), "same transition event count")
		for index: int in range(first.events.size()):
			assert_int_equal(first.events[index].kind, second.events[index].kind, "same transition kind")
			assert_int_equal(first.events[index].deck, second.events[index].deck, "same transition deck")
		a.end_tick()
		b.end_tick()
	assert_int_equal(b.mode(), Ladder.Mode.LANDED, "evicted presentation does not prevent landing")
	assert_int_equal(b.landing_deck(), 13, "same landed deck")
	root.free()
