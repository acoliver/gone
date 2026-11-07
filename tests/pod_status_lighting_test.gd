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
			assert_true(is_equal_approx(light.light_energy,.12),"status spill energy is explicit")
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
			assert_true(is_equal_approx(light.light_energy,.12),"room power changes do not extinguish pod status spill")
	assert_int_equal(lights,6*Pods.POD_COUNT,"every pod retains all status spill samples")
	lighting.free()
