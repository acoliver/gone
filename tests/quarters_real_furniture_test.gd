extends SimTestCase

const REPLACED := {
	"wardrobe": "wardrobe", "bed": "bed", "desk_chair": "desk_chair",
	"dining_table": "dining_table", "dining_chair_1": "dining_chair", "dining_chair_2": "dining_chair",
	"desk": "desk", "console": "console", "bedside_l": "bedside", "bedside_r": "bedside",
	"view_screen": "view_screen", "media_cabinet": "media_cabinet", "lockers_over_bed": "lockers_over_bed",
}

func test_accepted_furniture_uses_real_assets_in_both_states() -> void:
	for state: StringName in QuartersProps.STATES:
		var furnishings := QuartersFurnishings.build(state)
		for id: String in REPLACED:
			var placement := furnishings.get_node("Placement_" + id)
			assert_false(placement.has_node("Standin_" + id), "no replaced stand-in " + id)
			var asset := placement.get_node_or_null(REPLACED[id]) as Node3D
			assert_true(asset != null, "accepted asset at " + id)
			if asset != null:
				assert_true(asset.scene_file_path == QuartersFurnishings.ROOT + REPLACED[id] + ".glb", "real imported GLB " + id)
		for item: Dictionary in QuartersInventory.small_items():
			assert_true(furnishings.has_node("Item_" + item.id), "small item retains its placement: " + item.id)
			assert_false(furnishings.has_node("Standin_" + item.id), "small stand-in replaced: " + item.id)
		assert_true(furnishings.get_node("Placement_bed/bed_soft").find_child("Mattress", true, false) is MeshInstance3D, "real mattress remains with bed")
		furnishings.free()

func test_real_furniture_matches_layout_footprints_facing_and_height() -> void:
	var furnishings := QuartersFurnishings.build(&"as_built")
	for prop: Dictionary in QuartersInventory.props():
		if not REPLACED.has(prop.id) or prop.id == "wardrobe": continue
		var asset := furnishings.get_node_or_null("Placement_%s/%s" % [prop.id, REPLACED[prop.id]]) as Node3D
		if asset == null:
			assert_true(false, "missing real " + prop.id)
			continue
		var expected := QuartersInventory.world_bounds(QuartersInventory.prop_bounds(prop))
		if prop.id == "bed": expected.size.y = 1.1
		if prop.id == "console":
			var worktop := furnishings.get_node("Placement_desk/desk").find_child("Worktop", true, false) as MeshInstance3D
			expected.position.y = (ShipScene._world_frame(worktop) * worktop.get_aabb()).end.y
		var actual := QuartersFurnishings._bounds(asset)
		assert_close(actual.position, expected.position, "asset minimum " + prop.id)
		assert_close(actual.size, expected.size, "asset envelope " + prop.id)
		assert_close(asset.basis.z.normalized(), Basis(Vector3.UP, QuartersFurnishings._yaw(prop.get("faces", "+z"))).z, "asset facing " + prop.id)
	furnishings.free()

func test_tunic_and_fibres_fit_real_wardrobe_interior_and_rail() -> void:
	for state: StringName in QuartersProps.STATES:
		var furnishings := QuartersFurnishings.build(state)
		var placement := furnishings.get_node("Placement_wardrobe")
		var wardrobe := placement.get_node_or_null("wardrobe") as Node3D
		assert_true(wardrobe != null, "real wardrobe")
		if wardrobe == null:
			furnishings.free()
			continue
		var panels := {}
		for part: String in ["BottomPanel", "TopPanel", "SidePanel_L", "SidePanel_R", "BackPanel", "Rail"]:
			var node := wardrobe.find_child(part, true, false) as MeshInstance3D
			panels[part] = (wardrobe.transform.affine_inverse() * ShipScene._world_frame(node)) * node.get_aabb()
		var interior := AABB(Vector3(panels.SidePanel_R.end.x, panels.BottomPanel.end.y, panels.BackPanel.end.z), Vector3.ZERO)
		interior.size = Vector3(panels.SidePanel_L.position.x, panels.TopPanel.position.y, 0.325) - interior.position
		for garment_name: String in ["HangingUniform", "UniformFragments"]:
			var garment := placement.get_node(garment_name) as Node3D
			var bounds := QuartersFurnishings._bounds(garment, wardrobe.transform.affine_inverse(), true)
			if not bounds.has_volume(): continue
			assert_true(interior.grow(0.001).encloses(bounds), "%s %s fits actual panel interior: %s inside %s" % [state, garment_name, bounds, interior])
			if garment_name == "HangingUniform":
				assert_float_in_range(bounds.end.y, panels.Rail.get_center().y - 0.025, panels.Rail.end.y + 0.025, "hook reaches rail")
		var hinge: Node3D = wardrobe.find_child("Door", true, false)
		var room_hinge := QuartersLayout.from_world((ShipScene._world_frame(hinge)).origin)
		assert_close(room_hinge, Vector3(7.335, 0.12, 4.1), "specified wardrobe handedness and hinge")
		furnishings.free()

