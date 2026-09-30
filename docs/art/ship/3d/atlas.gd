extends Node3D
## Out-of-world planning display. All world coordinates are meters from ship_atlas.json.

const DATA_PATH := "res://docs/art/ship/3d/ship_atlas.json"
const RESULT_LIMIT := 35
const FUNCTION_COLORS := {
	"command": Color("78bfff"),
	"living / quarters": Color("a9d985"),
	"civic / medical": Color("e99fcb"),
	"utilities": Color("86d3ce"),
	"industrial": Color("e5bb77"),
	"generation / propulsion": Color("bd9ef4"),
	"hazards": Color("f27676")
}
const BUILT := Color("5ee0ad")
const FUTURE := Color("90a9c4")
const HAZARD := Color("f05b64")

var atlas: Dictionary
var facilities: Dictionary = {}
var route_nodes: Dictionary = {}
var district_nodes: Array[Node3D] = []
var districts: Dictionary = {}
var district_highlights: Dictionary = {}
var floor_nodes: Array[Node3D] = []
var facility_nodes: Dictionary = {}
var facility_glyphs: Dictionary = {}
var facility_details: Dictionary = {}
var facility_highlights: Dictionary = {}
var facility_labels: Dictionary = {}
var route_nodes_3d: Array[Node3D] = []
var power_nodes_3d: Array[Node3D] = []
var hull_cage: Node3D
var opening_node: Node3D
var extension_node: Node3D
var sides: Dictionary = {"port": true, "core": true, "starboard": true}
var selected_deck: int = 0
var selected_id := ""
var selected_district := ""
var orbit_target := Vector3(-410, 0, 0)
var orbit_yaw := 0.35
var orbit_pitch := 0.55
var orbit_distance := 1950.0
var camera: Camera3D
var deck_choice: OptionButton
var facility_list: ItemList
var search: LineEdit
var detail: Label
var district_list: ItemList
var district_search: LineEdit
var district_detail: Label
var district_count: Label
var deck_readout: Label
var route_toggle: CheckButton
var power_toggle: CheckButton
var shown_facilities: Array[String] = []
var shown_districts: Array[String] = []
var side_toggles: Dictionary = {}

func _ready() -> void:
	var file := FileAccess.open(DATA_PATH, FileAccess.READ)
	assert(file != null, "Missing atlas JSON")
	var parser := JSON.new()
	assert(parser.parse(file.get_as_text()) == OK, parser.get_error_message())
	assert(parser.data is Dictionary, "Atlas JSON root must be an object")
	atlas = parser.data
	assert(atlas.schema_version == 1, "Unsupported atlas schema")
	for item: Dictionary in atlas.facilities:
		facilities[item.id] = item
	for item: Dictionary in atlas.grid.districts:
		districts[item.id] = item
	for item: Dictionary in atlas.routes.nodes:
		route_nodes[item.id] = item
	_build_camera()
	_build_hull()
	_build_decks()
	_build_districts()
	_build_facilities()
	_build_opening()
	_build_routes()
	_build_power()
	_build_ui()
	_apply_filters()
	_update_camera()

func _build_camera() -> void:
	camera = Camera3D.new()
	camera.fov = 62.0
	camera.near = 0.05
	camera.far = 12000.0
	add_child(camera)
	camera.current = true
	var environment := WorldEnvironment.new()
	var settings := Environment.new()
	settings.background_mode = Environment.BG_COLOR
	settings.background_color = Color("101a29")
	settings.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	settings.ambient_light_color = Color.WHITE
	settings.ambient_light_energy = 0.9
	environment.environment = settings
	add_child(environment)

func _update_camera() -> void:
	var flat := cos(orbit_pitch) * orbit_distance
	camera.position = orbit_target + Vector3(sin(orbit_yaw) * flat, sin(orbit_pitch) * orbit_distance, cos(orbit_yaw) * flat)
	camera.look_at(orbit_target, Vector3.UP)
	_update_glyphs()

func _update_glyphs() -> void:
	for item: Dictionary in atlas.facilities:
		var p := _position(item)
		var distance := camera.position.distance_to(p)
		var glyph: MeshInstance3D = facility_glyphs[item.id]
		glyph.scale = Vector3.ONE * clampf(distance * 0.007, 1.5, 24.0)
		glyph.visible = selected_deck == 0 and (not item.has("bounds") or distance > 300.0)
		facility_details[item.id].visible = selected_deck != 0
		var highlight: Node3D = facility_highlights[item.id]
		highlight.scale = Vector3.ONE * (1.3 if item.status == "built" else clampf(distance * 0.018, 5.0, 60.0))

