extends SimTestCase
## Installed fault inventory replaces the retired twelve-run dressing.

const EXPECTED := [Vector3(-.77,2.486,-.587), Vector3(-.83,2.556,-.613), Vector3(-.35,2.526,-.613)]

func test_exact_three_sparks_are_the_installed_copper_tip_endpoints() -> void:
	var graph := StasisWiringRoutes.graph()
	var spots := Placement.spark_spots()
	assert_int_equal(spots.size(),3,"three specific physical power tips")
	for index in range(3):
		assert_vec3_equal(spots[index],EXPECTED[index],"tip coordinate is pinned")
		assert_vec3_equal(spots[index],graph.fault.tips[index].end_m,"spark touches copper end")
		assert_true(graph.fault.tips[index].id==StasisWiringRoutes.TIP_IDS[index],"specific tip identity")
		assert_true(graph.fault.tips[index].lead==StasisWiringRoutes.TIP_LEADS[index],"specific released power core")

func test_copper_exposure_and_safe_insulated_core_inventory() -> void:
	var fault: Dictionary = StasisWiringRoutes.graph().fault
	assert_true(fault.sealed_connection=="fault-right-power-2","fourth physical end is sealed")
	assert_int_equal(fault.released_leads.size(),3,"three released insulated cores")
	for index in range(3):
		var lead: Dictionary = fault.released_leads[index]
		var tip: Dictionary = fault.tips[index]
		assert_true(lead["class"]=="power" and tip["class"]=="power","data never sparks")
		assert_true(absf(tip.start_m.distance_to(tip.end_m)-.004)<0.000001,"4 mm copper within native float32 precision")
		assert_float_equal(lead.insulation_radius_m,.004,"released cores are 8 mm OD")
		assert_true(lead.minimum_centerline_radius_m>=.048-0.0001,"released 8 mm core obeys 6D")
		assert_true(lead.actual_mesh_bounds_m[0][1]>=Placement.OVERHEAD_CLEARANCE,"complete insulation clears camera floor")
		assert_true(lead.retained_clamp_contact_gap_m<0.000001,"retained support touches actual jacket")

func test_hazards_bind_to_tip_positions_without_changing_three_effects() -> void:
	var hazards := Hazards.build()
	var groups := hazards.find_children("SparkSpot*","Node3D",true,false)
	assert_int_equal(groups.size(),3,"exactly three existing spark groups")
	for index in range(3):
		assert_vec3_equal(groups[index].position,EXPECTED[index],"actual emitter is on real tip")
		assert_int_equal(groups[index].get_child_count(),3,"one light, one spray and their visible spark arc")
		assert_int_equal(groups[index].find_children("*","OmniLight3D",true,false).size(),1,"one physical spark light")
		assert_true(groups[index].get_node("SparkSpray") is GPUParticles3D,"existing spark spray remains")
		assert_true(groups[index].get_node("SparkArc") is MeshInstance3D,"visible arc seats the light at the installed copper tip")
	assert_float_equal(hazards._next_burst_in,1.5,"initial timing unchanged")
	hazards.free()

func test_tip_reads_are_deterministic_and_do_not_expose_mutable_cache() -> void:
	var first := Placement.spark_spots()
	first[0] = Vector3.ZERO
	var second := Placement.spark_spots()
	for index in range(3): assert_vec3_equal(second[index],EXPECTED[index],"generated tips are immutable to callers")

func test_tip_position_mismatch_and_extra_tip_are_rejected() -> void:
	var broken := StasisWiringRoutes.graph()
	broken.fault.power_tip_positions[0] += Vector3(0,0.01,0)
	var errors := StasisWiringRoutes.validate(broken)
	assert_true(errors.size()==1 and errors[0].contains("power_tip_1"),"exact mismatched tip fails")
	broken = StasisWiringRoutes.graph()
	broken.fault.tips.append(broken.fault.tips[0].duplicate())
	errors = StasisWiringRoutes.validate(broken)
	assert_true(errors.size()==1 and errors[0].contains("exactly power_tip_1/2/3"),"extra spark inventory fails")
