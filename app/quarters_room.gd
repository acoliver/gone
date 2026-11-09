class_name QuartersRoom
extends Node3D

const TEXT_WIDTH_PX := 1024.0
const TEXT_FONT_SIZE := 32
const CORRUPTION_COLORS: Array[Color] = [Color(0.004, 0.008, 0.012), Color(0.02, 0.10, 0.14), Color(0.12, 0.72, 0.82), Color(0.82, 0.94, 1.0), Color(0.08, 0.28, 0.34)]

var remembered: Node3D
var present: Node3D
var screens: Array[MeshInstance3D] = []
var screen_labels: Array[Label3D] = []
var corruption: Node3D
var white_lights: Array[OmniLight3D] = []
var entrance_bounces: Array[OmniLight3D] = []
var white_finish: StandardMaterial3D
var white_fade: Intensity.FixtureFade
var _game: Game
var _screen_text := ""

static func build(game: Game) -> QuartersRoom:
	var room := QuartersRoom.new()
	room._game = game
	room.name = "States"
	room.remembered = QuartersFurnishings.build(&"as_built")
	room.present = QuartersFurnishings.build(&"aged")
	for state: Node3D in [room.remembered, room.present]:
		room.add_child(state)
		room._screen(state)
		var probe := ReflectionProbe.new()
		probe.name = "QuartersReflection"
		probe.position = QuartersLayout.bounds().get_center()
		probe.size = QuartersLayout.bounds().size
		probe.cull_mask = Lighting.QUARTERS_MASK
		probe.box_projection = true
		probe.interior = true
		state.add_child(probe)
		Lighting.mesh_layers(state, Lighting.QUARTERS_MASK)
	room._lights()
	room.process_frame()
	return room

func _screen(state: Node3D) -> void:
	var console := state.get_node("Placement_console/console")
	var screen := console.find_child("Display", true, false) as MeshInstance3D
	var bounds := screen.get_aabb()
	var finish := (QuartersProps.interim_material(&"Display", &"as_built" if state == remembered else &"aged") as StandardMaterial3D).duplicate() as StandardMaterial3D
	finish.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	finish.albedo_color = Color(0.004, 0.012, 0.018)
	finish.emission_enabled = true
	finish.emission = Color(0.008, 0.035, 0.05)
	finish.emission_energy_multiplier = 0.4
	screen.material_override = finish
	screens.append(screen)
	var label := Label3D.new()
	label.name = "PlaceholderText"
	label.position = bounds.get_center() + Vector3(0, 0, bounds.size.z / 2 + 0.0017)
	label.pixel_size = bounds.size.x / TEXT_WIDTH_PX
	label.font_size = TEXT_FONT_SIZE
	label.font = ThemeDB.fallback_font
	label.outline_size = 0
	label.shaded = false
	label.modulate = Color(0.86, 0.98, 1.0)
	screen.add_child(label)
	screen_labels.append(label)
	var scanlines := MeshInstance3D.new()
	scanlines.name = "Scanlines"
	var raster := QuadMesh.new()
	raster.size = Vector2(bounds.size.x, bounds.size.y)
	scanlines.mesh = raster
	scanlines.position = bounds.get_center() + Vector3(0, 0, bounds.size.z / 2 + 0.0003)
	var scan_finish := ShaderMaterial.new()
	scan_finish.shader = preload("res://app/shaders/quarters_scanlines.gdshader")
	scanlines.material_override = scan_finish
	screen.add_child(scanlines)
	if state == remembered:
		corruption = Node3D.new()
		corruption.name = "CorruptedVideoBlocks"
		corruption.position = bounds.get_center() + Vector3(0, 0, bounds.size.z / 2 + 0.0012)
		screen.add_child(corruption)
		for index: int in range(12):
			var block := MeshInstance3D.new()
			var mesh := QuadMesh.new()
			mesh.size = Vector2(bounds.size.x / 4.5, bounds.size.y / 4.0)
			block.mesh = mesh
			block.position = Vector3((index % 4 - 1.5) * bounds.size.x / 4.2, (index / 4 - 1) * bounds.size.y / 3.2, 0)
			var material := StandardMaterial3D.new()
			material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
			block.material_override = material
			corruption.add_child(block)