func _material(color: Color) -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.albedo_color = color
	mat.no_depth_test = false
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA if color.a < 1.0 else BaseMaterial3D.TRANSPARENCY_DISABLED
	mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	return mat

func _stroke(parent: Node3D, points: PackedVector3Array, color: Color) -> Node3D:
	var mesh := ImmediateMesh.new()
	mesh.surface_begin(Mesh.PRIMITIVE_LINES, _material(color))
	for point: Vector3 in points:
		mesh.surface_add_vertex(point)
	mesh.surface_end()
	var instance := MeshInstance3D.new()
	instance.mesh = mesh
	parent.add_child(instance)
	return instance

func _segment(points: PackedVector3Array, a: Vector3, b: Vector3) -> void:
	points.append(a)
	points.append(b)

func _box(parent: Node3D, low: Vector3, high: Vector3, color: Color) -> void:
	var points := PackedVector3Array()
	for y: float in [low.y, high.y]:
		var a := Vector3(low.x, y, low.z)
		var b := Vector3(high.x, y, low.z)
		var c := Vector3(high.x, y, high.z)
		var d := Vector3(low.x, y, high.z)
		_segment(points, a, b)
		_segment(points, b, c)
		_segment(points, c, d)
		_segment(points, d, a)
	for x: float in [low.x, high.x]:
		for z: float in [low.z, high.z]:
			_segment(points, Vector3(x, low.y, z), Vector3(x, high.y, z))
	_stroke(parent, points, color)

func _bounds(item: Dictionary, bottom: float, height: float, color: Color, parent: Node3D) -> void:
	var x: Array = item.bounds.x
	var z: Array = item.bounds.z
	_box(parent, Vector3(float(x[0]), bottom, float(z[0])), Vector3(float(x[1]), bottom + height, float(z[1])), color)

func _floor(deck: int) -> float:
	return (14 - deck) * float(atlas.coordinate_system.deck_pitch)

func _position(item: Dictionary) -> Vector3:
	var xyz: Array = item.xyz
	return Vector3(float(xyz[0]), float(xyz[1]), float(xyz[2]))

func _build_hull() -> void:
	var cage := Node3D.new()
	cage.name = "Proposed exterior-compatible hull guide (not measured tracing)"
	add_child(cage)
	hull_cage = cage
	var stations: Array = atlas.coordinate_system.hull_profile
	var lines := PackedVector3Array()
	var previous: Array[Vector3] = []
	for station: Dictionary in stations:
		var ring: Array[Vector3] = []
		for j in range(48):
			var angle := TAU * float(j) / 48.0
			var lateral := cos(angle)
			var z: float = signf(lateral) * pow(absf(lateral), 0.10) * float(station.halfwidth)
			ring.append(Vector3(float(station.x), sin(angle) * float(station.halfheight), z))
		for j in range(48):
			_segment(lines, ring[j], ring[(j + 1) % 48])
			if not previous.is_empty():
				_segment(lines, previous[j], ring[j])
		previous = ring
	_stroke(cage, lines, Color(0.30, 0.47, 0.59, 0.58))

func _build_decks() -> void:
	var stations: Array = atlas.coordinate_system.hull_profile
	for deck in range(1, 31):
		var node := Node3D.new()
		node.name = "D%02d floor datum (not occupied floor plan)" % deck
		add_child(node)
		var y := _floor(deck)
		var points := PackedVector3Array()
		var previous := Vector2.ZERO
		for station: Dictionary in stations:
			var x := float(station.x)
			var height := float(station.halfheight)
			if absf(y) <= height:
				var width := maxf(0.0, float(station.halfwidth) * pow(maxf(0.0, 1.0 - pow(y / height, 2.0)), 0.05) - 3.0)
				if previous != Vector2.ZERO:
					for side: float in [-1.0, 1.0]:
						_segment(points, Vector3(previous.x, y, side * previous.y), Vector3(x, y, side * width))
				previous = Vector2(x, width)
			else:
				previous = Vector2.ZERO
		_stroke(node, points, Color(0.38, 0.53, 0.62, 0.40))
		floor_nodes.append(node)

