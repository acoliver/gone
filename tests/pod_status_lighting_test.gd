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
			assert_true(light.light_color == Color.RED,"the status belt adds no white ambient fill")
			assert_false(light.shadow_enabled,"indirect proxies add no shadow maps")
			assert_true(is_zero_approx(light.light_specular),"indirect fill must not reflect a point source on glossy plastic")
			assert_int_equal(light.light_cull_mask,Lighting.POD_STATUS_MASK,"fill illuminates pod receivers, not bay walls or floor")
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
		assert_true((mesh.layers & (Lighting.POD_STATUS_MASK)) != 0,"shell and interior receive status fill")
		assert_true((mesh.layers & ship.lighting._reflection_probe.cull_mask) != 0,"reflection captures still see the pod")
		assert_int_equal(mesh.layers & (1 | Lighting.BAY_FILL_MASK | Lighting.HALL_FILL_MASK | Lighting.POWER_FILL_MASK),0,"architectural keys and fills cannot change the pod look")
	for mesh: MeshInstance3D in ship.room.find_children("*","MeshInstance3D",true,false):
		assert_int_equal(mesh.layers & (Lighting.POD_STATUS_MASK),0,"bay walls and floor cannot receive status fill")
	for group: Node3D in ship.lighting.find_children("PodStatusSpill*","Node3D",true,false):
		for light: OmniLight3D in group.get_children():
			assert_int_equal(light.light_cull_mask,Lighting.POD_STATUS_MASK,"ship circuit isolation preserves the receiver-only fill")
	root.free()

func test_pod_receiver_layer_is_disjoint_from_every_architectural_circuit() -> void:
	var layout := ShipLayout.authored().layout
	assert_int_equal(Lighting.POD_STATUS_MASK, 1 << 3, "layer four is reserved for pod lighting")
	assert_int_equal(Lighting.POD_STATUS_MASK & (1 | Lighting.BAY_FILL_MASK | Lighting.HALL_FILL_MASK | Lighting.POWER_FILL_MASK), 0, "all switched-room keys and fills exclude pods")
	for deck: int in range(1, 31):
		for id: StringName in layout.deck(deck).connector_ids():
			assert_int_equal(Lighting.space_mask(layout, id) & Lighting.POD_STATUS_MASK, 0, "connector keys cannot illuminate pods")
		for section: int in [40, 41, 42]:
			assert_int_equal(Lighting.space_mask(layout, ShipLayout.section_id(deck, section)) & Lighting.POD_STATUS_MASK, 0, "section keys cannot illuminate pods")

func test_pod_keys_keep_main_profile_and_follow_the_existing_fade() -> void:
	var game := Game.new(0)
	var lighting := Lighting.build(game)
	var frames := Lighting.fixture_transforms(game.registry)
	assert_int_equal(lighting._pod_keys.size(), 8, "seven pod wall keys plus main's lintel key")
	for index: int in range(8):
		var key := lighting._pod_keys[index]
		assert_true(key.transform.is_equal_approx(frames[index]), "main's fixture placement stays unchanged for pods")
		assert_true(key.light_color == Color.RED, "main's pure-red pod keys")
		assert_float_equal(key.omni_range, 6.0, "main's long throw reaches fitted pod padding")
		assert_float_equal(key.omni_attenuation, 1.0, "main's default falloff")
		assert_int_equal(key.light_cull_mask, Lighting.POD_STATUS_MASK, "pod keys cannot change walls or hatch steel")
		assert_false(key.shadow_enabled, "no added shadow work")
	game.press_console()
	for tick: int in range(Lighting.FIXTURE_SETTLE_TICKS):
		lighting.process_frame(Sim.LOGICAL_TICK_SECS)
		for key: OmniLight3D in lighting._pod_keys:
			assert_float_equal(key.light_energy, PackedFloat32Array([Lighting.FIXTURE_ENERGY * lighting.level()])[0], "pod keys use the existing emergency fade at native light-property precision")
	for white: OmniLight3D in lighting.white_lights():
		assert_true((white.light_cull_mask & Lighting.POD_STATUS_MASK) != 0, "regular white still lights the pods")
	lighting.free()
