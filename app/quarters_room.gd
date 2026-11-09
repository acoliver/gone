class_name QuartersRoom
extends Node3D

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
	var screen := MeshInstance3D.new()
	screen.name = "ConsoleScreen"
	var quad := QuadMesh.new()
	quad.size = Vector2(0.96, 0.48)
	screen.mesh = quad
	screen.transform = QuartersLayout.console_frame()
	screen.position += Vector3(0.015, 0.38, 0)
	var finish := StandardMaterial3D.new()
	finish.albedo_color = Color(0.05, 0.18, 0.24)
	finish.emission_enabled = true
	finish.emission = Color(0.12, 0.45, 0.62)
	finish.emission_energy_multiplier = 0.8
	screen.material_override = finish
	state.add_child(screen)
	screens.append(screen)
	var label := Label3D.new()
	label.name = "PlaceholderText"
	label.position.z = 0.008
	label.pixel_size = 0.0005
	label.font_size = 32
	label.outline_size = 0
	label.modulate = Color(0.65, 0.85, 0.95)
	screen.add_child(label)
	screen_labels.append(label)
	if state == remembered:
		corruption = Node3D.new()
		corruption.name = "CorruptedVideoBlocks"
		screen.add_child(corruption)
		for index: int in range(12):
			var block := MeshInstance3D.new()
			var mesh := QuadMesh.new()
			mesh.size = Vector2(0.20, 0.085)
			block.mesh = mesh
			block.position = Vector3((index % 4 - 1.5) * 0.22, (index / 4 - 1) * 0.13, 0.012)
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
	for x: float in [2.9, 5.1]:
		for state: Node3D in [remembered, present]:
			var finish := warm if state == remembered else StandardMaterial3D.new()
			var lamp := QuartersFurnishings.box("Standin_bedside_lamp", AABB(Vector3(x - 0.06, 0.6, 5.69), Vector3(0.12, 0.22, 0.12)), finish)
			lamp.layers = Lighting.QUARTERS_MASK
			state.add_child(lamp)
		var lamp := OmniLight3D.new()
		lamp.name = "BedsideLamp"
		lamp.position = QuartersLayout.to_world(Vector3(x, 0.85, 5.7))
		lamp.light_color = Color(1.0, 0.64, 0.31)
		lamp.light_energy = 0.35
		lamp.omni_range = 2.0
		lamp.light_cull_mask = Lighting.QUARTERS_MASK
		remembered.add_child(lamp)

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
	var text := _wrapped(_game.quarters.screen_text())
	for label: Label3D in screen_labels:
		if label.text != text: label.text = text
	corruption.visible = _game.quarters.state == QuartersMemory.State.PLAYING and _game.quarters.elapsed < QuartersMemory.CORRUPT_TICKS
	if corruption.visible:
		for index: int in range(corruption.get_child_count()):
			var block := corruption.get_child(index) as MeshInstance3D
			var shade := 0.01 + float((index * 19 + _game.quarters.elapsed / 4 * 7) % 13) * 0.022
			block.material_override.albedo_color = Color(shade, shade * 1.12, shade * 1.2)

static func _wrapped(text: String) -> String:
	var lines := PackedStringArray()
	for paragraph: String in text.split("\n"):
		var line := ""
		for word: String in paragraph.split(" "):
			if line.length() + word.length() > 64:
				lines.append(line)
				line = ""
			line += ("" if line == "" else " ") + word
		lines.append(line)
	return "\n".join(lines)
