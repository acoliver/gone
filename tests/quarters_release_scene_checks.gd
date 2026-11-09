extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	var check := SimTestCase.new()
	var game := Game.new(114)
	var scene := ShipScene.new()
	var owner := Node3D.new()
	root.add_child(owner)
	scene._parent = owner
	scene._game = game
	scene.text_cache = ShipTextCache.new()
	scene.text_cache.pair_ready.connect(scene._labels_ready)
	owner.add_child(scene.text_cache)
	scene._add_hatch(&"D16-C-001-H-AFT")
	scene.ensure_d16()
	var release: Node3D = scene.d16_section.get_node("ManualRelease")
	check.assert_true((scene.d16_section.get_node("D16-S-042_STARBOARD_002").layers & Lighting.QUARTERS_MASK) != 0, "lintel underside receives the local threshold bounce")
	check.assert_true((release.get_node("PullGrip").layers & Lighting.QUARTERS_MASK) != 0, "grip receives the local threshold bounce")
	check.assert_int_equal(scene.d16_section.get_node("D16-S-042_STARBOARD_000").layers & Lighting.QUARTERS_MASK, 0, "other corridor walls do not receive the local threshold bounce")
	var trims := 0
	for piece: MeshInstance3D in scene.d16_section.find_children("*", "MeshInstance3D", true, false):
		if release.is_ancestor_of(piece) or not piece.has_meta(&"surface_frame"): continue
		var surface: Surfaces.SurfaceFrame = piece.get_meta(&"surface_frame")
		if surface.key != StringName("%s/FRAME" % QuartersLayout.DOOR): continue
		trims += 1
		check.assert_true((piece.layers & Lighting.QUARTERS_MASK) != 0, "all six doorway trims, including the head underside, receive the local bounce")
	check.assert_int_equal(trims, 6, "both sides retain their three authored trim pieces")
	for part: String in ["Recess", "FrameHead", "FrameFoot", "FrameLeft", "FrameRight", "PullGrip", "HandleLeft", "HandleRight"]:
		check.assert_true(release.has_node(part), "readable recessed handle component: " + part)
	var grip: MeshInstance3D = release.get_node("PullGrip")
	check.assert_true(grip.mesh is CylinderMesh, "rounded grip silhouette distinguishes it from a plain block")
	check.assert_true(grip.material_override == HatchModel.material(HatchModel.DOOR_SHADE), "grip uses the existing brighter hardware material")
	check.assert_true(grip.position.z > release.get_node("Recess").position.z + 0.03, "grip stands clear of dark recess")
	check.assert_true(scene.labels.has(QuartersLayout.RELEASE), "release participates in existing label system")
	var label: ShipLabel = scene.labels[QuartersLayout.RELEASE]
	var ink := Image.create(64, 64, false, Image.FORMAT_RGBA8)
	ink.fill(Color.WHITE)
	scene.text_cache.complete(label.pair.key, ink, ink)
	check.assert_true(label.pair.ready() and label._quad != null, "release label attaches when the shared raster completes")
	check.assert_true(label._material.get_shader_parameter("ink_albedo") == ShipTextCanvas.STATE_COLOR, "release supplies visible unshaded albedo, not emission alone")
	var eye := release.global_position + Vector3(0, 0.1, -1)
	var aim := (label.global_position - eye).normalized()
	for tick: int in range(180): scene.tick_attention(eye, aim, 16)
	check.assert_true(label.perception.perceive > 0, "release label is visible and perceived when looked at like other labels")
	owner.free()
	if not check.failure.is_empty():
		printerr(check.failure)
		quit(1)
		return
	print("QUARTERS RELEASE PASS")
	quit(0)
