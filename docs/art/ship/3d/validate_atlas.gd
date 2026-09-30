extends SceneTree
## Data-only atlas gate. Run: godot --headless --path . -s docs/art/ship/3d/validate_atlas.gd

const ATLAS := "res://docs/art/ship/3d/ship_atlas.json"
var failures: Array[String] = []

func _initialize() -> void:
	var file := FileAccess.open(ATLAS, FileAccess.READ)
	if file == null:
		_fail("cannot read " + ATLAS)
		_finish()
		return
	var parser := JSON.new()
	if parser.parse(file.get_as_text()) != OK or not (parser.data is Dictionary):
		_fail("JSON parse failed: " + parser.get_error_message())
		_finish()
		return
	var data: Dictionary = parser.data
	_check(data.get("schema_version") == 1, "schema version")
	_check_grid(data.grid)
	var facilities := _index(data.facilities, "facility")
	_check_facilities(data, facilities)
	_check_routes(data.routes, facilities)
	_check_power(data.power, facilities)
	_finish()

func _check_grid(grid: Dictionary) -> void:
	var groups: Array = grid.groups
	var sectors: Array = grid.sectors
	var sides: Array = grid.sides
	_check(groups.size() == 7 and sectors.size() == 5 and sides.size() == 3, "7x5x3 grid")
	_check(_same(groups, [
		{"id": "D01-04", "decks": [1, 4]}, {"id": "D05-08", "decks": [5, 8]},
		{"id": "D09-12", "decks": [9, 12]}, {"id": "D13-16", "decks": [13, 16]},
		{"id": "D17-20", "decks": [17, 20]}, {"id": "D21-25", "decks": [21, 25]},
		{"id": "D26-30", "decks": [26, 30]}
	]), "deck groups cover D01 through D30")
	var expected_sectors := [[-1200, -720], [-720, -240], [-240, 240], [240, 720], [720, 1200]]
	for i in range(5):
		_check(sectors[i].id == i and _same(sectors[i].x, expected_sectors[i]), "sector %d" % i)
	_check(_same(sides, [
		{"id": "port", "z": [-310, -120]}, {"id": "core", "z": [-100, 100]},
		{"id": "starboard", "z": [120, 310]}
	]), "lateral bands")
	var cells: Dictionary = {}
	for entry: Dictionary in grid.districts:
		var key: String = "%s-%s-%s" % [entry.group, int(entry.sector), entry.side]
		_check(not cells.has(key) and entry.id == key, "unique district " + key)
		cells[key] = true
		_check(entry.functions is Array and not entry.functions.is_empty() and not String(entry.category).is_empty(), "district program " + key)
		_check(not String(entry.source).is_empty() and not String(entry.status).is_empty(), "district provenance " + key)
		_check(String(entry.geometry).begins_with("diagrammatic"), "district hull taper marker " + key)
		for group: Dictionary in groups:
			if entry.group == group.id:
				_check(_same(entry.deck_range, group.decks), "district deck range " + key)
		_check(_same(entry.diagrammatic_x, sectors[int(entry.sector)].x) and _same(entry.diagrammatic_z, sides[["port", "core", "starboard"].find(entry.side)].z), "district diagram bin " + key)
		for func_name: String in entry.functions:
			if entry.group == "D13-16":
				_check(not func_name.contains("bank A") and not func_name.contains("bank B") and not func_name.contains("bank C"), "no additional stasis banks " + key)
	for group: Dictionary in groups:
		for sector: Dictionary in sectors:
			for side: Dictionary in sides:
				_check(cells.has("%s-%s-%s" % [group.id, int(sector.id), side.id]), "missing district %s/%s/%s" % [group.id, int(sector.id), side.id])
	_check(cells.size() == 105 and grid.districts.size() == 105, "105 explicit districts")
	var program: Dictionary = {}
	var crew_sectors: Dictionary = {}
	var officer_groups: Dictionary = {}
	for entry: Dictionary in grid.districts:
		for name: String in entry.functions:
			program[name] = true
			if name == "crew cabins" and entry.side != "core":
				crew_sectors["%s-%s" % [int(entry.sector), entry.side]] = true
			if name == "officer staterooms":
				officer_groups[entry.group] = true
	for required in ["command", "navigation", "astrometry", "captain cabin", "medical", "civic rooms", "escape craft", "air handling", "water treatment", "workshops", "distribution buses", "fabrication", "engineering", "M-drive", "primary generation plant", "seven-pod bay", "medical annex"]:
		_check(program.has(required), "district function " + required)
	_check(crew_sectors.size() == 10 and officer_groups.size() >= 4, "crew across fore/mid/aft both sides and scattered officer rooms")

