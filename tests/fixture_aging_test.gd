extends SimTestCase

func test_hatch_cage_lods_keep_each_fitting_surface_and_bounds() -> void:
	var spec := ShipLayout.authored().layout.door(&"D14-C-001-H-FORE")
	var services := HatchServices.build(spec, 0, 1)
	var steel: MeshInstance3D = services.get_node("Lamp/Steel")
	var bounds: Array[AABB] = steel.mesh.get_meta(&"service_bounds")
	assert_int_equal(steel.mesh.get_surface_count(), bounds.size(), "each hatch fitting retains its swept-bound surface")
	var lods := 0
	for index: int in range(steel.mesh.get_surface_count()):
		var surface := RenderingServer.mesh_get_surface(steel.mesh.get_rid(), index)
		if surface.has("lods"): lods += surface.lods.size()
	assert_true(lods > 0, "hatch cages simplify their rounded fittings at distance too")
	services.free()

func test_cage_glass_keeps_close_detail_with_distance_lods() -> void:
	var layout := ShipLayout.authored().layout
	var fixture := Lighting.steady_fixture(Vector3(0, 2.65, 0), 1, 3, Surfaces.surface_frame(layout, &"D14-S-041", &"CEILING"))
	var glass: MeshInstance3D = fixture.get_node("Lens")
	var surface := RenderingServer.mesh_get_surface(glass.mesh.get_rid(), 0)
	assert_true(surface.has("lods") and not surface.lods.is_empty(), "rounded glass retains its close-up surface and simplifies at distance")
	fixture.free()

func test_cage_glass_maps_weathering_across_its_aperture() -> void:
	var layout := ShipLayout.authored().layout
	var fixture := Lighting.steady_fixture(Vector3(0, 2.65, 0), 1, 3, Surfaces.surface_frame(layout, &"D14-S-041", &"CEILING"))
	var glass: MeshInstance3D = fixture.get_node("Lens")
	var uv: Variant = glass.mesh.surface_get_arrays(0)[Mesh.ARRAY_TEX_UV]
	assert_true(uv is PackedVector2Array and not uv.is_empty(), "dirty glass needs aperture UVs rather than one constant texture sample")
	if uv is PackedVector2Array and not uv.is_empty():
		var bounds := Rect2(uv[0], Vector2.ZERO)
		for point: Vector2 in uv: bounds = bounds.expand(point)
		assert_close(Vector3(bounds.position.x, bounds.position.y, 0), Vector3.ZERO, "glass UVs start at the seal")
		assert_close(Vector3(bounds.end.x, bounds.end.y, 0), Vector3(1, 1, 0), "glass UVs cover the whole aperture")
	fixture.free()

func test_regular_glass_has_a_translucent_aperture_and_grimy_rim() -> void:
	var light := Lighting.regular_end_fill(Vector3.ZERO, 1.0)
	var material := light.lens_material
	assert_true(material.albedo_texture != material.emission_texture, "white diffuser transmission is separate from opaque surface grime")
	var image := material.emission_texture.get_image()
	var minimum := 1.0
	var maximum := 0.0
	for y: int in range(image.get_height()):
		for x: int in range(image.get_width()):
			var value := image.get_pixel(x, y).r
			minimum = minf(minimum, value)
			maximum = maxf(maximum, value)
	assert_true(minimum > 0.0 and minimum < 0.10 and maximum > 0.90 and maximum < 1.0, "rim deposits interrupt the glow while the aperture stays translucent")
	assert_true(image.get_pixel(128, 64).r >= 0.80 and image.get_pixel(128, 0).r < 0.10, "grime accumulates at the glass seal instead of obscuring the white aperture")
	assert_true(material.emission == Lighting.REGULAR_WHITE * Lighting.REGULAR_EMISSIVE, "diffuser treatment preserves the circuit emission colour and level")
	light.free()

func test_cage_noise_is_a_shared_baked_volume() -> void:
	var first := FixtureEmitter.steel_material()
	var second := FixtureEmitter.steel_material()
	assert_true(first == second, "fixtures share the same weathering material")
	var texture: Texture3D = first.get_shader_parameter("grime_noise")
	assert_true(texture != null, "weathering uses baked noise instead of fragment hash calculations")
	if texture != null:
		assert_int_equal(texture.get_width(), 64, "the metre-scale noise volume has a fixed size")
		assert_int_equal(texture.get_height(), 64, "the volume covers all fixture axes")
		assert_int_equal(texture.get_depth(), 64, "grain does not collapse to flat projection")

func test_cage_backing_is_a_narrow_mount_rather_than_a_box() -> void:
	var layout := ShipLayout.authored().layout
	var group := Node3D.new()
	var service := ShipLayout.HatchServiceSpec.new(&"Lamp", Transform3D.IDENTITY)
	HatchServices._lamp(group, service, 1, Surfaces.surface_frame(layout, &"D14-S-041", &"CEILING"))
	var backing := group.get_child(0) as MeshInstance3D
	assert_true(backing.mesh.get_aabb().size.x <= Vector3(0.075, 0, 0).x, "narrow mounting neck leaves the rounded cage silhouette exposed")
	assert_true(backing.mesh.get_aabb().size.y <= Vector3(0, 0.09, 0).y, "backing no longer fills the cage outline")
	group.free()

