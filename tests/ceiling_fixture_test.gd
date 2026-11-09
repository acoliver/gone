extends SimTestCase

const ASSET := "res://assets/props/ceiling/fixture.glb"

func test_runtime_glass_preserves_texture_variation_without_a_second_warm_tint() -> void:
	var material := CeilingFixture.glass_material(1.0)
	var image := material.emission_texture.get_image()
	assert_true(image.has_mipmaps(), "retain the authored distant filtering")
	var minimum := 1.0
	var maximum := 0.0
	for y: int in range(0, image.get_height(), 16):
		for x: int in range(0, image.get_width(), 16):
			var pixel := image.get_pixel(x, y)
			assert_int_equal(roundi(pixel.r * 255), roundi(pixel.g * 255 * Lighting.REGULAR_WHITE.g / Lighting.REGULAR_WHITE.r), "balance the circuit's red/green bias in the intensity map")
			assert_float_equal(pixel.g, pixel.b, "the emission map contributes intensity, not another warm tint")
			minimum = minf(minimum, pixel.r)
			maximum = maxf(maximum, pixel.r)
	assert_true(maximum - minimum > 0.1, "keep the authored dirt and failing-section intensity variation")

func test_every_built_spine_fixture_keeps_its_light_at_the_visible_lens() -> void:
	var game := Game.new(91)
	var checked := 0
	for space: ShipLayout.Spec in game.layout.records():
		if not (space is ShipLayout.SectionSpec or space is ShipLayout.ConnectorSpec) or not space.is_built(): continue
		var node: Node3D = Hallway.build(game) if space.id() == &"D14-S-041" else (ShipSection.build(game.layout, space) if space is ShipLayout.SectionSpec else ShipConnector.build(game.layout, space))
		var lights := node.find_children("*", "OmniLight3D", true, false)
		var fixtures := 0
		for light: OmniLight3D in lights:
			if light.light_color != Lighting.EMERGENCY_RED: continue
			var lens: MeshInstance3D = light.get_parent().get_node("Lens")
			var light_position := Surfaces.world_frame(light).origin
			var lens_position := Surfaces.world_frame(lens) * lens.mesh.get_aabb().get_center()
			var separation := light_position.distance_to(lens_position)
			assert_true(separation <= 0.01, "%s %s light is within 1 cm of its visible lens: %.5f m" % [space.id(), light.get_parent().name, separation])
			fixtures += 1
		assert_int_equal(fixtures, space.emergency_fixture_frames().size(), "every authored emergency fixture is checked: %s" % space.id())
		checked += fixtures
		node.free()
	assert_int_equal(checked, 204, "all section fixtures and connector fixtures, including remote decks and landing keys")

func test_spine_fixture_housings_and_mounts_clear_every_service() -> void:
	var game := Game.new(91)
	for space: ShipLayout.Spec in game.layout.records():
		if not (space is ShipLayout.SectionSpec or space is ShipLayout.ConnectorSpec) or not space.is_built(): continue
		var services := game.layout.ceiling_services(space.id())
		var node: Node3D = Hallway.build(game) if space.id() == &"D14-S-041" else (ShipSection.build(game.layout, space) if space is ShipLayout.SectionSpec else ShipConnector.build(game.layout, space))
		for mesh: MeshInstance3D in node.find_children("*", "MeshInstance3D", true, false):
			var combined_mount := mesh.has_meta(&"mount_bounds")
			if not combined_mount and mesh.name != "CeilingMount" and mesh.get_meta(&"lamp_circuit", "") == "" and mesh.get_parent().name != "CeilingFixture": continue
			var box := Surfaces.world_frame(mesh.get_parent()) * (mesh.get_meta(&"mount_bounds") as AABB) if combined_mount else Surfaces.world_frame(mesh) * mesh.mesh.get_aabb()
			for obstacle: ShipLayout.DressingClearance in services.reservations():
				assert_false(box.intersects(obstacle.bounds), "%s %s clears %s: %s versus %s" % [space.id(), mesh.name, obstacle.id, box, obstacle.bounds])
		node.free()

func test_generated_fixture_keeps_metric_bounds_budget_and_separate_glass() -> void:
	assert_true(ResourceLoader.exists(ASSET), "selected round-6 fixture must be installed")
	if not ResourceLoader.exists(ASSET): return
	var node: Node3D = load(ASSET).instantiate()
	var bounds := _bounds(node)
	assert_close(bounds.position, Vector3(-0.55, -0.10, -0.11), "exported mounting envelope minimum")
	assert_close(bounds.end, Vector3(0.55, 0, 0.11), "exported mounting plane is Y=0")
	var triangles := 0
	var glass_count := 0
	for piece: MeshInstance3D in node.find_children("*", "MeshInstance3D", true, false):
		triangles += piece.mesh.get_faces().size() / 3
		assert_true(piece.material_override == null, "authored metal finish is not replaced")
		for surface: int in range(piece.mesh.get_surface_count()):
			var material := piece.mesh.surface_get_material(surface) as StandardMaterial3D
			if material.resource_name == "RecessedFrostedGlass":
				glass_count += 1
				assert_true(material.emission_enabled and material.emission_texture != null, "authored glass retains its emission texture")
	assert_int_equal(triangles, 2664, "selected round-6 topology")
	assert_true(triangles <= 3000, "fixture triangle budget")
	assert_int_equal(glass_count, 1, "one independent glass surface")
	assert_true(node.find_children("*", "CollisionObject3D", true, false).is_empty(), "visual prop adds no colliders")
	node.free()