func _index(entries: Array, label: String) -> Dictionary:
	var result: Dictionary = {}
	for entry: Dictionary in entries:
		var id: String = entry.id
		_check(not result.has(id), "unique %s %s" % [label, id])
		result[id] = entry
	return result

func _at(facilities: Dictionary, id: String, xyz: Array, deck: String, status: String) -> void:
	_check(facilities.has(id), "facility " + id)
	if facilities.has(id):
		var item: Dictionary = facilities[id]
		_check(_same(item.xyz, xyz) and item.deck == deck and item.status == status, "coordinate/deck/status " + id)

func _check_facilities(data: Dictionary, facilities: Dictionary) -> void:
	var coordinates: Dictionary = data.coordinate_system
	_check(_same(coordinates.envelope_max, {"x": [-1200, 1200], "y": [-96, 96], "z": [-360, 360]}), "2400x720x192 maximum envelope")
	_check(coordinates.deck_pitch == 5.5 and coordinates.opening_deck == "D14" and coordinates.opening_floor_y == 0 and coordinates.opening_clear_height == 3.2, "opening deck and clearance")
	var profile: Array = coordinates.hull_profile
	_check(profile.size() >= 2 and float(profile[0].x) == -1200.0 and float(profile[-1].x) == 1200.0, "hull profile spans full ship")
	for i in range(profile.size()):
		var station: Dictionary = profile[i]
		_check(float(station.halfwidth) > 0.0 and float(station.halfwidth) <= 360.0 and float(station.halfheight) > 0.0 and float(station.halfheight) <= 96.0, "hull station envelope %d" % i)
		if i > 0:
			_check(float(profile[i - 1].x) < float(station.x), "hull stations increase at %d" % i)
	_check(float(profile[0].halfwidth) < float(profile[4].halfwidth) and float(profile[-1].halfwidth) > float(profile[0].halfwidth), "asymmetric tapered bow and broad aft")
	var cells := _index(data.grid.districts, "district")
	for item: Dictionary in facilities.values():
		var deck: int = int(String(item.deck).substr(1))
		_check(deck >= 1 and deck <= 30 and item.deck == "D%02d" % deck, "deck ID " + item.id)
		var xyz: Array = item.xyz
		_check(xyz.size() == 3 and xyz[0] >= -1200 and xyz[0] <= 1200 and xyz[1] >= -96 and xyz[1] <= 96 and xyz[2] >= -360 and xyz[2] <= 360, "envelope " + item.id)
		if item.kind != "hall light switch":
			_check(is_equal_approx(float(xyz[1]), (14 - deck) * 5.5), "deck floor " + item.id)
		else:
			_check(is_equal_approx(float(xyz[1]), (14 - deck) * 5.5 + 1.25), "switch height")
		_check(cells.has(item.district) and not String(item.source).is_empty() and (item.status == "built" or item.status == "proposed"), "facility source/district/status " + item.id)
		_check(_inside_hull(profile, Vector3(float(xyz[0]), float(xyz[1]), float(xyz[2]))), "facility center inside hull " + item.id)
	for cell: Dictionary in data.grid.districts:
		for ref: String in cell.facility_refs:
			_check(facilities.has(ref) and facilities[ref].district == cell.id, "district facility reference " + cell.id + " -> " + ref)
	_check(_same(facilities.bay.bounds, {"x": [-6, 6], "z": [-4, 4]}) and facilities.bay.clear_height == 3.2, "built bay bounds")
	_check(_same(facilities.hall.bounds, {"x": [6, 30], "z": [-1.5, 1.5]}) and facilities.hall.endcap_x == 30, "hall bounds and blocked endcap")
	_check(_same(facilities.power_room.bounds, {"x": [21, 33], "z": [-9.7, -1.7]}), "power room bounds")
	_at(facilities, "rod", [-0.6, 0, -1.55], "D14", "built")
	_at(facilities, "hatch", [6, 0, 0], "D14", "built")
	_at(facilities, "switch", [6.22, 1.25, 0.85], "D14", "built")
	_at(facilities, "power_door", [27, 0, -1.5], "D14", "built")
	_at(facilities, "backup", [27, 0, -5.7], "D14", "built")
	_at(facilities, "primary", [700, -71.5, 0], "D27", "proposed")
	_at(facilities, "m_drive", [1030, -77, 0], "D28", "proposed")
	_at(facilities, "bridge", [480, 60.5, 0], "D03", "proposed")
	_check(facilities.bridge.district == "D01-04-3-core" and _same(cells["D01-04-3-core"].facility_refs, ["bridge"]), "aft-mid upper bridge district")
	_check(not cells["D01-04-2-core"].functions.has("bridge") and cells["D01-04-3-core"].functions.has("bridge"), "one aft-mid bridge program")
	_at(facilities, "r2", [-525, -44, -180], "D22", "proposed")
	_at(facilities, "remote_room", [-490, -44, -170], "D22", "proposed")
	_at(facilities, "armory", [-560, -44, -190], "D22", "proposed")
	_at(facilities, "remote_pod_1", [-490.7, -44, -170], "D22", "proposed")
	_at(facilities, "remote_pod_2", [-489.3, -44, -170], "D22", "proposed")
	_check(_same(cells["D21-25-0-port"].facility_refs, []) and _same(cells["D21-25-1-port"].facility_refs, ["r2", "remote_room", "armory", "remote_pod_1", "remote_pod_2"]), "single sector 1 port hazard program")
	_check(cells["D21-25-0-port"].category != "hazard" and cells["D21-25-1-port"].category == "hazard", "former bow district remains safe")
	var opening_pods: Array = [
		[-4.8, 0, -2.9], [-3.4, 0, -2.9], [-2, 0, -2.9], [-0.6, 0, -2.9],
		[-2, 0, 2.9], [-3.4, 0, 2.9], [-4.8, 0, 2.9]
	]
	var built_pods := 0
	var remote_pods := 0
	var primary_count := 0
	var backup_count := 0
	var radiation_count := 0
	for item: Dictionary in facilities.values():
		if item.kind == "stasis pod":
			if item.status == "built":
				built_pods += 1
				_check(item.room == "bay" and _has_coordinates(opening_pods, item.xyz), "built pod layout " + item.id)
			else:
				remote_pods += 1
				_check(item.room == "remote_room" and item.deck == "D22", "remote pod room " + item.id)
		if item.kind == "primary generation plant": primary_count += 1
		if item.kind == "secondary generator (local backup)": backup_count += 1
		if item.has("radiation_source"):
			radiation_count += 1
			_check(item.radiation_source == "unknown", "unknown radiation origin " + item.id)
	_check(built_pods == 7 and remote_pods == 2 and built_pods + remote_pods == 9, "seven built and two proposed pods only")
	_check(primary_count == 1 and backup_count == 1, "one main plant and one backup")
	_at(facilities, "pod_6", [-4.8, 0, 2.9], "D14", "built")
	_check(facilities.pod_6.state == "player", "player pod id 6")
	for x in [9, 15, 21]:
		for side in ["north", "south"]:
			var id: String = "leaf_%s_%s" % [x, side]
			_at(facilities, id, [x, 0, -1.5 if side == "north" else 1.5], "D14", "built")
			_check(facilities[id].pierced == false, "unpierced visual leaf " + id)
	_check(radiation_count == 2, "two separate radiation regions")
	_check(_same(facilities.r1.bounds, {"x": [970, 1120], "z": [170, 300]}) and _same(facilities.r1.deck_range, [26, 30]), "M-drive-side radiation bounds")
	_check(_same(facilities.r2.bounds, {"x": [-600, -450], "z": [-230, -130]}) and _same(facilities.r2.deck_range, [21, 23]), "forward-mid radiation bounds")
	_check(facilities.r2.district == "D21-25-1-port" and facilities.r1.bounds.x[0] - facilities.r2.bounds.x[1] > 1400, "radiation zones are distant and disjoint")
	for id: String in ["r1", "r2"]:
		_check(_volume_inside_hull(profile, facilities[id], coordinates.deck_pitch), "hazard volume inside hull " + id)
	_check(facilities.remote_room.radiation_region == "r2" and facilities.armory.radiation_region == "r2" and facilities.armory.shielding == "separate room enclosure", "remote rooms independently enclosed")
	_check(_same(facilities.remote_room.bounds, {"x": [-507, -473], "z": [-184, -156]}) and _same(facilities.armory.bounds, {"x": [-577, -543], "z": [-208, -172]}), "remote room bounds")
	for id: String in ["remote_room", "armory"]:
		var room: Dictionary = facilities[id]
		_check(room.district == "D21-25-1-port" and _bounds_within(room.bounds, facilities.r2.bounds), "remote room inside R2 " + id)
		_check(_volume_inside_hull(profile, room, coordinates.deck_pitch), "remote room inside hull " + id)
	_check(facilities.remote_room.bounds.x[0] > facilities.armory.bounds.x[1], "remote pod room and armory do not overlap")
	for id: String in ["remote_pod_1", "remote_pod_2"]:
		var pod: Dictionary = facilities[id]
		_check(pod.district == "D21-25-1-port" and _point_in_bounds(pod.xyz, facilities.remote_room.bounds), "remote pod inside room " + id)
	var trunk_positions := [[-550, 0, -90], [-300, 0, 90], [300, 0, -90], [850, 0, 90]]
	for i in range(4):
		var trunk: Dictionary = facilities["trunk_%d" % (i + 1)]
		_check(_same(trunk.xyz, trunk_positions[i]) and _same(trunk.deck_range, [1, 30]), "through trunk %d" % (i + 1))
		for y: float in [-88.0, 77.0]:
			for x: float in [float(trunk.xyz[0]) - 3.0, float(trunk.xyz[0]) + 3.0]:
				for z: float in [float(trunk.xyz[2]) - 3.0, float(trunk.xyz[2]) + 3.0]:
					_check(_inside_hull(profile, Vector3(x, y, z)), "through trunk %d full-deck extent" % (i + 1))