func test_real_dining_chairs_clear_table_and_each_other() -> void:
	for state: StringName in QuartersProps.STATES:
		var furnishings := QuartersFurnishings.build(state)
		var table := furnishings.get_node_or_null("Placement_dining_table/dining_table") as Node3D
		assert_true(table != null, "real table")
		if table != null:
			var table_bounds := QuartersFurnishings._bounds(table)
			var chairs: Array[AABB] = []
			for index: int in [1, 2]:
				var chair := furnishings.get_node_or_null("Placement_dining_chair_%d/dining_chair" % index) as Node3D
				assert_true(chair != null, "real chair")
				if chair == null: continue
				var bounds := QuartersFurnishings._bounds(chair)
				assert_false(bounds.intersects(table_bounds), "chair %d does not intersect table" % index)
				chairs.append(bounds)
			if chairs.size() == 2: assert_false(chairs[0].intersects(chairs[1]), "chairs do not intersect each other")
		furnishings.free()

func test_interim_slot_materials_are_shared_and_state_specific() -> void:
	for slot: StringName in [&"PaintedSteel", &"BareSteel", &"DarkSteel", &"Fabric", &"Wood", &"Display", &"Glass"]:
		var clean := QuartersProps.interim_material(slot, &"as_built")
		var aged := QuartersProps.interim_material(slot, &"aged")
		assert_true(clean == QuartersProps.interim_material(slot, &"as_built"), "clean slot cached")
		assert_true(aged == QuartersProps.interim_material(slot, &"aged"), "aged slot cached")
		assert_true(clean != aged, "finish states do not alias")
		if slot in [&"PaintedSteel", &"BareSteel", &"DarkSteel"]:
			assert_true(aged is ShaderMaterial and aged.shader == Surfaces.STEEL, "unbaked ship steel shader")
			assert_false(aged.get_shader_parameter(&"baked_hatch") == true, "no prop bake")
	for state: StringName in QuartersProps.STATES:
		var furnishings := QuartersFurnishings.build(state)
		for id: String in REPLACED:
			var prop := StringName(REPLACED[id])
			var asset := furnishings.get_node("Placement_%s/%s" % [id, prop])
			for mesh: MeshInstance3D in asset.find_children("*", "MeshInstance3D", true, false):
				for surface: int in range(mesh.mesh.get_surface_count()):
					var slot := StringName(mesh.mesh.surface_get_material(surface).resource_name)
					var expected: Material = QuartersProps.material(prop, state)
					if prop == &"bedside" and mesh.name == &"LampLens":
						expected = QuartersProps.bedside_lens(state)
					elif slot in [&"Display", &"Glass"]:
						expected = QuartersProps.interim_material(slot, state)
					assert_true(mesh.get_active_material(surface) == expected, "routed slot assignment %s/%s/%s" % [state, id, slot])
		furnishings.free()

func test_soft_bed_parts_rest_on_real_platform() -> void:
	var furnishings := QuartersFurnishings.build(&"as_built")
	var bed := furnishings.get_node_or_null("Placement_bed/bed") as Node3D
	assert_true(bed != null, "real bed")
	if bed != null:
		var soft := furnishings.get_node("Placement_bed/bed_soft") as Node3D
		# Measure the millimetre gap near zero, without ship-coordinate cancellation.
		bed.position = Vector3.ZERO
		soft.position = Vector3.ZERO
		var platform := bed.find_child("MattressPlatform", true, false) as MeshInstance3D
		var top := (ShipScene._world_frame(platform) * platform.get_aabb()).end.y
		var mattress := soft.find_child("Mattress", true, false) as MeshInstance3D
		assert_float_in_range((ShipScene._world_frame(mattress) * mattress.get_aabb()).position.y - top, 0, 0.001, "mattress contacts platform")
		for name: String in ["Quilt", "Pillow_L", "Pillow_R"]:
			assert_true(soft.find_child(name, true, false) is MeshInstance3D, "real soft part " + name)
	furnishings.free()
