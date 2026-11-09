class_name SectionPowerLighting
extends Node3D
## D16's corridor uses the opening hallway's switched red/white circuit.

var _game: Game
var _red: Intensity.FixtureFade
var _white: Intensity.FixtureFade
var _red_lights: Array[OmniLight3D] = []
var _red_lenses: Array[StandardMaterial3D] = []
var _white_lights: Array[OmniLight3D] = []
var _white_material: StandardMaterial3D

static func build(game: Game, spec: ShipLayout.SectionSpec, owner: ShipSection) -> SectionPowerLighting:
	var circuit := SectionPowerLighting.new()
	circuit.name = "PowerLighting"
	circuit._game = game
	var red := 1.0 if game.hallway_lit and not game.power_active else 0.0
	var white := 1.0 if game.power_active else 0.0
	circuit._red = Intensity.FixtureFade.holding(red).fade
	circuit._white = Intensity.FixtureFade.holding(white).fade
	for fixture: Node in owner.get_children():
		if not String(fixture.name).begins_with("EmergencyFixture"): continue
		for child: Node in fixture.get_children():
			if child is OmniLight3D: circuit._red_lights.append(child)
			if child is MeshInstance3D and child.name == &"Lens":
				circuit._red_lenses.append(child.material_override)
	circuit._white_material = CeilingFixture.glass_material(white)
	var mask := Lighting.space_mask(game.layout, spec.id())
	for frame: Transform3D in spec.regular_light_frames():
		var fixture := Node3D.new()
		fixture.name = "RegularStrip"
		fixture.transform = frame
		circuit.add_child(fixture)
		var light := OmniLight3D.new()
		light.position.y = -0.12
		light.light_color = Lighting.REGULAR_WHITE
		light.omni_range = Lighting.REGULAR_RANGE
		light.light_cull_mask = mask
		fixture.add_child(light)
		circuit._white_lights.append(light)
		CeilingFixture.mount(fixture, spec.bounds().end.y, mask, circuit._white_material)
	circuit._apply()
	return circuit

func process_frame() -> void:
	var red := 1.0 if _game.hallway_lit and not _game.power_active else 0.0
	var white := 1.0 if _game.power_active else 0.0
	if _red.target() != red: _red.retarget(red, Lighting.FIXTURE_SETTLE_TICKS)
	if _white.target() != white: _white.retarget(white, Lighting.FIXTURE_SETTLE_TICKS)
	_red.tick()
	_white.tick()
	_apply()

func _apply() -> void:
	for light: OmniLight3D in _red_lights:
		light.light_energy = Lighting.emergency_energy() * _red.intensity()
	for material: StandardMaterial3D in _red_lenses:
		material.emission = Lighting.emergency_emission(_red.intensity())
	for light: OmniLight3D in _white_lights:
		light.light_energy = Lighting.regular_energy() * _white.intensity()
	_white_material.emission = Lighting.REGULAR_WHITE * Lighting.REGULAR_EMISSIVE * _white.intensity()

func white_level() -> float:
	return _white.intensity()

func red_level() -> float:
	return _red.intensity()