func _hull_limits(profile: Array, x: float) -> Vector2:
	for i in range(1, profile.size()):
		var a: Dictionary = profile[i - 1]
		var b: Dictionary = profile[i]
		if x <= float(b.x):
			var t := (x - float(a.x)) / (float(b.x) - float(a.x))
			return Vector2(lerpf(float(a.halfwidth), float(b.halfwidth), t), lerpf(float(a.halfheight), float(b.halfheight), t))
	return Vector2.ZERO

func _inside_hull(profile: Array, point: Vector3) -> bool:
	if point.x < float(profile[0].x) or point.x > float(profile[-1].x):
		return false
	var limits := _hull_limits(profile, point.x)
	if absf(point.y) > limits.y or absf(point.z) > limits.x:
		return false
	# Same flattened plate-side section used by atlas.gd: z = halfwidth * cos(angle)^0.1.
	return pow(point.y / limits.y, 2.0) + pow(absf(point.z) / limits.x, 20.0) <= 1.00001

func _point_in_bounds(xyz: Array, bounds: Dictionary) -> bool:
	return float(xyz[0]) >= float(bounds.x[0]) and float(xyz[0]) <= float(bounds.x[1]) and float(xyz[2]) >= float(bounds.z[0]) and float(xyz[2]) <= float(bounds.z[1])