func _function_category(item: Dictionary) -> String:
	var names := ", ".join(item.functions).to_lower()
	if item.category == "hazard":
		return "hazards"
	if names.contains("m-drive") or names.contains("generation") or names.contains("propulsion") or names.contains("drive service"):
		return "generation / propulsion"
	if names.contains("stateroom") or names.contains("captain cabin"):
		return "living / quarters"
	if names.contains("bridge") or names.contains("command") or names.contains("navigation") or names.contains("astrometry") or names.contains("mission planning") or names.contains("operations") or names.contains("flight plotting"):
		return "command"
	if names.contains("medical") or names.contains("clinic") or names.contains("hospital") or names.contains("triage") or names.contains("civic") or names.contains("school") or names.contains("care") or names.contains("gardens") or names.contains("mess") or names.contains("galley") or names.contains("commons"):
		return "civic / medical"
	if names.contains("engineering") or names.contains("fabrication") or names.contains("workshop") or names.contains("freight") or names.contains("maintenance") or names.contains("engine access"):
		return "industrial"
	if names.contains("crew cabins"):
		return "living / quarters"
	return "utilities"

func _district_center(item: Dictionary) -> Vector3:
	var decks: Array = item.deck_range
	var x: Array = item.diagrammatic_x
	var z: Array = item.diagrammatic_z
	return Vector3((float(x[0]) + float(x[1])) * 0.5, (_floor(int(decks[0])) + _floor(int(decks[1]))) * 0.5, (float(z[0]) + float(z[1])) * 0.5)

func _build_districts() -> void:
	for item: Dictionary in atlas.grid.districts:
		var node := Node3D.new()
		node.name = "%s | %s | %s | %s | proposed indexing bin" % [item.id, item.category, ", ".join(item.functions), item.geometry]
		add_child(node)
		var decks: Array = item.deck_range
		var x: Array = item.diagrammatic_x
		var z: Array = item.diagrammatic_z
		var bottom := _floor(int(decks[1]))
		var top := _floor(int(decks[0])) + float(atlas.coordinate_system.deck_pitch)
		var tint: Color = FUNCTION_COLORS[_function_category(item)]
		tint.a = 0.46
		_box(node, Vector3(float(x[0]) + 10.0, bottom, float(z[0]) + 7.0), Vector3(float(x[1]) - 10.0, top, float(z[1]) - 7.0), tint)
		node.set_meta("id", item.id)
		node.set_meta("side", item.side)
		node.set_meta("first", int(decks[0]))
		node.set_meta("last", int(decks[1]))
		district_nodes.append(node)
		var highlight := Node3D.new()
		highlight.name = "Selected proposed bin outline"
		node.add_child(highlight)
		_box(highlight, Vector3(float(x[0]) + 8.0, bottom - 1.0, float(z[0]) + 5.0), Vector3(float(x[1]) - 8.0, top + 1.0, float(z[1]) - 5.0), Color("fff4a3"))
		highlight.visible = false
		district_highlights[item.id] = highlight

func _build_facilities() -> void:
	for item: Dictionary in atlas.facilities:
		var node := Node3D.new()
		node.name = "%s | %s | %s | %s" % [item.id, item.kind, item.deck, item.status]
		add_child(node)
		facility_nodes[item.id] = node
		var p := _position(item)
		var color := BUILT if item.status == "built" else FUTURE
		if item.has("radiation_source"):
			color = HAZARD
		if item.kind == "stasis pod":
			color = BUILT if item.status == "built" else Color("f1c878")
		# Glyphs track camera distance; measured bounds below never change scale.
		var sphere := SphereMesh.new()
		sphere.radius = 1.0
		sphere.height = 2.0
		var marker := MeshInstance3D.new()
		marker.mesh = sphere
		marker.material_override = _material(color)
		marker.position = p
		node.add_child(marker)
		facility_glyphs[item.id] = marker
		var local := Node3D.new()
		local.name = "Meter-scale facility marker"
		local.position = p
		node.add_child(local)
		facility_details[item.id] = local
		if item.kind == "stasis pod":
			var capsule := CapsuleMesh.new()
			capsule.radius = 0.32
			capsule.height = 1.18
			var pod := MeshInstance3D.new()
			pod.mesh = capsule
			pod.material_override = _material(Color("84d5b5") if item.status == "built" else Color("f1c878"))
			pod.rotation.z = PI / 2.0
			pod.position.y = 0.5
			local.add_child(pod)
		elif item.id == "rod":
			_wall(local, Vector3(0, 0.12, 0), Vector3(0.85, 0.12, 0.12), Color("f1c878"))
		elif item.id == "switch":
			_wall(local, Vector3.ZERO, Vector3(0.18, 0.24, 0.18), Color("f1c878"))
		var highlight := Node3D.new()
		highlight.position = p
		node.add_child(highlight)
		var cross := PackedVector3Array()
		for axis: Vector3 in [Vector3.RIGHT, Vector3.UP, Vector3.BACK]:
			_segment(cross, -axis, axis)
		_stroke(highlight, cross, Color("fff4a3"))
		facility_highlights[item.id] = highlight
		if item.has("bounds") and not ["bay", "hall", "power_room"].has(item.id):
			var height := 3.2
			var bottom := p.y
			if item.has("deck_range"):
				var decks: Array = item.deck_range
				bottom = _floor(int(decks[1]))
				height = _floor(int(decks[0])) + 5.5 - bottom
			_bounds(item, bottom, height, color, node)
		if item.kind == "through-deck trunk":
			_box(node, Vector3(p.x - 3, _floor(30), p.z - 3), Vector3(p.x + 3, _floor(1) + 5.5, p.z + 3), Color(0.45, 0.89, 0.81, 0.8))
		var label := Label3D.new()
		label.text = "%s | %s | %s\n%s  (%.1f, %.1f, %.1f)" % [item.id, item.kind, item.status.to_upper(), item.deck, p.x, p.y, p.z]
		label.position = p + Vector3(0, 7, 0)
		label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		label.font_size = 32
		label.pixel_size = 0.015
		label.modulate = Color.WHITE
		label.outline_size = 8
		label.visible = false
		node.add_child(label)
		facility_labels[item.id] = label