func _lights() -> void:
	# Both entrance-side storage banks face away from the ceiling keys.
	# Local diffuse bounce lights their solid panels without ambient or D14 changes.
	for x: float in [0.9, 7.1]:
		var bounce := OmniLight3D.new()
		bounce.name = "EntranceStorageBounce" if x < 4 else "EntranceStorageBounceRight"
		bounce.position = QuartersLayout.to_world(Vector3(x, 2.6, 0.05))
		bounce.light_color = Lighting.REGULAR_WHITE
		bounce.omni_range = 3.2
		bounce.light_cull_mask = Lighting.QUARTERS_MASK
		bounce.light_specular = 0.0
		add_child(bounce)
		entrance_bounces.append(bounce)
	white_fade = Intensity.FixtureFade.holding(1.0 if _game.power_active else 0.0).fade
	white_finish = CeilingFixture.glass_material(1.0 if _game.power_active else 0.0)
	var warm := _lens(Color(1.0, 0.69, 0.38))
	for x: float in [2.0, 6.0]:
		for z: float in [1.5, 4.5]:
			var position := QuartersLayout.to_world(Vector3(x, 3.05, z))
			for state: Node3D in [remembered, present]:
				var finish := warm if state == remembered else white_finish
				var fixture := Node3D.new()
				fixture.position = position
				state.add_child(fixture)
				CeilingFixture.mount(fixture, QuartersLayout.FLOOR_Y + QuartersLayout.HEIGHT, Lighting.QUARTERS_MASK, finish)
				var lamp := OmniLight3D.new()
				lamp.position = position - Vector3(0, 0.10, 0)
				lamp.omni_range = Lighting.REGULAR_RANGE
				lamp.light_color = Color(1.0, 0.73, 0.46) if state == remembered else Lighting.REGULAR_WHITE
				lamp.light_energy = 3.2 if state == remembered else 0.0
				lamp.light_cull_mask = Lighting.QUARTERS_MASK
				state.add_child(lamp)
				if state == present: white_lights.append(lamp)
	for id: String in ["bedside_l", "bedside_r"]:
		var asset := remembered.get_node("Placement_" + id + "/bedside")
		var lens := asset.find_child("LampLens", true, false) as MeshInstance3D
		var lamp := OmniLight3D.new()
		lamp.name = "BedsideLamp"
		lamp.position = lens.get_aabb().get_center() - Vector3(0, 0.008, 0)
		lamp.light_color = Color(1.0, 0.64, 0.31)
		lamp.light_energy = 0.35
		lamp.omni_range = 2.0
		lamp.light_cull_mask = Lighting.QUARTERS_MASK
		lens.add_child(lamp)

static func _lens(color: Color) -> StandardMaterial3D:
	var finish := StandardMaterial3D.new()
	finish.albedo_color = color
	finish.emission_enabled = true
	finish.emission = color
	finish.emission_energy_multiplier = Lighting.REGULAR_EMISSIVE
	return finish

func process_frame() -> void:
	remembered.visible = _game.quarters.remembered()
	present.visible = not remembered.visible
	var white := 1.0 if _game.power_active else 0.0
	if white_fade.target() != white: white_fade.retarget(white, 30)
	white_fade.tick()
	var level := white_fade.intensity()
	for bounce: OmniLight3D in entrance_bounces: bounce.light_energy = Lighting.regular_energy() * 0.35 * level
	for lamp: OmniLight3D in white_lights: lamp.light_energy = Lighting.regular_energy() * level
	white_finish.emission = Lighting.REGULAR_WHITE * Lighting.REGULAR_EMISSIVE * level
	var source := _game.quarters.screen_text()
	if source != _screen_text:
		_screen_text = source
		var text := _wrapped(source)
		for label: Label3D in screen_labels: label.text = text
	corruption.visible = _game.quarters.state == QuartersMemory.State.PLAYING and _game.quarters.elapsed < QuartersMemory.CORRUPT_TICKS
	if corruption.visible:
		for index: int in range(corruption.get_child_count()):
			var block := corruption.get_child(index) as MeshInstance3D
			block.material_override.albedo_color = CORRUPTION_COLORS[(index * 3 + _game.quarters.elapsed / 4) % CORRUPTION_COLORS.size()]

static func _wrapped(text: String) -> String:
	var lines := PackedStringArray()
	for paragraph: String in text.split("\n"):
		var line := ""
		for word: String in paragraph.split(" "):
			var candidate := line + ("" if line == "" else " ") + word
			var width := ThemeDB.fallback_font.get_string_size(candidate, HORIZONTAL_ALIGNMENT_LEFT, -1, TEXT_FONT_SIZE).x
			if width > TEXT_WIDTH_PX * 0.92:
				lines.append(line)
				line = word
			else:
				line = candidate
		lines.append(line)
	return "\n".join(lines)