func test_spark_gate_rejects_displaced_or_hidden_active_arcs() -> void:
	var hazards := Hazards.build()
	hazards.auto_bursts = false
	var inventory := preload("res://tools/light_inventory.gd").new()
	var light := hazards._spark_lights[0]
	assert_true(inventory._fixture_error(light).is_empty(), "idle spark is at its real emitter")
	light.position.x = 0.02
	assert_false(inventory._fixture_error(light).is_empty(), "displaced spark cannot pass co-location")
	light.position.x = 0.0
	hazards.fire_burst()
	assert_true(inventory._fixture_error(light).is_empty(), "active arc and light follow the same flash")
	var arc: MeshInstance3D = light.get_meta(&"spark_emitter")
	arc.hide()
	assert_false(inventory._fixture_error(light).is_empty(), "an active source requires a visible arc")
	hazards.free()

func test_shared_cage_has_local_weathering_and_dirty_emissive_glass() -> void:
	var layout := ShipLayout.authored().layout
	var fixture := Lighting.steady_fixture(Vector3(0, 2.65, 0), 1, 3, Surfaces.surface_frame(layout, &"D14-S-041", &"CEILING"))
	var steel: MeshInstance3D = fixture.get_node("Steel")
	var glass: MeshInstance3D = fixture.get_node("Lens")
	assert_true(steel.material_override.shader.resource_path.ends_with("fixture_steel.gdshader"), "cage weathering uses the fixture's metre-scale geometry")
	assert_true(steel.material_override.get_shader_parameter("weathering_enabled"), "production weathering is enabled")
	assert_int_equal(HatchRenderFaces._opaque_cull_mode(steel.material_override), BaseMaterial3D.CULL_BACK, "weathered cage remains opaque back-face-culled steel in seal probes")
	var material := glass.material_override as StandardMaterial3D
	assert_true(material.albedo_texture != null and material.emission_texture != null, "grime interrupts both glass reflection and glow")
	assert_true(material.roughness_texture != null, "dust roughens the glass")
	fixture.free()

func test_wall_cage_retains_its_hatch_bracket_without_a_ceiling_stem() -> void:
	var game := Game.new(91)
	var hall := Hallway.build(game)
	var light: OmniLight3D = hall.get_node("EmergencyFill0")
	var steel: MeshInstance3D = light.get_node("Steel")
	assert_false(light.has_node("CeilingMount"), "wall cage has no ceiling drop")
	assert_false(steel.has_meta(&"mount_bounds"), "native hatch bracket needs no added stem")
	var box := Surfaces.world_frame(steel) * steel.mesh.get_aabb()
	assert_true(box.end.z >= 1.5 and box.position.z >= 1.1, "bracket meets starboard wall and cage stays at its edge")
	hall.free()

func test_spark_source_is_at_the_visible_arc_without_a_lamp_cage() -> void:
	var hazards := Hazards.build()
	hazards.auto_bursts = false
	for light: OmniLight3D in hazards._spark_lights:
		assert_false(light.get_parent().has_node("Steel"), "shorting wiring has no caged lamp")
		var arc: MeshInstance3D = light.get_meta(&"spark_emitter")
		assert_close(Surfaces.world_frame(light).origin, Surfaces.world_frame(arc).origin, "light is at the arc point")
		assert_false(arc.visible, "idle arc is dark")
	hazards.fire_burst()
	var light := hazards._spark_lights[0]
	var arc: MeshInstance3D = light.get_meta(&"spark_emitter")
	assert_true(arc.visible, "the source is visible during the flash")
	assert_true(arc.material_override.emission == Hazards.SPARK_LIGHT_COLOR * light.light_energy, "arc follows the same strobe")
	hazards._physics_process(Hazards.SPARK_FLASH_SECS)
	assert_false(arc.visible, "arc extinguishes with the flash")
	assert_float_equal(light.light_energy, 0, "light extinguishes with the arc")
	hazards.free()

func test_all_nineteen_relocated_cages_have_no_exposed_ceiling_conduit() -> void:
	var checked := 0
	for room: Node3D in [Lighting.build(Game.new(91)), Hallway.build(Game.new(91)), PowerRoom.build(Game.new(91))]:
		for light: OmniLight3D in room.find_children("EmergencyFill*", "OmniLight3D", true, false):
			if light.name == "EmergencyFillEnd": continue
			checked += 1
			var steel: MeshInstance3D = light.get_node("Steel")
			var box := Surfaces.world_frame(steel) * steel.mesh.get_aabb()
			assert_true(box.size.y < 0.32, "only the hatch cage, no suspended conduit")
			assert_true(box.end.y < 2.7, "cage is below the pipe and duct band")
			assert_false(steel.has_meta(&"mount_bounds"), "cage uses its own wall bracket")
		room.free()
	assert_int_equal(checked, 19, "six bay, seven hall and six power-room lamps")