func _wall(parent: Node3D, center: Vector3, size: Vector3, color: Color) -> void:
	var mesh := BoxMesh.new()
	mesh.size = size
	var instance := MeshInstance3D.new()
	instance.mesh = mesh
	instance.material_override = _material(color)
	instance.position = center
	parent.add_child(instance)

func _build_opening() -> void:
	var built := Node3D.new()
	built.name = "D14 built footprint | 1:1 meters | bay, pierced hatch, hall, power doorway, blocked leaves and endcap"
	add_child(built)
	opening_node = built
	var wall := Color(0.21, 0.73, 0.64, 0.60)
	var floor_color := Color(0.25, 0.60, 0.56, 0.36)
	# Real bounds at D14. No ceiling slab: inspection stays possible from above.
	for id: String in ["bay", "hall", "power_room"]:
		var item: Dictionary = facilities[id]
		_bounds(item, 0.0, 3.2, BUILT, built)
		var x: Array = item.bounds.x
		var z: Array = item.bounds.z
		_wall(built, Vector3((float(x[0]) + float(x[1])) / 2, -0.08, (float(z[0]) + float(z[1])) / 2), Vector3(float(x[1]) - float(x[0]), 0.16, float(z[1]) - float(z[0])), floor_color)
	# Bay hatch x=6, aperture z=-0.6..0.6 and y=0..2.4.
	for z in [-2.3, 2.3]:
		_wall(built, Vector3(6, 1.6, z), Vector3(0.15, 3.2, 3.4), wall)
	_wall(built, Vector3(6, 2.8, 0), Vector3(0.15, 0.8, 1.2), wall)
	_wall(built, Vector3(-6, 1.6, 0), Vector3(0.15, 3.2, 8), wall)
	for z in [-4.0, 4.0]:
		_wall(built, Vector3(0, 1.6, z), Vector3(12, 3.2, 0.15), wall)
	# Hall south side has six intact, impassable leaves; power door alone is pierced.
	_wall(built, Vector3(18, 1.6, 1.5), Vector3(24, 3.2, 0.15), wall)
	_wall(built, Vector3(30, 1.6, 0), Vector3(0.15, 3.2, 3), HAZARD)
	_wall(built, Vector3(16.25, 1.6, -1.5), Vector3(20.5, 3.2, 0.15), wall)
	_wall(built, Vector3(28.75, 1.6, -1.5), Vector3(2.5, 3.2, 0.15), wall)
	_wall(built, Vector3(27, 2.7, -1.5), Vector3(1, 1, 0.15), wall)
	for x in [9.0, 15.0, 21.0]:
		for z in [-1.43, 1.43]:
			_wall(built, Vector3(x, 1.1, z), Vector3(1, 2.2, 0.09), Color(0.85, 0.42, 0.36))
	_wall(built, Vector3(21, 1.6, -5.7), Vector3(0.15, 3.2, 8), wall)
	_wall(built, Vector3(33, 1.6, -5.7), Vector3(0.15, 3.2, 8), wall)
	_wall(built, Vector3(27, 1.6, -9.7), Vector3(12, 3.2, 0.15), wall)
	# The room's south face is shared with the pierced hall wall, never duplicated.
	var stopped := PackedVector3Array()
	_segment(stopped, Vector3(15, 0, 2.6), Vector3(15, 0, 7))
	_stroke(built, stopped, HAZARD)
	var extension := Node3D.new()
	extension.name = "FUTURE ONLY: x15 south leaf needs wall piercing; no traversable connection"
	add_child(extension)
	extension_node = extension
	_box(extension, Vector3(11, 0, 10), Vector3(19, 3.2, 14), Color(0.60, 0.64, 0.72, 0.6))

