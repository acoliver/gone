extends SimTestCase

func test_soft_goods_use_state_assets_and_exact_bed_frame_transform() -> void:
	for state: StringName in QuartersProps.STATES:
		var furnishings := QuartersFurnishings.build(state)
		assert_true(furnishings.find_children("Standin_bed_soft", "", true, false).is_empty(), "no bed soft stand-in remains")
		var soft := furnishings.get_node_or_null("Placement_bed/bed_soft") as Node3D
		assert_true(soft != null, "real soft goods in " + String(state))
		if soft != null:
			var source := "bed_soft.glb" if state == &"as_built" else "bed_soft_aged.glb"
			assert_true(soft.scene_file_path == QuartersFurnishings.ROOT + source, "state-specific imported asset")
			assert_true(soft.transform == furnishings.get_node("Placement_bed/bed").transform, "exact frame transform, without separate fitting")
			for part: String in ["Mattress", "Quilt", "Pillow_L", "Pillow_R"]:
				assert_true(soft.find_child(part, true, false) is MeshInstance3D, "imported soft part " + part)
			if state == &"aged":
				for part: String in ["FibreFoamPowder_Floor", "FibreFoamPowder_Platform", "FoamCrumbs_Floor", "FoamCrumbs_Platform"]:
					assert_true(soft.find_child(part, true, false) is MeshInstance3D, "aged debris " + part)
		furnishings.free()

func test_soft_goods_keep_imported_cloth_materials_without_steel_overrides() -> void:
	for state: StringName in QuartersProps.STATES:
		var furnishings := QuartersFurnishings.build(state)
		var soft := furnishings.get_node_or_null("Placement_bed/bed_soft")
		assert_true(soft != null, "real soft goods")
		if soft != null:
			for mesh: MeshInstance3D in soft.find_children("*", "MeshInstance3D", true, false):
				assert_true(mesh.material_override == null, "no global override on " + String(mesh.name))
				for surface: int in range(mesh.mesh.get_surface_count()):
					assert_true(mesh.get_surface_override_material(surface) == null, "no slot override")
					var material := mesh.get_active_material(surface) as StandardMaterial3D
					assert_true(material != null, "imported PBR material")
					if material != null: assert_float_equal(material.metallic, 0.0, "soft goods are not metal")
		furnishings.free()

func test_all_soft_goods_parts_clear_bedside_units_and_over_bed_lockers() -> void:
	for state: StringName in QuartersProps.STATES:
		var furnishings := QuartersFurnishings.build(state)
		var soft := furnishings.get_node_or_null("Placement_bed/bed_soft")
		assert_true(soft != null, "real soft goods")
		if soft != null:
			for part: MeshInstance3D in soft.find_children("*", "MeshInstance3D", true, false):
				var bounds := ShipScene._world_frame(part) * part.get_aabb()
				for id: String in ["bedside_l", "bedside_r", "lockers_over_bed"]:
					var furniture := furnishings.get_node("Placement_" + id)
					for other: MeshInstance3D in furniture.find_children("*", "MeshInstance3D", true, false):
						assert_false(bounds.intersects(ShipScene._world_frame(other) * other.get_aabb()), "%s %s clears %s/%s" % [state, part.name, id, other.name])
		furnishings.free()

func test_soft_goods_add_no_colliders_and_keep_shared_bed_collider() -> void:
	var room := QuartersRoom.build(Game.new(114))
	for state: Node3D in [room.remembered, room.present]:
		var soft := state.get_node_or_null("Placement_bed/bed_soft")
		assert_true(soft != null, "real soft goods")
		if soft != null:
			assert_true(soft.find_children("*", "CollisionObject3D", true, false).is_empty(), "soft goods add no physics bodies")
			assert_true(soft.find_children("*", "CollisionShape3D", true, false).is_empty(), "powder and cloth add no shapes")
	var ids := ShipCollision.new(ShipLayout.authored().layout).solid_ids(16)
	assert_int_equal(ids.count(&"D16-QUARTERS/PROP/bed"), 1, "existing shared bed collider retained")
	for id: StringName in ids: assert_false(String(id).contains("bed_soft"), "no new soft-goods solid")
	room.free()
