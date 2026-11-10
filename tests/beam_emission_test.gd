extends SimTestCase

const Inventory := preload("res://tools/light_inventory.gd")
const Rays := preload("res://harness/lamp_samples.gd")

func test_every_beam_is_seated_at_glass_and_emits_only_downward() -> void:
	var game := Game.new(91)
	var count := 0
	for room: Node3D in [Lighting.build(game), Hallway.build(game), PowerRoom.build(game)]:
		for source: Light3D in room.white_lights():
			count += 1
			assert_true(source is SpotLight3D, "recessed beam needs a downward hemisphere, not an omni")
			if not source is SpotLight3D: continue
			var lens: MeshInstance3D = source.get_meta(&"fixture_emitter")
			var center := Surfaces.world_frame(lens) * lens.mesh.get_aabb().get_center()
			assert_true(Surfaces.world_frame(source).origin.distance_to(center) <= 0.01, "source remains within 1 cm of glass")
			assert_close(-Surfaces.world_frame(source).basis.z, Vector3.DOWN, "beam axis points down in world space")
			assert_float_equal(source.spot_angle, 90.0, "hemisphere includes the full aperture's lower half-space")
			assert_float_equal(source.spot_angle_attenuation, 0.0, "no artificial angular falloff below the aperture")
			assert_float_equal(source.spot_range, Lighting.REGULAR_RANGE, "unchanged source range")
			assert_float_equal(source.spot_attenuation, 1.0, "unchanged distance falloff")
			assert_false(source.shadow_enabled, "unchanged shadow policy")
		room.free()
	assert_int_equal(count, 16, "all three rooms' beams")

func test_spot_illuminance_clips_at_the_aperture_plane_and_preserves_lower_hemisphere() -> void:
	var probe := Inventory.new()
	var spot := SpotLight3D.new()
	spot.position = Vector3(0, 2, 0)
	spot.rotation.x = -PI / 2
	spot.spot_angle = 90
	spot.spot_angle_attenuation = 0
	spot.light_cull_mask = 1
	spot.spot_range = 4
	spot.spot_attenuation = 2
	var omni := OmniLight3D.new()
	omni.position = spot.position
	omni.omni_range = spot.spot_range
	omni.omni_attenuation = spot.spot_attenuation
	for point: Vector3 in [Vector3.ZERO, Vector3(2, 1, 0), Vector3(1, 1.99, 0)]:
		assert_float_equal(probe.incident(spot, point, Vector3.UP, 1), probe.incident(omni, point, Vector3.UP, 1), "flat lower hemisphere keeps the original radial profile")
	assert_float_equal(probe.incident(spot, Vector3(0, 3, 0), Vector3.DOWN, 1), 0.0, "no illumination above the glass")
	assert_float_equal(probe.incident(spot, Vector3(1, 2, 0), Vector3.LEFT, 1), 0.0, "glass plane is the cone boundary")
	assert_float_equal(probe.incident(spot, Vector3(0, -2, 0), Vector3.UP, 1), 0.0, "range cutoff")
	assert_float_equal(probe.incident(spot, Vector3.ZERO, Vector3.UP, 2), 0.0, "receiver mask")
	spot.spot_angle = 45
	assert_float_equal(probe.incident(spot, Vector3(2, 1, 0), Vector3.UP, 1), 0.0, "narrower spots also respect their cone")
	spot.rotation.x = PI / 2
	assert_float_equal(probe.incident(spot, Vector3.ZERO, Vector3.UP, 1), 0.0, "cone follows the source transform")
	spot.free()
	omni.free()

func test_beam_tops_touch_the_rendered_ceiling_without_drops() -> void:
	var world := Node3D.new()
	var ship := ShipScene.build_into(world, Game.new(91))
	var rays := Rays.new()
	var count := 0
	for room: Node3D in [ship.lighting, ship.hallway, ship.power_room]:
		for source: Light3D in room.white_lights():
			var asset: Node3D = source.get_parent().get_node("CeilingFixture")
			var bounds := AABB()
			var first := true
			for part: MeshInstance3D in asset.find_children("*", "MeshInstance3D", true, false):
				var box := Surfaces.world_frame(part) * part.mesh.get_aabb()
				bounds = box if first else bounds.merge(box)
				first = false
			var top := Vector3(bounds.get_center().x, bounds.end.y, bounds.get_center().z)
			var ceiling_y := INF
			for mesh: MeshInstance3D in world.find_children("*", "MeshInstance3D", true, false):
				if not mesh.has_meta(&"surface_frame") or mesh.material_override != Surfaces.material(&"ceiling"): continue
				var surface: Surfaces.SurfaceFrame = mesh.get_meta(&"surface_frame")
				if not String(surface.key).ends_with("/CEILING"): continue
				var hit := rays._hit(mesh.mesh, Surfaces.world_frame(mesh), top - Vector3(0, 0.02, 0), top + Vector3(0, 1, 0))
				if not hit.is_empty(): ceiling_y = minf(ceiling_y, hit.position.y)
			assert_true(is_finite(ceiling_y), "beam has a rendered ceiling above it")
			assert_float_equal(top.y, Vector3(0, 3.2, 0).y, "beam top remains on its authored mounting plane")
			var underside := Vector3(0, 3.2, 0).y
			print("MOUNT ", room.name, " top_y=", top.y, " ceiling_underside_y=", ceiling_y)
			assert_int_equal(roundi(ceiling_y * 100000), roundi(underside * 100000), "rendered ceiling underside is measured independently")
			assert_int_equal(roundi((top.y - ceiling_y) * 100000), roundi((Vector3(0, 3.2, 0).y - underside) * 100000), "beam contacts the architectural ceiling; there is no air gap")
			assert_false(source.get_parent().has_node("CeilingMount"), "no beam hanger")
			count += 1
	assert_int_equal(count, 16, "all sixteen mounting planes measured")
	world.free()