func _build_routes() -> void:
	for edge: Dictionary in atlas.routes.edges:
		if edge.status != "future" or edge["from"] == "leaf_15_south":
			continue
		var a: Dictionary = route_nodes[edge["from"]]
		var b: Dictionary = route_nodes[edge["to"]]
		var first := _position(facilities[a.facility_ref]) if a.has("facility_ref") else _position(a)
		var last := _position(facilities[b.facility_ref]) if b.has("facility_ref") else _position(b)
		if first.is_equal_approx(last):
			continue
		var node := Node3D.new()
		node.name = "FUTURE ONLY: %s > %s" % [edge["from"], edge["to"]]
		add_child(node)
		var points := PackedVector3Array()
		_segment(points, first + Vector3.UP * 1.5, last + Vector3.UP * 1.5)
		_stroke(node, points, Color(0.56, 0.68, 0.80, 0.65))
		route_nodes_3d.append(node)

func _build_power() -> void:
	# The local generator and emergency bus share one atlas coordinate; no room feeds are mapped.
	var main := Node3D.new()
	main.name = "PROPOSED main: plant > isolation > distribution > sectional breakers | D27 near M-drive"
	add_child(main)
	var main_points := PackedVector3Array()
	for x in [700.0, 725.0, 750.0]:
		_segment(main_points, Vector3(x, -67, 0), Vector3(x + 20, -67, 0))
	_stroke(main, main_points, Color("e7c262"))
	power_nodes_3d.append(main)
	var local := Node3D.new()
	local.name = "BUILT D14 local backup > local emergency bus (co-located); transfer to ship network sealed"
	add_child(local)
	var local_points := PackedVector3Array()
	var source := Vector3(27, 2.6, -5.7)
	_segment(local_points, source + Vector3.LEFT * 2.0, source + Vector3.RIGHT * 2.0)
	_segment(local_points, source + Vector3.FORWARD * 2.0, source + Vector3.BACK * 2.0)
	_stroke(local, local_points, Color("f0ca7a"))
	power_nodes_3d.append(local)

func _text(parent: Node, content: String, size: int, color: Color = Color("d5e6ef")) -> Label:
	var label := Label.new()
	label.text = content
	label.add_theme_font_size_override("font_size", size)
	label.add_theme_color_override("font_color", color)
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	parent.add_child(label)
	return label