func _bounds_within(inner: Dictionary, outer: Dictionary) -> bool:
	return float(inner.x[0]) >= float(outer.x[0]) and float(inner.x[1]) <= float(outer.x[1]) and float(inner.z[0]) >= float(outer.z[0]) and float(inner.z[1]) <= float(outer.z[1])

func _volume_inside_hull(profile: Array, item: Dictionary, pitch: float) -> bool:
	var bounds: Dictionary = item.bounds
	var low := float(item.xyz[1])
	var high := low + 3.2
	if item.has("deck_range"):
		low = (14 - int(item.deck_range[1])) * pitch
		high = (15 - int(item.deck_range[0])) * pitch
	var xs: Array[float] = [float(bounds.x[0]), float(bounds.x[1])]
	for station: Dictionary in profile:
		if float(station.x) > xs[0] and float(station.x) < xs[1]:
			xs.append(float(station.x))
	for x: float in xs:
		for y: float in [low, high]:
			for z: float in [float(bounds.z[0]), float(bounds.z[1])]:
				if not _inside_hull(profile, Vector3(x, y, z)):
					return false
	return true

func _check_routes(routes: Dictionary, facilities: Dictionary) -> void:
	var nodes := _index(routes.nodes, "route node")
	var opening := ["bay", "hatch", "hall", "power_door", "power_room", "leaf_15_south"]
	var portal := false
	var r1_entry := 0
	var r2_entry := 0
	for node: Dictionary in nodes.values():
		if node.has("facility_ref"):
			_check(facilities.has(node.facility_ref), "route facility reference " + node.id)
	for edge: Dictionary in routes.edges:
		_check(nodes.has(edge["from"]) and nodes.has(edge["to"]), "route endpoint " + edge["from"] + " -> " + edge["to"])
		_check(["built", "future", "sealed"].has(edge.status), "route status")
		if edge.status == "built":
			_check(opening.has(edge["from"]) and opening.has(edge["to"]), "no built opening to proposed network")
		if edge["from"] == "leaf_15_south" and edge["to"] == "future_neighbor":
			portal = edge.status == "future" and String(edge.kind).contains("pierce")
		if ["r1", "r2", "remote_room", "armory"].has(edge["from"]) or ["r1", "r2", "remote_room", "armory"].has(edge["to"]):
			_check(edge.status == "sealed", "hazard route sealed " + edge["from"] + " -> " + edge["to"])
		if edge["to"] == "r1":
			r1_entry += 1
		if edge["to"] == "r2":
			r2_entry += 1
	_check(portal and r1_entry == 1 and r2_entry == 1, "future opening and two isolated spurs")
	_check(_same(routes.longitudinal_passages_z, [-90, 90]) and routes.through_trunks == ["trunk_1", "trunk_2", "trunk_3", "trunk_4"], "two passage axes and four trunks")

