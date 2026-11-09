extends RefCounted

const MIN_WALL_SPACING := 1.5
const MAX_SHARE_RATIO := 3.0

static func rows(inventory: Dictionary) -> Array[Dictionary]:
	var layout := ShipLayout.authored().layout
	var groups: Dictionary = {}
	for source: Dictionary in inventory.lights_and_emissives:
		if source.kind != "light" or source.fixture == "NONE": continue
		if "PodStrips" in source.fixture or "/Generator/" in source.fixture or "SparkArc" in source.fixture: continue
		var key: String = source.circuit_state + "/" + source.fixture
		if not groups.has(key):
			var bounds: AABB
			if source.owner == ShipLayout.BAY_ID: bounds = layout.bay_to_world() * layout.bay().local_bounds()
			elif source.owner == ShipLayout.POWER_ID: bounds = layout.power_room().bounds()
			elif StringName(source.owner) in layout.connector_ids(): bounds = layout.connector(source.owner).bounds()
			else: bounds = layout.section(source.owner).bounds()
			var p := Vector3(source.position[0], source.position[1], source.position[2])
			var distances := [absf(p.x - bounds.position.x), absf(p.x - bounds.end.x), absf(p.z - bounds.position.z), absf(p.z - bounds.end.z)]
			var wall: String = ["WEST", "EAST", "PORT", "STARBOARD"][distances.find(distances.min())]
			if p.y >= bounds.end.y - 0.15: wall = "CEILING"
			groups[key] = {"owner": source.owner, "state": source.circuit_state, "fixture": source.fixture, "position": source.position, "wall": wall, "share": 0.0, "sources": [], "live": false}
		groups[key].share += source.energy / Lighting.FIXTURE_ENERGY
		groups[key].sources.append(source)
		var switched: bool = source.owner in [ShipLayout.BAY_ID, ShipLayout.POWER_ID, "D14-S-041"]
		var white: bool = "RecessedGlass" in source.fixture or "RegularFillEnd" in source.fixture
		groups[key].live = groups[key].live or not switched or white == (source.circuit_state == "secondary-white")
	var result: Array[Dictionary] = []
	for row: Dictionary in groups.values(): result.append(row)
	return result

static func close_pairs(fixtures: Array[Dictionary]) -> Array[String]:
	var failures: Array[String] = []
	for index: int in range(fixtures.size()):
		var a := fixtures[index]
		if a.wall == "CEILING": continue
		for next: int in range(index + 1, fixtures.size()):
			var b := fixtures[next]
			if a.owner != b.owner or a.state != b.state or a.wall != b.wall: continue
			var p := Vector3(a.position[0], a.position[1], a.position[2])
			var q := Vector3(b.position[0], b.position[1], b.position[2])
			var distance := p.distance_to(q)
			if distance <= MIN_WALL_SPACING:
				failures.append("%s %s %s: %s and %s are %.3f m apart" % [a.state, a.owner, a.wall, a.fixture, b.fixture, distance])
	return failures

static func dim_lamps(fixtures: Array[Dictionary]) -> Array[String]:
	var circuits: Dictionary = {}
	for row: Dictionary in fixtures:
		if not row.live: continue
		var key: String = row.state + "/" + row.owner
		if not circuits.has(key): circuits[key] = []
		circuits[key].append(row)
	var failures: Array[String] = []
	for key: String in circuits:
		var shares: Array[float] = []
		for row: Dictionary in circuits[key]: shares.append(row.share)
		shares.sort()
		var median := shares[shares.size() / 2] if shares.size() % 2 else (shares[shares.size() / 2 - 1] + shares[shares.size() / 2]) / 2.0
		for row: Dictionary in circuits[key]:
			if row.share <= 0.0 or row.share < median / MAX_SHARE_RATIO:
				failures.append("%s: %s share %.4f must be positive and at least median %.4f / %.0f" % [key, row.fixture, row.share, median, MAX_SHARE_RATIO])
	return failures