func _build_ui() -> void:
	var canvas := CanvasLayer.new()
	add_child(canvas)
	var panel := PanelContainer.new()
	panel.set_anchors_and_offsets_preset(Control.PRESET_LEFT_WIDE)
	var panel_style := StyleBoxFlat.new()
	panel_style.bg_color = Color("172535")
	panel_style.set_content_margin_all(8.0)
	panel.add_theme_stylebox_override("panel", panel_style)
	panel.custom_minimum_size.x = 400
	panel.offset_right = 412
	canvas.add_child(panel)
	var scroll := ScrollContainer.new()
	panel.add_child(scroll)
	var column := VBoxContainer.new()
	column.custom_minimum_size.x = 385
	column.add_theme_constant_override("separation", 8)
	scroll.add_child(column)
	_text(column, "PROPOSED SHIP PLANNING ATLAS", 21, Color("f4d18b"))
	_text(column, "OUT-OF-WORLD DESIGN • meters\nX: bow − / aft +   Y: up +\nZ: port − / starboard +", 15)
	_text(column, "Hull cage = proposed exterior-compatible guide: tapered bow (X−), broad aft (X+). Not measured image tracing. Colored bins = diagrammatic indexing, NOT built rooms or hull occupancy.", 15, Color("e9c893"))
	deck_choice = OptionButton.new()
	deck_choice.add_item("OVERVIEW • D01–D30")
	for deck in range(1, 31):
		deck_choice.add_item("D%02d   floor Y = %.1f m" % [deck, _floor(deck)])
	deck_choice.item_selected.connect(_on_deck_selected)
	column.add_child(deck_choice)
	deck_readout = _text(column, "", 15)
	var row := HBoxContainer.new()
	column.add_child(row)
	for side: String in ["port", "core", "starboard"]:
		var toggle := CheckButton.new()
		toggle.text = side.capitalize()
		toggle.button_pressed = true
		toggle.toggled.connect(_on_side_toggled.bind(side))
		row.add_child(toggle)
		side_toggles[side] = toggle
	var reset := Button.new()
	reset.text = "Reset overview (R)"
	reset.pressed.connect(_reset)
	column.add_child(reset)
	_text(column, "Drag: orbit  |  Shift + drag: pan  |  Wheel: zoom\nR: reset  |  [ / ]: previous / next deck\n0: overview  |  D: focus built D14", 14, Color("9dbacc"))
	_text(column, "FACILITIES • search / click to focus", 16, Color("f4d18b"))
	search = LineEdit.new()
	search.placeholder_text = "Search id, kind, deck, status (%d facilities)" % atlas.facilities.size()
	search.text_changed.connect(_refresh_list)
	column.add_child(search)
	facility_list = ItemList.new()
	facility_list.custom_minimum_size.y = 190
	facility_list.item_selected.connect(_on_facility_selected)
	column.add_child(facility_list)
	detail = _text(column, "Select a facility for coordinates and provenance.", 14)
	_text(column, "DISTRICTS • 105 diagrammatic bins • search / click", 16, Color("f4d18b"))
	district_search = LineEdit.new()
	district_search.placeholder_text = "Bridge, staterooms, engineering, group, sector..."
	district_search.text_changed.connect(_refresh_districts)
	column.add_child(district_search)
	district_count = _text(column, "", 13)
	district_list = ItemList.new()
	district_list.custom_minimum_size.y = 230
	district_list.item_selected.connect(_on_district_selected)
	column.add_child(district_list)
	district_detail = _text(column, "Select a district to inspect its proposed bin.", 14)
	_text(column, "BIN COLORS • function tags (mixed bins use a representative tag)", 14, Color("f4d18b"))
	for category: String in FUNCTION_COLORS:
		_text(column, "■  " + category, 14, FUNCTION_COLORS[category])
	_text(column, "Deck groups: D01–04 / 05–08 / 09–12 / 13–16 / 17–20 / 21–25 / 26–30. Filter with the deck selector; bin colors do not encode decks.\nFacility glyphs scale for overview; bounds and D14 walls stay in meters. Green = built, blue = proposed, red = sealed radiation.\nPods: 7 built D14 + 2 proposed D22. Four shafts; two independent future spines.", 14)
	route_toggle = CheckButton.new()
	route_toggle.text = "Proposed route overlay (no built/future link)"
	route_toggle.button_pressed = true
	route_toggle.toggled.connect(_on_overlay_toggled)
	column.add_child(route_toggle)
	power_toggle = CheckButton.new()
	power_toggle.text = "Power topology"
	power_toggle.button_pressed = true
	power_toggle.toggled.connect(_on_overlay_toggled)
	column.add_child(power_toggle)
	_text(column, "Main: (+700, −71.5, 0), D27 near M-drive\nplant → isolation → distribution → breakers\nBackup: (27, 0, −5.7), D14 local bus at source\nNo bay or hall feed mapped. Ship transfer SEALED.", 14, Color("f0d095"))
	_text(column, "D14 built geometry is at true coordinates and scale. Hatch and power doorway are pierced; side leaves and x=30 endcap remain blocked. The x=15 south extension requires future construction.", 14, Color("e9c893"))
	_refresh_list("")
	_refresh_districts("")

