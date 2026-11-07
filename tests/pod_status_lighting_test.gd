extends SimTestCase
## Local indirect-light proxies follow the always-on pod status belts (#88).

func test_status_spill_is_local_symmetric_and_red() -> void:
	var lighting := Lighting.build(Game.new(0))
	var groups := lighting.find_children("PodStatusSpill*","Node3D",true,false)
	assert_int_equal(groups.size(),Pods.POD_COUNT,"each pod has its own bounded status spill")
	for group: Node3D in groups:
		var lights := group.find_children("*","OmniLight3D",false,false)
		assert_int_equal(lights.size(),6,"four belt samples and two head-seam bounces")
		var belt_positions: Array[Vector3] = []
		var head_positions: Array[Vector3] = []
		for light: OmniLight3D in lights:
			assert_true(light.light_color == Lighting.EMERGENCY_RED,"the status belt adds no white ambient fill")
			assert_false(light.shadow_enabled,"indirect proxies add no shadow maps")
			assert_true(is_zero_approx(light.light_specular),"indirect fill must not reflect a point source on glossy plastic")
			assert_int_equal(light.light_cull_mask,1 << 19,"fill illuminates pod receivers, not bay walls or floor")
			assert_true(is_equal_approx(light.light_energy,.14),"diffuse fill retains the measured shell visibility")
			assert_true(is_equal_approx(light.omni_range,1.1),"spill stays local to the pod")
			if String(light.name).begins_with("HeadStatusBounce"):
				head_positions.append(light.position)
			else:
				belt_positions.append(light.position)
		for side: float in [-1.0,1.0]:
			assert_true(Vector3(side*.38,.42,-1.30) in head_positions,"both sides of the attached head roll receive the wall bounce")
			for station: float in [-.45,.45]:
				assert_true(Vector3(side*.52,.28,station) in belt_positions,"the belt spill is mirrored at the existing belt height")
	lighting.free()

func test_status_spill_remains_on_after_secondary_power() -> void:
	var game := Game.new(0)
	var lighting := Lighting.build(game)
	game.press_console()
	game.press_console()
	lighting.process_frame(1.0)
	var lights := 0
	for group: Node3D in lighting.find_children("PodStatusSpill*","Node3D",true,false):
		for light: OmniLight3D in group.get_children():
			lights += 1
			assert_true(light.visible,"the always-on belt still illuminates nearby shell under white service lighting")
			assert_true(is_equal_approx(light.light_energy,.14),"room power changes do not extinguish pod status spill")
	assert_int_equal(lights,6*Pods.POD_COUNT,"every pod retains all status spill samples")
	lighting.free()

func test_status_receivers_survive_ship_light_isolation() -> void:
	var root := Node3D.new()
	var ship := ShipScene.build_into(root,Game.new(0))
	for mesh: MeshInstance3D in ship.pods_node.find_children("*","MeshInstance3D",true,false):
		if mesh.name == "PodStrips":
			continue
		assert_true((mesh.layers & (1 << 19)) != 0,"shell and interior receive status fill")
		assert_true((mesh.layers & 1) != 0,"room lighting and reflection captures still see the pod")
	for mesh: MeshInstance3D in ship.room.find_children("*","MeshInstance3D",true,false):
		assert_int_equal(mesh.layers & (1 << 19),0,"bay walls and floor cannot receive status fill")
	for group: Node3D in ship.lighting.find_children("PodStatusSpill*","Node3D",true,false):
		for light: OmniLight3D in group.get_children():
			assert_int_equal(light.light_cull_mask,1 << 19,"ship circuit isolation preserves the receiver-only fill")
	root.free()
