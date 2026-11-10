class_name StatusBoardData
extends RefCounted

const MINIMUM_ROW_CELL_PX := 60
const DECK_COUNT := {"native": "wupo [36]", "perceived_es": "30 CUBIERTAS"}
const ATLAS_PATH := "res://docs/art/ship/3d/ship_atlas.json"
const SYSTEMS: Array[Dictionary] = [
	{"native": "te na nawa lina", "perceived_es": "ENERGÍA PRINCIPAL", "state": "palo"},
	{"native": "te mu nawa lina", "perceived_es": "ENERGÍA SECUNDARIA", "state": "shenu"},
	{"native": "chena lina", "perceived_es": "RED DE LA NAVE", "state": "palo"},
	{"native": "taka chena lina", "perceived_es": "RED DE EMERGENCIA", "state": "palo"},
	{"native": "kimela lina", "perceived_es": "COMPUTADORAS DE LA NAVE", "state": "palo"},
	{"native": "te mu kimela lina", "perceived_es": "COMPUTADORAS SECUNDARIAS", "state": "palo"},
	{"native": "wesha kama", "perceived_es": "MOTOR S", "state": "palo"},
	{"native": "chalu kama", "perceived_es": "MOTOR H", "state": "palo"},
	{"native": "pama shoketa", "perceived_es": "SENSORES INTERNOS", "state": "palo"},
	{"native": "te mu pama shoketa", "perceived_es": "SENSORES INTERNOS SECUNDARIOS", "state": "palo"},
	{"native": "showi shoketa", "perceived_es": "SENSORES EXTERNOS", "state": "palo"},
	{"native": "te mu showi shoketa", "perceived_es": "SENSORES EXTERNOS SECUNDARIOS", "state": "palo"},
	{"native": "kelawa pasha lina", "perceived_es": "EXTINCIÓN DE INCENDIOS", "state": "palo"},
	{"native": "talu lina", "perceived_es": "SOPORTE VITAL", "state": "palo"},
]
const HEADER := {"native": "malu mishela", "perceived_es": "MAPA DE LA NAVE"}
const DAMAGE := {"native": "mo lokemi malu", "perceived_es": "SIN DAÑOS EN LA NAVE"}
const HERE := {"native": "wupo to lometa [16] pama", "perceived_es": "CUBIERTA 14 · USTED ESTÁ AQUÍ"}

static func running_system_count() -> int:
	var count := 0
	for system: Dictionary in SYSTEMS:
		if system.state == "shenu":
			count += 1
	return count

static func native_text() -> PackedStringArray:
	var lines := PackedStringArray([HEADER.native, DAMAGE.native, HERE.native, DECK_COUNT.native])
	for system: Dictionary in SYSTEMS:
		lines.append(system.native)
	return lines

static func side_elevation(rect: Rect2) -> Dictionary:
	var atlas: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(ATLAS_PATH))
	var coordinates: Dictionary = atlas.coordinate_system
	var profile: Array = coordinates.hull_profile
	var envelope: Dictionary = coordinates.envelope_max
	var opening := int(str(coordinates.opening_deck).trim_prefix("D"))
	var deck_count := 0
	for group: Dictionary in atlas.grid.groups:
		deck_count = maxi(deck_count, int(group.decks[1]))
	var hull := PackedVector2Array()
	for station: Dictionary in profile:
		hull.append(_elevation_point(rect, envelope, station.x, station.halfheight))
	for index in range(profile.size() - 1, -1, -1):
		hull.append(_elevation_point(rect, envelope, profile[index].x, -float(profile[index].halfheight)))
	var decks: Array[Dictionary] = []
	for number in range(1, deck_count + 1):
		var floor_y := (opening - number) * float(coordinates.deck_pitch)
		var span := _deck_span(profile, absf(floor_y))
		decks.append({
			"number": number,
			"floor_y": floor_y,
			"highlighted": number == opening,
			"line": PackedVector2Array([
				_elevation_point(rect, envelope, span.y, floor_y),
				_elevation_point(rect, envelope, span.x, floor_y),
			]),
		})
	return {"hull": hull, "decks": decks, "marker": _elevation_point(rect, envelope, 27.0, float(coordinates.opening_floor_y))}

static func _elevation_point(rect: Rect2, envelope: Dictionary, x: float, y: float) -> Vector2:
	return rect.position + Vector2(
		inverse_lerp(float(envelope.x[1]), float(envelope.x[0]), x) * rect.size.x,
		inverse_lerp(float(envelope.y[1]), float(envelope.y[0]), y) * rect.size.y
	)

static func _deck_span(profile: Array, height: float) -> Vector2:
	var first := INF
	var last := -INF
	for index in range(profile.size() - 1):
		var a: Dictionary = profile[index]
		var b: Dictionary = profile[index + 1]
		var ah := float(a.halfheight)
		var bh := float(b.halfheight)
		if maxf(ah, bh) < height:
			continue
		var left := float(a.x)
		var right := float(b.x)
		if ah < height:
			left = lerpf(left, right, (height - ah) / (bh - ah))
		if bh < height:
			right = lerpf(float(a.x), right, (height - ah) / (bh - ah))
		first = minf(first, left)
		last = maxf(last, right)
	assert(first < last, "every deck intersects the atlas hull")
	return Vector2(first, last)