func _refresh_districts(query: String) -> void:
	district_list.clear()
	shown_districts.clear()
	var matches := 0
	for item: Dictionary in atlas.grid.districts:
		var category := _function_category(item)
		var searchable := "%s %s %s sector %d %s %s %s %s" % [item.id, item.group, item.side, int(item.sector), item.category, category, ", ".join(item.functions), item.status]
		if not query.is_empty() and not searchable.to_lower().contains(query.strip_edges().to_lower()):
			continue
		matches += 1
		if shown_districts.size() < RESULT_LIMIT:
			shown_districts.append(item.id)
			var decks: Array = item.deck_range
			var x: Array = item.diagrammatic_x
			var z: Array = item.diagrammatic_z
			var caption := "%s | %s | D%02d–D%02d | %s" % [item.id, ", ".join(item.functions), int(decks[0]), int(decks[1]), item.status]
			district_list.add_item(caption)
			var list_index := shown_districts.size() - 1
			district_list.set_item_tooltip(list_index, "%s | %s\n%s | sector %d | %s | %s\nX %.0f..%.0f m | Z %.0f..%.0f m" % [caption, category, item.group, int(item.sector), item.side, item.category, float(x[0]), float(x[1]), float(z[0]), float(z[1])])
			district_list.set_item_custom_fg_color(list_index, FUNCTION_COLORS[category])
	district_count.text = "%d matches • showing first %d. Refine search to see more." % [matches, shown_districts.size()]

func _on_district_selected(index: int) -> void:
	var item: Dictionary = districts[shown_districts[index]]
	selected_district = item.id
	selected_id = ""
	var decks: Array = item.deck_range
	selected_deck = int(decks[0])
	deck_choice.select(selected_deck)
	if not sides[item.side]:
		side_toggles[item.side].button_pressed = true
	orbit_target = _district_center(item)
	orbit_distance = 850.0
	orbit_pitch = 0.55
	var x: Array = item.diagrammatic_x
	var z: Array = item.diagrammatic_z
	district_detail.text = "%s • %s\nFunctions: %s\nGroup %s • sector %d • %s\nD%02d–D%02d • viewing D%02d\nX %.0f..%.0f m • Z %.0f..%.0f m\nSource: %s\nDiagrammatic bin, not confirmed room/hull geometry." % [item.id, _function_category(item), ", ".join(item.functions), item.group, int(item.sector), item.side, int(decks[0]), int(decks[1]), selected_deck, float(x[0]), float(x[1]), float(z[0]), float(z[1]), item.status]
	_apply_filters()
	_update_camera()

func _refresh_list(query: String) -> void:
	facility_list.clear()
	shown_facilities.clear()
	for item: Dictionary in atlas.facilities:
		var caption := "%s  |  %s  |  %s  |  %s" % [item.id, item.kind, item.deck, item.status]
		if query.is_empty() or caption.to_lower().contains(query.to_lower()):
			shown_facilities.append(item.id)
			facility_list.add_item(caption)
	assert(shown_facilities.size() <= atlas.facilities.size(), "Facility list exceeds atlas data")

func _on_facility_selected(index: int) -> void:
	selected_id = shown_facilities[index]
	selected_district = ""
	var item: Dictionary = facilities[selected_id]
	var side: String = String(item.district).get_slice("-", 3)
	if not sides[side]:
		side_toggles[side].button_pressed = true
	selected_deck = int(String(item.deck).substr(1))
	deck_choice.select(selected_deck)
	var p := _position(item)
	orbit_target = p
	orbit_distance = 85.0 if item.status == "built" else (220.0 if item.has("bounds") else 160.0)
	orbit_pitch = 0.50
	_update_camera()
	var extras := ""
	if item.has("radiation_source"):
		extras = "\nSEALED region; radiation origin unknown."
	if item.id == "backup":
		extras = "\nLocal D14 backup only. Transfer to ship-wide distribution SEALED."
	if item.kind == "decorative solid side leaf":
		extras = "\nIMPASSABLE. Wall not pierced."
	detail.text = "%s • %s\n%s  %s\nXYZ (%.2f, %.2f, %.2f) m\nDistrict: %s\nSource: %s%s" % [item.id, item.kind, item.deck, item.status.to_upper(), p.x, p.y, p.z, item.district, item.source, extras]
	_apply_filters()
	_update_camera()

func _on_deck_selected(index: int) -> void:
	selected_deck = index
	selected_id = ""
	selected_district = ""
	district_detail.text = "Select a district to inspect its proposed bin."
	_apply_filters()

func _on_side_toggled(pressed: bool, side: String) -> void:
	sides[side] = pressed
	_apply_filters()

func _on_overlay_toggled(_pressed: bool) -> void:
	_apply_filters()

