class_name SectionPowerLighting
extends Node3D
## D16's corridor uses the opening hallway's switched red/white circuit.

const REVEAL_BOUNCE_SHARE := 0.72

var _game: Game
var _red: Intensity.FixtureFade
var _white: Intensity.FixtureFade
var _red_lights: Array[OmniLight3D] = []
var _red_lenses: Array[StandardMaterial3D] = []
var _white_lights: Array[SpotLight3D] = []
var _white_material: StandardMaterial3D
var _fills: Array[Lighting.EmergencyFill] = []
var _white_end_fill: Lighting.RegularEndFill
var _reveal_regular: OmniLight3D
var _reveal_emergency: Lighting.EmergencyFill

static func build(game: Game, spec: ShipLayout.SectionSpec, owner: ShipSection) -> SectionPowerLighting:
	var circuit := SectionPowerLighting.new()
	circuit.name = "PowerLighting"
	circuit._game = game
	var red := 1.0 if game.hallway_lit and not game.power_active else 0.0
	var white := 1.0 if game.power_active else 0.0
	circuit._red = Intensity.FixtureFade.holding(red).fade
	circuit._white = Intensity.FixtureFade.holding(white).fade
	for fixture: Node in owner.get_children():
		var existing_key: OmniLight3D
		var lens: MeshInstance3D
		for child: Node in fixture.get_children():
			if child is OmniLight3D: existing_key = child
			if child is MeshInstance3D and child.get_meta(&"lamp_circuit", "") == "emergency": lens = child
		if existing_key == null: continue
		assert(lens != null, "D16 emergency fixture retains its caged lens")
		circuit._red_lenses.append(lens.material_override as StandardMaterial3D)
		var key := existing_key
		EmergencyFixtureProfile.apply(key, EmergencyFixtureProfile.HALL[circuit._red_lights.size()], red)
		key.light_cull_mask = Lighting.space_mask(game.layout, spec.id())
		circuit._red_lights.append(key)
	circuit._white_material = CeilingFixture.glass_material(white)
	var mask := Lighting.space_mask(game.layout, spec.id())
	for frame: Transform3D in spec.regular_light_frames():
		var fixture := Node3D.new()
		fixture.name = "RegularStrip"
		fixture.transform = frame
		circuit.add_child(fixture)
		var light := SpotLight3D.new()
		light.light_color = Lighting.REGULAR_WHITE
		light.spot_range = Lighting.REGULAR_RANGE
		light.light_cull_mask = mask
		fixture.add_child(light)
		circuit._white_lights.append(light)
		var lens := CeilingFixture.mount(fixture, spec.bounds().end.y, mask, circuit._white_material)
		FixtureEmitter.beam(light, lens, Surfaces.surface_frame(game.layout, spec.id(), &"CEILING"))
	for position: Vector3 in spec.emergency_fill_positions():
		var fill := Lighting.emergency_fill(position, red, Lighting.HALL_FILL_MASK)
		fill.name = "EmergencyFill%d" % circuit._fills.size()
		circuit.add_child(fill)
		circuit._fills.append(fill)
	var end := Lighting.emergency_fill(spec.emergency_end_fill_position(), red, Lighting.HALL_FILL_MASK, Lighting.EMERGENCY_END_FILL_SHARE, Lighting.EMERGENCY_END_FILL_COLOR)
	end.name = "EmergencyFillEnd"
	FixtureEmitter.wall_source(end, Surfaces.surface_frame(game.layout, spec.id(), &"STARBOARD"), "emergency", end.lens_material, 0.0)
	circuit.add_child(end)
	circuit._fills.append(end)
	circuit._white_end_fill = Lighting.regular_end_fill(spec.emergency_end_fill_position() - Vector3(0, 0, 2.6), white)
	FixtureEmitter.wall_source(circuit._white_end_fill, Surfaces.surface_frame(game.layout, spec.id(), &"PORT"), "white", circuit._white_end_fill.lens_material, PI)
	circuit.add_child(circuit._white_end_fill)
	var reveal := game.layout.door(QuartersLayout.DOOR).frame() * Vector3(0, 1.7, -0.45)
	circuit._reveal_regular = OmniLight3D.new()
	circuit._reveal_regular.name = "QuartersRevealRegular"
	circuit._reveal_regular.position = reveal
	circuit._reveal_regular.light_color = Lighting.REGULAR_WHITE
	circuit._reveal_emergency = Lighting.emergency_fill(reveal, red, Lighting.QUARTERS_MASK, Lighting.EMERGENCY_END_FILL_SHARE, Lighting.EMERGENCY_END_FILL_COLOR)
	circuit._reveal_emergency.name = "QuartersRevealEmergency"
	for bounce: OmniLight3D in [circuit._reveal_regular, circuit._reveal_emergency]:
		bounce.light_cull_mask = Lighting.QUARTERS_MASK
		bounce.omni_range = 1.8
		circuit.add_child(bounce)
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
		assert(light.has_meta(&"energy_share"), "applied emergency profile provides an energy share")
		light.light_energy = Lighting.emergency_energy() * float(light.get_meta(&"energy_share")) * _red.intensity()
	for material: StandardMaterial3D in _red_lenses:
		material.emission = Lighting.emergency_emission(_red.intensity())
	for fill: Lighting.EmergencyFill in _fills: fill.apply_level(_red.intensity())
	_white_end_fill.apply_level(_white.intensity())
	_reveal_regular.light_energy = Lighting.regular_energy() * REVEAL_BOUNCE_SHARE * _white.intensity()
	_reveal_emergency.apply_level(_red.intensity())
	for light: SpotLight3D in _white_lights:
		light.light_energy = Lighting.regular_energy() * _white.intensity()
	_white_material.emission = Lighting.REGULAR_WHITE * Lighting.REGULAR_EMISSIVE * _white.intensity()

func white_level() -> float:
	return _white.intensity()

func red_level() -> float:
	return _red.intensity()
