extends SimTestCase

func _lit(hit: Dictionary, lights: Array[OmniLight3D], mask: int) -> bool:
	for lamp: OmniLight3D in lights:
		var toward := ShipScene._world_frame(lamp).origin - Vector3(hit.position)
		if (lamp.light_cull_mask & mask) != 0 and toward.length() < lamp.omni_range and toward.dot(hit.normal) > 0: return true
	return false

func test_every_capture_pixel_hits_lit_room_shell_or_the_open_doorway() -> void:
	var game := Game.new(114)
	game.power_active = true
	var room := QuartersRoom.build(game)
	var shell := RoomGeometry.build_solids(game.layout, QuartersGeometry.shell())
	var section := ShipSection.build(game.layout, game.layout.section(QuartersLayout.SECTION))
	section.add_child(SectionPowerLighting.build(game, game.layout.section(QuartersLayout.SECTION), section))
	section.side_leaves[QuartersLayout.DOOR].position += Vector3(SlidingDoorParts.stroke(game.layout.door(QuartersLayout.DOOR)), 0, 0)
	var plan: Dictionary = QuartersInventory.plan().camera
	for view: String in ["remembered-wide", "present-wide", "doorway"]:
		var wide := view.ends_with("wide")
		var eye := QuartersLayout.to_world(Vector3(0.75, 2.2, 0.10) if wide else Vector3(plan.position[0], plan.position[1], plan.position[2]))
		var target := QuartersLayout.to_world(Vector3(4.0, 1.15, 3.6) if wide else Vector3(plan.look_at[0], plan.look_at[1], plan.look_at[2]))
		var basis := Basis.looking_at(target - eye)
		var tangent := tan(deg_to_rad(66.0 if wide else float(plan.horizontal_fov_deg) / 2))
		var faces := PackedVector3Array()
		HatchRenderFaces.collect(shell, eye, Lighting.QUARTERS_MASK, faces)
		var mesh := TriangleMesh.new()
		assert_true(mesh.create_from_faces(faces), "room-owned opaque front-facing shell")
		var state := room.present if view.begins_with("present") else room.remembered
		var lights: Array[OmniLight3D] = []
		lights.append_array(room.entrance_bounces)
		for source: Node3D in [state, section]:
			for lamp: OmniLight3D in source.find_children("*", "OmniLight3D", true, false):
				if lamp.light_energy > 0: lights.append(lamp)
		var corridor_faces := PackedVector3Array()
		var corridor_masks: Array[int] = []
		for piece: Node3D in section.get_children():
			if not piece is MeshInstance3D: continue
			if piece.get_meta(&"solid_id", &"") == &"D16-S-042/STARBOARD/002": piece.layers |= Lighting.QUARTERS_MASK
			var count := corridor_faces.size()
			HatchRenderFaces.collect(piece, eye, Lighting.architectural_mask(game.layout, QuartersLayout.SECTION), corridor_faces)
			for index: int in range(count, corridor_faces.size(), 3): corridor_masks.append(piece.layers)
		var corridor := TriangleMesh.new()
		assert_true(corridor.create_from_faces(corridor_faces), "lit corridor beyond the intentional open doorway")
		var portals := 0
		var checked := 0
		for y: int in range(864):
			for x: int in range(1536):
				var ray := basis * Vector3((2 * (x + 0.5) / 1536 - 1) * tangent, (1 - 2 * (y + 0.5) / 864) * tangent * 864 / 1536, -1)
				var hit := mesh.intersect_segment(eye, eye + ray.normalized() * 20)
				if hit.is_empty():
					# The working door is a portal, not a seventh wall. Only its
					# exact clear aperture may expose the lit corridor beyond it.
					var crossing := eye + ray * ((QuartersLayout.ENTRANCE_Z - eye.z) / ray.z)
					var passage := ray.z < 0 and crossing.x >= 44.4 and crossing.x <= 45.6 and crossing.y >= QuartersLayout.FLOOR_Y and crossing.y <= QuartersLayout.FLOOR_Y + 2.4
					assert_true(passage, "%s pixel (%d,%d) escapes outside the open doorway: %s" % [view, x, y, crossing])
					var beyond := corridor.intersect_segment(eye, eye + ray.normalized() * 100)
					assert_false(beyond.is_empty(), "the intentional doorway must not expose a void")
					if not beyond.is_empty(): assert_true(_lit(beyond, lights, corridor_masks[beyond.face_index]), "%s doorway pixel (%d,%d) exposes unlit corridor steel: %s" % [view, x, y, beyond])
					if not passage or beyond.is_empty():
						shell.free()
						room.free()
						section.free()
						return
					portals += 1
					checked += 1
					continue
				assert_true(_lit(hit, lights, Lighting.QUARTERS_MASK), "%s pixel (%d,%d) hits a surface without incident room light: %s" % [view, x, y, hit])
				checked += 1
		assert_int_equal(checked, 1327104, "all pixels, including the four frame edges")
		print("ENCLOSURE ", view, " room=", checked - portals, " doorway=", portals)
	shell.free()
	room.free()
	section.free()

func test_entrance_lining_stays_inside_room_and_leaves_the_passage_open() -> void:
	var lining := 0
	for solid: ShipGeometry.SolidSpec in QuartersGeometry.shell():
		if not String(solid.id).begins_with("D16-QUARTERS/ENTRANCE-INNER-"): continue
		lining += 1
		assert_true(solid.surface_owner == QuartersLayout.ID, "room owns entrance finish")
		assert_true(solid.surface_part == &"PORT", "entrance uses the room's architectural wall finish")
		var bounds := solid.transform * AABB(-solid.size / 2, solid.size)
		assert_float_in_range(bounds.position.z, QuartersLayout.ENTRANCE_Z - 0.000001, QuartersLayout.ENTRANCE_Z + 0.000001, "no lining on the corridor side or in the sliding pocket")
		var passage := AABB(Vector3(44.4001, -11, 1.5), Vector3(1.1998, 2.3999, 0.3))
		assert_false(bounds.intersects(passage), "approved 1.2 by 2.4 m passage stays clear")
	assert_int_equal(lining, 3, "both jamb-side spans and lintel close the sixth side")
