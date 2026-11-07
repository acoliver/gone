extends SimTestCase

func test_rebuilding_an_open_hatch_keeps_leaf_local_writing_and_face_identity() -> void:
	var game := Game.new(0)
	var root := Node3D.new()
	var scene := ShipScene.build_into(root, game, false)
	scene.prepare_near(Vector3(28.5, 0, 0))
	var id: StringName = &"D14-C-001-H-FORE"
	var face: StringName = &"D14-C-001-H-FORE/FORE"
	var context := Doors.Context.new()
	context.face_id = face
	for _attempt: int in range(HatchResistance.schedule(0, id).weights.size()):
		game.doors.press(id, context)
		for _tick: int in range(6): game.advance_doors()
	for _tick: int in range(48): game.advance_doors()
	assert_int_equal(game.doors.snapshot(id).state, Doors.State.OPEN, "fixture opens the stored hatch")
	var local: Transform3D = scene.labels[face].transform
	root.free()
	root = Node3D.new()
	scene = ShipScene.build_into(root, game, false)
	scene.prepare_near(Vector3(28.5, 0, 0))
	assert_true(scene.labels[face].transform.is_equal_approx(local), "reload must not counter-rotate the ink back into the closed plane")
	assert_true(ShipScene._world_frame(scene.labels[face]).basis.z.dot(Vector3.LEFT) < 0.01, "rebuilt ink remains on the open leaf")
	root.free()

func test_prefetched_console_changes_cached_pixels_in_the_same_tick() -> void:
	var cache := ShipTextCache.new()
	var game := Game.new(0)
	var room := PowerRoom.build(game, cache)
	room.tick_console_attention(Vector3(27, 1.6, -0.5), Vector3.FORWARD)
	assert_int_equal(cache.pending_count(), 2, "doorway approach prefetches both console states")
	var pairs: Array[ShipTextCache.Pair] = []
	for state: String in ["inactive", "active"]:
		var head := ShipText.message("secondary_power.heading")
		var tail := ShipText.message("secondary_power." + state)
		var pair := cache.acquire(ShipText.LabelText.new(head.native + "\n" + tail.native, head.perceived_es + "\n" + tail.perceived_es), &"console")
		var image := Image.create(2, 2, false, Image.FORMAT_RGBA8)
		image.fill(Color.RED if state == "inactive" else Color.GREEN)
		cache.complete(pair.key, image, image)
		pairs.append(pair)
	for pair: ShipTextCache.Pair in pairs:
		if pair == pairs[1]:
			game.press_console()
		room.process_frame(Sim.LOGICAL_TICK_SECS)
		var quad := room.console_display.get_node("TextSurface") as MeshInstance3D
		assert_true(quad.material_override.get_shader_parameter("native_ink") == pair.native_texture(), "console press installs prefetched pixels immediately")
		assert_int_equal(cache.pending_count(), 0, "press queues no raster work")
	room.free()
	cache.free()

func test_repeated_labels_share_pixels_without_sharing_material_or_blend() -> void:
	var cache := ShipTextCache.new()
	var memory := DisplayPerception.Memory.new()
	var first := ShipLabel.build(cache, ShipText.deck_label(14), &"one", Transform3D.IDENTITY, Vector2(0.92, 0.23), DisplayPerception.new(memory))
	var second := ShipLabel.build(cache, ShipText.deck_label(14), &"two", Transform3D.IDENTITY, Vector2(0.92, 0.23), DisplayPerception.new(memory))
	assert_true(first.pair == second.pair, "same text shares immutable pixels")
	assert_int_equal(first.get_child_count(), 0, "no blank label surface before pair is ready")
	var ink := Image.create(2, 2, false, Image.FORMAT_RGBA8)
	ink.fill(Color.WHITE)
	cache.complete(first.pair.key, ink, ink)
	var a := first.get_node("TextSurface") as MeshInstance3D
	var b := second.get_node("TextSurface") as MeshInstance3D
	assert_true(a.material_override != b.material_override, "unique blend materials")
	for tick: int in range(168): first.perception.tick(true)
	first.present()
	second.present()
	assert_float_equal(a.material_override.get_shader_parameter("perceive"), 1, "first face resolved")
	assert_float_equal(b.material_override.get_shader_parameter("perceive"), 0, "second face native")
	first.free()
	second.free()
	cache.free()

func test_built_d14_faces_generate_labels_without_remote_or_startup_jobs() -> void:
	var parent := Node3D.new()
	var game := Game.new(0)
	var scene := ShipScene.build_into(parent, game, false)
	assert_int_equal(scene.text_cache.pending_count(), 1, "arrival console queues its inactive text")
	scene.prepare_near(Vector3(18, 0, 0))
	# The regular-door design adds five side plates and both power-door faces.
	assert_int_equal(scene.labels.size(), 11, "four hatch faces plus seven regular-door plates")
	scene.prepare_near(Vector3(28, 0, 0))
	scene.prepare_near(Vector3(8, 0, 0))
	assert_int_equal(scene.labels.size(), 33, "fourteen hatch/lift faces plus seventeen side and two power plates")
	assert_int_equal(scene.text_cache.pending_count(), 7, "six navigation pairs plus arrival console text")
	assert_int_equal(scene.text_cache.raster_viewport_count(), 0, "pure scene tests do not await GPU")
	assert_true(scene.labels[&"D14-C-001-H-FORE/FORE"].pair.native == "lometa [16]\nshelani paki [52]", "corridor face points to section forty-two")
	assert_true(scene.labels[&"D14-C-001-H-FORE/AFT"].pair.native == "lometa [16]\nshelani paki [51]", "connector face points back to forty-one")
	parent.free()

func test_complete_key_shares_pair_but_separates_style_and_text() -> void:
	var cache := ShipTextCache.new()
	var text := ShipText.deck_label(14)
	var first := cache.acquire(text, &"navigation")
	var second := cache.acquire(text, &"navigation")
	assert_true(first == second, "same complete key shares pair")
	assert_int_equal(cache.pending_count(), 1, "cache hit queues no raster work")
	assert_true(cache.acquire(text, &"console") != first, "style is part of key")
	assert_true(cache.acquire(ShipText.deck_label(30), &"navigation") != first, "text is part of key")
	assert_int_equal(cache.raster_viewport_count(), 0, "headless request does not create viewports")
	cache.free()

func test_completed_pairs_are_copied_and_unreferenced_lru_is_bounded() -> void:
	var cache := ShipTextCache.new()
	var text := ShipText.deck_label(14)
	var held := cache.acquire(text, &"navigation")
	var native := Image.create(2, 2, false, Image.FORMAT_RGBA8)
	var perceived := Image.create(2, 2, false, Image.FORMAT_RGBA8)
	native.fill(Color.RED)
	perceived.fill(Color.BLUE)
	cache.complete(held.key, native, perceived)
	native.fill(Color.GREEN)
	assert_true(held.native_texture().get_image().get_pixel(0, 0) == Color.RED, "completed native pixels do not alias raster input")
	assert_true(held.perceived_texture().get_image().get_pixel(0, 0) == Color.BLUE, "separate perceived pixels")
	for deck: int in range(1, 80):
		var pair := cache.acquire(ShipText.deck_label(deck), &"navigation")
		cache.release(pair.key)
	assert_int_equal(cache.unreferenced_count(), 32, "at most thirty-two idle pairs")
	assert_true(cache.acquire(text, &"navigation") == held, "referenced pair cannot be evicted")
	cache.release(held.key)
	cache.release(held.key)
	cache.free()