func _check_power(power: Dictionary, facilities: Dictionary) -> void:
	var nodes := _index(power.nodes, "power node")
	var expected := ["plant>isolation:future", "isolation>distribution:future", "distribution>breakers:future", "secondary>local_emergency:built", "local_emergency>transfer:future", "transfer>breakers:sealed"]
	var observed: Array[String] = []
	for node: Dictionary in nodes.values():
		_check(facilities.has(node.facility_ref), "power facility reference " + node.id)
	for edge: Dictionary in power.edges:
		_check(nodes.has(edge["from"]) and nodes.has(edge["to"]), "power endpoints")
		observed.append("%s>%s:%s" % [edge["from"], edge["to"], edge.status])
	_check(observed == expected, "main isolation/distribution/breakers and isolated backup transfer")
	_check(nodes.plant.facility_ref == "primary" and nodes.secondary.facility_ref == "backup", "generation references")
	_check(String(power.transfer_rule).contains("does not energize"), "no whole-ship backup")

func _has_coordinates(options: Array, coordinates: Array) -> bool:
	for option: Array in options:
		if _same(option, coordinates):
			return true
	return false

func _same(left: Variant, right: Variant) -> bool:
	if left is Array and right is Array:
		if left.size() != right.size():
			return false
		for i in range(left.size()):
			if not _same(left[i], right[i]):
				return false
		return true
	if left is Dictionary and right is Dictionary:
		if left.size() != right.size():
			return false
		for key: Variant in left:
			if not right.has(key) or not _same(left[key], right[key]):
				return false
		return true
	if (left is float or left is int) and (right is float or right is int):
		return is_equal_approx(float(left), float(right))
	return left == right

func _check(condition: bool, message: String) -> void:
	if not condition:
		_fail(message)

func _fail(message: String) -> void:
	failures.append(message)
	printerr("atlas: " + message)

func _finish() -> void:
	if failures.is_empty():
		print("ship atlas PASS: 105 districts; D01-D30; 7 built + 2 proposed pods; 2 radiation zones; 1 primary + 1 local backup; isolated route and power graphs")
		quit(0)
	else:
		printerr("ship atlas FAIL: %d violations" % failures.size())
		quit(1)