func _apply_filters() -> void:
	var overview := selected_deck == 0
	hull_cage.visible = overview
	for node: Node3D in district_nodes:
		var visible_bin: bool = overview or (selected_district != "" and node.get_meta("id") == selected_district) or (selected_id == "" and selected_district == "" and selected_deck != 14 and selected_deck >= int(node.get_meta("first")) and selected_deck <= int(node.get_meta("last")))
		node.visible = sides[node.get_meta("side")] and visible_bin
		district_highlights[node.get_meta("id")].visible = node.get_meta("id") == selected_district
	for node: Node3D in floor_nodes:
		node.visible = overview
	opening_node.visible = selected_district == "" and sides.core and (overview or selected_deck == 14)
	extension_node.visible = selected_district == "" and sides.core and sides.starboard and (overview or selected_deck == 14)
	for item: Dictionary in atlas.facilities:
		var deck: int = int(String(item.deck).substr(1))
		var side: String = String(item.district).get_slice("-", 3)
		var in_deck := selected_deck == 0 or selected_deck == deck
		if item.has("deck_range"):
			var span: Array = item.deck_range
			in_deck = selected_deck == 0 or (selected_deck >= int(span[0]) and selected_deck <= int(span[1]))
		var in_focus: bool = selected_id == "" or item.id == selected_id
		if selected_id != "" and facilities[selected_id].status == "built" and selected_deck == 14:
			in_focus = item.status == "built" and deck == 14
		elif selected_id == "r2":
			in_focus = item.id == "r2" or item.get("radiation_region", "") == "r2" or item.get("room", "") == "remote_room"
		elif selected_district != "":
			in_focus = false
		facility_nodes[item.id].visible = sides[side] and in_deck and (overview or in_focus)
		facility_labels[item.id].visible = item.id == selected_id and overview and facility_nodes[item.id].visible
		facility_highlights[item.id].visible = item.id == selected_id and not overview
	for node: Node3D in route_nodes_3d:
		node.visible = overview and route_toggle.button_pressed and sides.core
	power_nodes_3d[0].visible = overview and power_toggle.button_pressed and sides.core
	power_nodes_3d[1].visible = overview and power_toggle.button_pressed and sides.core
	deck_readout.text = "All 30 floor datums; district group envelopes" if overview else "D%02d • floor Y = %.1f m • local focus (ship guides hidden)" % [selected_deck, _floor(selected_deck)]
	_update_glyphs()

func _reset() -> void:
	selected_deck = 0
	selected_id = ""
	selected_district = ""
	deck_choice.select(0)
	orbit_target = Vector3(-410, 0, 0)
	orbit_distance = 1950.0
	orbit_yaw = 0.35
	orbit_pitch = 0.55
	detail.text = "Select a facility for coordinates and provenance."
	district_detail.text = "Select a district to inspect its proposed bin."
	_apply_filters()
	_update_camera()

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT):
		var motion: InputEventMouseMotion = event
		if Input.is_key_pressed(KEY_SHIFT):
			var basis := camera.global_transform.basis
			var step := orbit_distance * 0.0009
			orbit_target += (basis.x * -motion.relative.x + basis.y * motion.relative.y) * step
		else:
			orbit_yaw -= motion.relative.x * 0.005
			orbit_pitch = clampf(orbit_pitch + motion.relative.y * 0.005, -1.48, 1.48)
		_update_camera()
	elif event is InputEventMouseButton and event.pressed:
		var mouse: InputEventMouseButton = event
		if mouse.button_index == MOUSE_BUTTON_WHEEL_UP or mouse.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			orbit_distance = clampf(orbit_distance * (0.83 if mouse.button_index == MOUSE_BUTTON_WHEEL_UP else 1.20), 7.0, 6500.0)
			_update_camera()
	elif event is InputEventKey and event.pressed and not event.echo:
		var key: InputEventKey = event
		if key.keycode == KEY_R or key.keycode == KEY_0:
			_reset()
		elif key.keycode == KEY_D:
			selected_id = ""
			selected_district = ""
			detail.text = "Select a facility for coordinates and provenance."
			district_detail.text = "Select a district to inspect its proposed bin."
			selected_deck = 14
			deck_choice.select(14)
			orbit_target = Vector3(12, 0, -2)
			orbit_distance = 85.0
			_apply_filters()
			_update_camera()
		elif key.keycode == KEY_BRACKETLEFT or key.keycode == KEY_BRACKETRIGHT:
			selected_deck = clampi(selected_deck + (-1 if key.keycode == KEY_BRACKETLEFT else 1), 0, 30)
			deck_choice.select(selected_deck)
			_apply_filters()
