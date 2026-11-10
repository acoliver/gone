class_name StasisWiringRoutes
extends RefCounted
## Bay-local route data generated with the baked installation; no scene objects.

const PODS := [
	Vector3(-4.8, 0.0, -2.596501), Vector3(-3.4, 0.0, -2.596501),
	Vector3(-2.0, 0.0, -2.596501), Vector3(-0.6, 0.0, -2.596501),
	Vector3(-2.0, 0.0, 2.596501), Vector3(-3.4, 0.0, 2.596501),
	Vector3(-4.8, 0.0, 2.596501),
]
const SOURCE := Vector3(-5.935, 2.75, -3.1)
const POWER_OD := 0.024
const DATA_OD := 0.006
const POWER_BEND_RADIUS := 0.144
const DATA_BEND_RADIUS := 0.048

const INSTALLATION := "res://assets/props/stasis-wiring/production-routes.json"
const TIP_IDS := ["power_tip_1", "power_tip_2", "power_tip_3"]
const TIP_LEADS := ["released-left-1", "released-left-2", "released-right-1"]
static var _power_tips: Array[Vector3] = []

static func power_tips() -> Array[Vector3]:
	if _power_tips.is_empty():
		var installed := graph()
		var errors := validate(installed)
		assert(errors.is_empty(), "invalid production fault: " + str(errors))
		_power_tips.assign(installed.fault.power_tip_positions)
	return _power_tips.duplicate()

static func graph() -> Dictionary:
	var file := FileAccess.open(INSTALLATION, FileAccess.READ)
	assert(file != null, "required baked production route graph")
	var parsed: Variant = JSON.parse_string(file.get_as_text())
	assert(parsed is Dictionary, "production route graph must be an object")
	var result: Dictionary = parsed
	for node: Dictionary in result.nodes: node.position = _point(node.position)
	for edge: Dictionary in result.edges:
		var points: Array[Vector3] = []
		for point: Array in edge.points: points.append(_point(point))
		edge.points = points
	var fault: Dictionary = result.fault
	fault.opening_cell = Vector2i(int(fault.opening_cell[0]),int(fault.opening_cell[1]))
	fault.opening_center = _point(fault.opening_center)
	fault.seat_center = _point(fault.seat_center)
	var endpoints: Array[Vector3] = []
	for point: Array in fault.connection_endpoints: endpoints.append(_point(point))
	fault.connection_endpoints = endpoints
	var tips: Array[Vector3] = []
	for point: Array in fault.power_tip_positions: tips.append(_point(point))
	fault.power_tip_positions = tips
	for tip: Dictionary in fault.tips:
		tip.start_m = _point(tip.start_m)
		tip.end_m = _point(tip.end_m)
	return result

static func _point(value: Array) -> Vector3:
	return Vector3(float(value[0]),float(value[1]),float(value[2]))

static func validate(candidate: Dictionary) -> PackedStringArray:
	var errors := PackedStringArray()
	var nodes_by_id: Dictionary = {}
	for node: Dictionary in candidate.get("nodes", []):
		var id: String = node.get("id", "")
		if id.is_empty() or nodes_by_id.has(id): errors.append("empty or duplicate node id: " + id)
		else: nodes_by_id[id] = node
	var outgoing: Dictionary = {}
	var incoming: Dictionary = {}
	for edge: Dictionary in candidate.get("edges", []):
		var id: String = edge.get("id", "")
		if id.is_empty() or outgoing.has("edge:"+id): errors.append("empty or duplicate edge id: " + id)
		outgoing["edge:"+id] = true
		var from_id: String = edge.get("from", "")
		var to_id: String = edge.get("to", "")
		if not nodes_by_id.has(from_id) or not nodes_by_id.has(to_id):
			errors.append("edge has missing endpoint: " + id)
			continue
		var points: Array = edge.get("points", [])
		if points.size() < 2 or points[0] != nodes_by_id[from_id].position or points[-1] != nodes_by_id[to_id].position:
			errors.append("edge endpoints do not match route points: " + id)
		if not ["power","data"].has(edge.get("class", "")): errors.append("unsupported cable class: " + id)
		if not edge.get("supported", false): errors.append("unsupported branch without retained support: " + id)
		if edge.get("physical_routes", []).is_empty(): errors.append("edge has no baked route reference: " + id)
		if not outgoing.has(from_id): outgoing[from_id] = []
		outgoing[from_id].append(to_id)
		incoming[to_id] = true
	var reached: Dictionary = {"enclosure": true}
	var frontier: Array[String] = ["enclosure"]
	while not frontier.is_empty():
		var current: String = frontier.pop_back()
		for next: String in outgoing.get(current, []):
			if not reached.has(next):
				reached[next] = true
				frontier.append(next)
	for index: int in range(PODS.size()):
		for cable_class: String in ["power","data"]:
			var terminal := "pod_%d_%s_base" % [index+1,cable_class]
			if not nodes_by_id.has(terminal) or not incoming.has(terminal) or not reached.has(terminal): errors.append("disconnected pod feed: " + terminal)
	for side: String in ["left","right"]:
		for index in [1,2]:
			var connection := "fault_%s_%d_connection" % [side,index]
			if not reached.has(connection): errors.append("disconnected retained power connection: " + connection)
	var fault: Dictionary = candidate.fault
	if fault.tips.size()!=3 or fault.power_tip_positions.size()!=3 or fault.released_leads.size()!=3:
		errors.append("fault requires exactly power_tip_1/2/3 and their three released leads")
		return errors
	for index in range(3):
		var tip: Dictionary = fault.tips[index]
		if tip.id!=TIP_IDS[index] or tip.lead!=TIP_LEADS[index] or tip["class"]!="power":
			errors.append("incorrect power tip inventory: " + str(tip.id))
		if not reached.has(TIP_IDS[index]): errors.append("disconnected exposed power tip: " + TIP_IDS[index])
		if not nodes_by_id.has(tip.id) or nodes_by_id[tip.id].position!=tip.end_m or fault.power_tip_positions[index]!=tip.end_m:
			errors.append("spark does not match physical copper tip: " + str(tip.id))
		if not is_equal_approx(tip.exposed_length_m,0.004) or absf(tip.start_m.distance_to(tip.end_m)-0.004)>0.000001:
			errors.append("power tip must expose exactly 4 mm: " + str(tip.id))
	if fault.sealed_connection!="fault-right-power-2" or not reached.has("fault_right_2_sealed"):
		errors.append("fourth power jacket is not sealed: fault_right_2_sealed")
	return errors
