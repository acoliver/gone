extends SimTestCase

func test_section_bounds_and_power_portal_drive_the_shared_shell() -> void:
	var original := ShipLayout.authored().layout
	var records := original.records()
	var section := original.section(&"D14-S-041")
	var bounds := section.bounds()
	bounds.position.x -= 1
	bounds.size.x += 1
	records[records.find(section)] = ShipLayout.SectionSpec.new(section.id(), 14, section.number(), bounds, section.opening_ids(), section.side_door_ids(), section.circuit(), section.is_built())
	var door := original.door(ShipLayout.POWER_DOOR_ID)
	var frame := door.frame()
	frame.origin.x -= 1
	records[records.find(door)] = ShipLayout.DoorSpec.new(door.id(), 14, door.kind(), door.policy(), frame, door.aperture(), door.spaces(), door.face_ids(), door.owner_id(), door.animation(), door.has_wheel())
	var result := ShipLayout.try_new(records)
	assert_true(result.is_ok(), "changed section and portal are valid")
	if not result.is_ok():
		return
	var solids := ShipGeometry.hallway_solids(result.layout)
	assert_vec3_equal(solids[0].center, Vector3(17.6, -0.1, 0), "floor follows section bounds")
	assert_vec3_equal(solids[0].size, Vector3(25.2, 0.2, 3.4), "floor preserves the shared wall band")
	assert_float_equal(solids[2].center.x - solids[2].size.x / 2, 5, "port wall starts at the section bound")
	assert_float_equal(solids[4].center.x, 26, "port lintel follows the power DoorSpec")
	assert_float_equal(solids[5].center.x - solids[5].size.x / 2, 5, "starboard wall starts at the section bound")

func test_moved_side_door_frame_moves_mesh_collider_and_interaction_together() -> void:
	var original := ShipLayout.authored().layout
	var id: StringName = &"D14-S-041-SIDE-003-PORT"
	var spec := original.door(id)
	var records := original.records()
	var frame := spec.frame()
	frame.origin.x += 1.0
	records[records.find(spec)] = ShipLayout.DoorSpec.new(id, 14, spec.kind(), spec.policy(), frame, spec.aperture(), spec.spaces(), spec.face_ids(), spec.owner_id(), spec.animation(), spec.has_wheel())
	# Reorder the ids as well: identity must not depend on the leaf array order.
	var section := original.section(&"D14-S-041")
	var ids := section.side_door_ids()
	ids.reverse()
	records[records.find(section)] = ShipLayout.SectionSpec.new(section.id(), 14, section.number(), section.bounds(), section.opening_ids(), ids, section.circuit(), section.is_built())
	var result := ShipLayout.try_new(records)
	assert_true(result.is_ok(), "shifted door is a valid authored layout")
	if not result.is_ok():
		return
	var game := Game.new(0)
	game.layout = result.layout
	var before := Hallway.build(Game.new(0))
	var after := Hallway.build(game)
	var old_leaf: MeshInstance3D = before.side_leaves[id]
	var new_leaf: MeshInstance3D = after.side_leaves[id]
	assert_vec3_equal(new_leaf.position - old_leaf.position, Vector3.RIGHT, "rendered leaf follows the changed frame by id")
	var old_solids := ShipGeometry.opening_hall_solids(original.bay().template(), true, original)
	var new_solids := ShipGeometry.opening_hall_solids(original.bay().template(), true, result.layout)
	var old_box := ShipGeometry.box_aabb(old_solids[-5])
	var new_box := ShipGeometry.box_aabb(new_solids[-5])
	assert_vec3_equal(new_box.center() - old_box.center(), Vector3.RIGHT, "ordered collider follows the same door frame")
	assert_vec3_equal(new_box.center(), new_leaf.position, "mesh and collider coincide")
	assert_vec3_equal(new_box.half_extents(), old_box.half_extents(), "move preserves collider dimensions")
	var colliders := ShipCollision.opening_set(result.layout.bay().template(), true, true, result.layout)
	var leaf_index := 0
	for solid: ShipGeometry.SolidSpec in new_solids.slice(0, new_solids.size() - 5):
		leaf_index += ShipGeometry.collision_boxes(solid).size()
	assert_true(colliders.boxes()[leaf_index].equals(new_box), "live collision set consumes the moved leaf after the subdivided frame")
	var old_targets := Interactions.new(original)
	var new_targets := Interactions.new(result.layout)
	for target: Interactions.Target in new_targets._targets:
		if target.id != spec.face_ids()[0]:
			continue
		for old: Interactions.Target in old_targets._targets:
			if old.id == target.id:
				assert_vec3_equal(target.frame.origin - old.frame.origin, Vector3.RIGHT, "interaction follows the changed frame")
		assert_float_equal(target.center.x, new_leaf.position.x, "interaction and mesh share the station")
	before.free()
	after.free()
