extends SimTestCase

const Routes = preload("res://sim/stasis_wiring_routes.gd")

func test_offline_graph_has_source_trunks_and_each_power_data_pod_feed() -> void:
	var graph := Routes.graph()
	assert_true(Routes.validate(graph).is_empty(), "authored semantic route graph is valid")
	var ids: Dictionary = {}
	for node: Dictionary in graph.nodes: ids[node.id] = node
	assert_true(ids.has("enclosure"), "source enclosure is anchored")
	assert_true(ids.enclosure.position == Vector3(-5.935,2.75,-3.1), "semantic source matches the installed end-wall enclosure")
	assert_true(ids.has("power_underpanel_trunk") and ids.has("data_underpanel_trunk"), "power and data remain separate supported trunks")
	for pod: int in range(1, 8):
		assert_true(ids.has("pod_%d_power_base" % pod), "pod has a power base feed")
		assert_true(ids.has("pod_%d_data_base" % pod), "pod has a data base feed")
	assert_true(graph.fault.all_tips_power_only and graph.fault.tips.size()==3 and graph.fault.released_cores_and_sparks_installed, "three actual power tips are installed")
	assert_true(graph.fault.seat_center == BayCeiling.FAILED_SEAT_CENTER and graph.fault.upper_carriers_intact, "fault uses the retained lower seat at Z=-0.6 without breaking upper carriers")
	assert_true(graph.fault.connection_endpoints.size() == 4, "two physical power cables reach each retained seat end")
	assert_true(ids.power_floor_drop.position.is_equal_approx(Vector3(-4.02,-0.1,-3.93)) and ids.data_floor_drop.position.is_equal_approx(Vector3(-4.18,-0.1,-3.955)), "one measured interpod wall drop pair replaces the five-riser proposal")
	for index in range(7):
		var pod: Vector3 = Routes.PODS[index]
		assert_true(ids["pod_%d_power_base" % [index+1]].position.is_equal_approx(pod+Vector3(-0.06,0.08,0)), "power terminates inside the stationary central plinth")
		assert_true(ids["pod_%d_data_base" % [index+1]].position.is_equal_approx(pod+Vector3(0.06,0.08,0)), "data uses its separate hidden bore")

func test_invalid_endpoints_duplicate_ids_and_disconnected_terminals_are_reported() -> void:
	var broken := Routes.graph()
	broken.edges[0].to = "missing"
	broken.edges[1].id = broken.edges[0].id
	broken.edges.erase(broken.edges[-1])
	var errors := Routes.validate(broken)
	assert_true(errors.size() >= 3, "bad endpoint, duplicate edge id, and missing terminal are all explicit errors")

func test_missing_terminal_and_fault_branches_are_detected_independently() -> void:
	for terminal: String in ["pod_7_data_base","fault_right_2_connection"]:
		var broken := Routes.graph()
		for edge: Dictionary in broken.edges.duplicate():
			if edge.to == terminal: broken.edges.erase(edge)
		var errors := Routes.validate(broken)
		var expected := 1 if terminal=="pod_7_data_base" else 2
		assert_int_equal(errors.size(),expected,"report both the retained connection and its disconnected seal")
		assert_true(String(errors[0]).contains(terminal), "the exact severed physical endpoint must be reported")
