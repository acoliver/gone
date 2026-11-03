extends SimTestCase

func _register(attention: LabelAttention, id: StringName, center: Vector3 = Vector3.ZERO) -> void:
	attention.register_face(id, 14, &"room", Transform3D(Basis(), center), Vector2(0.92, 0.46))

func test_first_resolution_is_shared_but_face_state_is_independent() -> void:
	var memory := DisplayPerception.Memory.new()
	var attention := LabelAttention.new(memory)
	_register(attention, &"first")
	_register(attention, &"second", Vector3(8, 0, 0))
	for tick: int in range(168):
		attention.tick(14, Vector3(0, 0, 2), Vector3.FORWARD, [])
		if tick == 71:
			assert_float_equal(attention.state(&"first").perceive, 0, "first hold unchanged")
	assert_float_equal(attention.state(&"first").perceive, 1, "first ramp unchanged")
	assert_true(memory.has_resolved, "shared memory completes")
	assert_float_equal(attention.state(&"second").perceive, 0, "other face independent")
	for tick: int in range(57):
		attention.tick(14, Vector3(8, 0, 2), Vector3.FORWARD, [])
		if tick == 20:
			assert_float_equal(attention.state(&"second").perceive, 0, "later hold unchanged")
	assert_float_equal(attention.state(&"second").perceive, 1, "later ramp unchanged")
	assert_int_equal(attention.last_ticked_count, 1, "far zero states do no per-tick work")
	var console := DisplayPerception.new(memory)
	for tick: int in range(57): console.tick(true)
	assert_float_equal(console.perceive, 1, "label resolution establishes later console timing")

func test_unloaded_faces_decay_and_reload_cannot_restore_stale_blend() -> void:
	var attention := LabelAttention.new(DisplayPerception.Memory.new())
	_register(attention, &"face")
	for tick: int in range(168): attention.tick(14, Vector3(0, 0, 2), Vector3.FORWARD, [])
	attention.unload(&"face")
	for tick: int in range(21): attention.tick(14, Vector3(0, 0, 2), Vector3.FORWARD, [])
	assert_float_equal(attention.state(&"face").perceive, 0, "evicted state decays fully")
	assert_int_equal(attention.decaying_count(), 0, "finished decay removed")
	_register(attention, &"face")
	assert_float_equal(attention.state(&"face").perceive, 0, "reload retains decayed state")

func test_range_front_deck_rectangle_and_occlusion_gate_attention() -> void:
	var attention := LabelAttention.new(DisplayPerception.Memory.new())
	_register(attention, &"face")
	var wall: Array[AABB] = [AABB(Vector3(-1, -1, 0.8), Vector3(2, 2, 0.2))]
	for tick: int in range(180):
		attention.tick(14, Vector3(0, 0, 2), Vector3.FORWARD, wall)
		attention.tick(13, Vector3(0, 0, 2), Vector3.FORWARD, [])
		attention.tick(14, Vector3(0, 0, -2), Vector3.BACK, [])
		attention.tick(14, Vector3(0, 0, 4.01), Vector3.FORWARD, [])
		attention.tick(14, Vector3(0, 0, 2), Vector3.RIGHT, [])
	assert_float_equal(attention.state(&"face").perceive, 0, "ineligible faces never resolve")

func test_layout_sign_frames_sizes_and_destinations_are_generated() -> void:
	var layout := ShipLayout.authored().layout
	var face := layout.face(&"D14-C-001-H-FORE/FORE")
	var frame := layout.door(face.door_id()).frame() * face.label_frame()
	assert_close(frame.origin, Vector3(29.99, 2.85, 0), "corridor-facing sign anchor")
	assert_vec3_equal(frame.basis.z, Vector3.LEFT, "sign faces corridor")
	assert_true(face.label_size() == Vector2(0.92, 0.46), "hatch size")
	var lift := layout.lift(&"D14-C-001-LIFT")
	assert_close(lift.label_anchor().origin, Vector3(33, 2.55, 1.49), "lift sign anchor")
	assert_vec3_equal(lift.label_anchor().basis.z, Vector3.FORWARD, "lift sign faces connector")
	assert_true(lift.label_size() == Vector2(0.92, 0.23), "lift size")