func test_all_sixteen_fixtures_keep_their_sources_in_glass_and_mount_to_the_ceiling() -> void:
	var game := Game.new(91)
	var nodes: Array[Node3D] = [Lighting.build(game), Hallway.build(game), PowerRoom.build(game)]
	for index: int in range(nodes.size()):
		var node := nodes[index]
		var fixtures := node.find_children("CeilingFixture", "Node3D", true, false)
		assert_int_equal(fixtures.size(), 4 if index == 1 else 6, "one complete beam replaces each pair")
		for fixture: Node3D in fixtures:
			var bounds := _bounds(fixture)
			assert_float_equal(bounds.end.y, Vector3(0, 3.2, 0).y, "beam mounting plane is flush with the actual ceiling")
			assert_false(fixture.get_parent().has_node("CeilingMount"), "no ceiling drop under a flush beam")
			var light := fixture.get_parent().get_child(0) as OmniLight3D
			var glasses := _glasses(fixture)
			assert_int_equal(glasses.size(), 1, "one imported emitter remains behind the grille")
			var glass := glasses[0]
			assert_close(Surfaces.world_frame(glass) * glass.mesh.get_aabb().get_center(), Surfaces.world_frame(light).origin, "source is seated in recessed glass")
			assert_true(fixture.find_children("*", "CollisionObject3D", true, false).is_empty(), "fixture adds zero prop colliders")
		node.free()

func test_imported_glass_tracks_each_room_circuit_without_material_churn() -> void:
	var game := Game.new(91)
	game.light_hallway()
	var nodes: Array[Node3D] = [Lighting.build(game), Hallway.build(game), PowerRoom.build(game)]
	var materials: Array[StandardMaterial3D] = []
	for node: Node3D in nodes:
		var glasses := _glasses(node)
		assert_int_equal(glasses.size(), 4 if node is Hallway else 6, "each beam owns its imported recessed glass")
		for glass: MeshInstance3D in glasses:
			var material := glass.get_active_material(0) as StandardMaterial3D
			assert_true(material.emission == Lighting.REGULAR_WHITE * 0.0, "emergency leaves white glass dark")
			materials.append(material)
	game.press_console()
	game.press_console()
	for tick: int in range(Lighting.FIXTURE_SETTLE_TICKS):
		for node: Node3D in nodes:
			node.process_frame(Sim.LOGICAL_TICK_SECS)
			for glass: MeshInstance3D in _glasses(node):
				var material := glass.get_active_material(0) as StandardMaterial3D
				assert_true(materials.has(material), "fade reuses the circuit material")
				assert_true(material.emission == Lighting.REGULAR_WHITE * Lighting.REGULAR_EMISSIVE * node.white_level(), "actual imported glass follows the same fade as the light")
				assert_float_equal(material.emission_energy_multiplier, Vector3(0.30, 0, 0).x, "circuit control preserves the production glass response")
				assert_int_equal(material.emission_operator, BaseMaterial3D.EMISSION_OP_MULTIPLY, "zero circuit level extinguishes the textured emission")
	for node: Node3D in nodes:
		assert_float_equal(node.white_level(), 1.0, "regular circuit settles lit")
	game.power_active = false
	for tick: int in range(Lighting.FIXTURE_SETTLE_TICKS):
		for node: Node3D in nodes:
			node.process_frame(Sim.LOGICAL_TICK_SECS)
			for glass: MeshInstance3D in _glasses(node):
				var material := glass.get_active_material(0) as StandardMaterial3D
				assert_true(material.emission == Lighting.REGULAR_WHITE * Lighting.REGULAR_EMISSIVE * node.white_level(), "return to emergency fades actual glass off")
	for node: Node3D in nodes:
		assert_float_equal(node.white_level(), 0.0, "emergency leaves no white emission")
		node.free()

func _glasses(node: Node3D) -> Array[MeshInstance3D]:
	var result: Array[MeshInstance3D] = []
	for piece: MeshInstance3D in node.find_children("*", "MeshInstance3D", true, false):
		if piece.get_meta(&"lamp_circuit", "") == "white" and piece.get_active_material(0).resource_name == "RecessedFrostedGlass": result.append(piece)
	return result

func _bounds(node: Node3D) -> AABB:
	var bounds := AABB()
	var first := true
	for piece: MeshInstance3D in node.find_children("*", "MeshInstance3D", true, false):
		var box := Surfaces.world_frame(piece) * piece.mesh.get_aabb()
		bounds = box if first else bounds.merge(box)
		first = false
	return bounds
