extends RefCounted

var records: Array[Dictionary] = []
var spaces: Dictionary = {}
var samples: Dictionary = {}
var circuit: String
func collect_ship() -> Dictionary:
	for white: bool in [false, true]:
		circuit = "secondary-white" if white else "emergency"
		var game := Game.new(91)
		game.light_hallway()
		if white: game.press_console()
		var world := Node3D.new()
		var scene := ShipScene.build_into(world, game)
		scene.hazards.auto_bursts = false
		scene.prepare_near(Vector3(10, 0, 0))
		scene.prepare_near(Vector3(26, 0, 0))
		var opening := {ShipLayout.BAY_ID: scene.bay_root, &"D14-S-041": scene.hallway, ShipLayout.POWER_ID: scene.power_room}
		for child: Node in world.get_children():
			if child is ShipConnector or child is ShipSection: opening[StringName(child.name)] = child
		for id: StringName in opening:
			_collect(opening[id], id)
		var lights := world.find_children("*", "Light3D", true, false)
		for id: StringName in opening:
			_measure(id, game.layout, lights)
			if id in game.layout.connector_ids(): _measure_adjacent(game.layout, game.layout.connector(id), lights)
		for id: StringName in game.layout.connector_ids():
			var spec := game.layout.connector(id)
			if spec.deck_number() == 14: continue
			var remote := scene.build_remote(spec)
			_collect(remote, id)
			var remote_lights := remote.find_children("*", "Light3D", true, false)
			_measure(id, game.layout, remote_lights)
			_measure_adjacent(game.layout, spec, remote_lights)
			scene.remove_remote(spec, remote)
		for spec: ShipLayout.Spec in game.layout.records():
			if spec is ShipLayout.LiftSpec:
				spaces[spec.id()] = {"deck": spec.deck_number(), "type": "lift", "note": "closed lift shell; receives only its connector circuit"}
			elif spec is ShipLayout.LadderWellSpec:
				var shaft := LadderShaft.build(game.layout, spec)
				_collect(shaft, spec.id())
				for deck: int in range(1, 31):
					var id := "%s/D%02d" % [spec.id(), deck]
					spaces[id] = {"deck": deck, "type": "ladder landing"}
				shaft.free()
		world.free()
	return {"spaces": spaces, "lights_and_emissives": records, "illuminance": samples}

func _visible(node: Node3D) -> bool:
	var current: Node = node
	while current is Node3D:
		if not current.visible: return false
		current = current.get_parent()
	return true

func _collect(node: Node, owner_id: StringName) -> void:
	if node is Light3D:
		var fixture := "NONE"
		var category := "c"
		var gap := INF
		var root_node: Node = node
		while root_node.get_parent() != null: root_node = root_node.get_parent()
		if node.has_meta(&"fixture_emitter"):
			var emitter: MeshInstance3D = node.get_meta(&"fixture_emitter")
			var point: Vector3 = node.get_meta(&"emitter_point", emitter.mesh.get_aabb().get_center())
			gap = Surfaces.world_frame(node).origin.distance_to(Surfaces.world_frame(emitter) * point)
			fixture = String(root_node.get_path_to(emitter))
			category = "a"
		else:
			for mesh: MeshInstance3D in root_node.find_children("*", "MeshInstance3D", true, false):
				if not _visible(mesh): continue
				if mesh.get_meta(&"lamp_circuit", "") == "": continue
				var distance := Surfaces.world_frame(node).origin.distance_to(Surfaces.world_frame(mesh) * mesh.mesh.get_aabb().get_center())
				if distance < gap and distance < 0.3:
					gap = distance
					fixture = String(root_node.get_path_to(mesh))
					category = "b" if mesh.mesh is BoxMesh else "a"
		var light: Light3D = node
		var radius: float = light.omni_range if light is OmniLight3D else (light.spot_range if light is SpotLight3D else INF)
		var decay: float = light.omni_attenuation if light is OmniLight3D else (light.spot_attenuation if light is SpotLight3D else 0.0)
		records.append({"owner": owner_id, "circuit_state": circuit, "kind": "light", "path": String(root_node.get_path_to(node)), "type": node.get_class(), "category": category, "fixture": fixture, "lens_gap_m": gap if gap != INF else -1, "color": _rgb(light.light_color), "energy": light.light_energy, "range": radius, "attenuation": decay, "mask": light.light_cull_mask, "position": _vec(Surfaces.world_frame(node).origin), "fixture_valid": _fixture_error(light) == "", "fixture_error": _fixture_error(light)})
	elif node is MeshInstance3D and node.mesh != null:
		for surface: int in range(node.mesh.get_surface_count()):
			var material: Material = node.get_active_material(surface)
			var emission := Color.BLACK
			var enabled := false
			if material is BaseMaterial3D:
				enabled = material.emission_enabled
				emission = material.emission * material.emission_energy_multiplier
			elif material is ShaderMaterial:
				var value: Variant = material.get_shader_parameter("emission_tint")
				if value is Color:
					emission = value
					enabled = true
			if enabled:
				records.append({"owner": owner_id, "circuit_state": circuit, "kind": "emissive", "path": String(node.name), "surface": surface, "category": "fixture" if node.has_meta(&"lamp_circuit") else "d", "visible": _visible(node), "color": _rgb(emission), "energy": "material emission, no GI", "range": 0, "fixture": String(node.get_parent().name) if node.has_meta(&"lamp_circuit") else "NONE"})
	elif node is GPUParticles3D:
		records.append({"owner": owner_id, "circuit_state": circuit, "kind": "emissive particles", "path": String(node.name), "category": "d", "fixture": "NONE", "color": "spark ember / smoke emission_tint", "energy": "particle material", "range": 0})
	for child: Node in node.get_children(): _collect(child, owner_id)

func _measure(id: StringName, layout: ShipLayout, lights: Array[Node]) -> void:
	var bounds: AABB
	var frame := Transform3D.IDENTITY
	var mask := Lighting.architectural_mask(layout, id)
	if id == ShipLayout.BAY_ID:
		bounds = layout.bay().local_bounds()
		frame = layout.bay_to_world()
		mask |= Lighting.BAY_FILL_MASK
	elif id == ShipLayout.POWER_ID:
		bounds = layout.power_room().bounds()
		mask |= Lighting.POWER_FILL_MASK
	elif id in layout.connector_ids(): bounds = layout.connector(id).bounds()
	else: bounds = layout.section(id).bounds()
	spaces[id] = {"deck": 14 if id in [ShipLayout.BAY_ID, ShipLayout.POWER_ID] else String(id).substr(1, 2).to_int(), "type": "bay" if id == ShipLayout.BAY_ID else ("power" if id == ShipLayout.POWER_ID else ("connector" if id in layout.connector_ids() else "section"))}
	_measure_bounds(id, bounds, frame, mask, lights)

func _measure_bounds(id: String, bounds: AABB, frame: Transform3D, mask: int, lights: Array) -> void:
	var values: Array[float] = []
	var panels := [0.0, 0.0, 0.0]
	for face: int in range(6):
		var normal := Vector3.UP if face == 0 else (Vector3.DOWN if face == 1 else (Vector3.RIGHT if face == 2 else (Vector3.LEFT if face == 3 else (Vector3.BACK if face == 4 else Vector3.FORWARD))))
		for u: int in range(5):
			for v: int in range(3):
				var a := (u + 0.5) / 5.0
				var b := (v + 0.5) / 3.0
				var p := bounds.position
				if face < 2: p += Vector3(a * bounds.size.x, 0.05 if face == 0 else bounds.size.y - 0.05, b * bounds.size.z)
				elif face < 4: p += Vector3(0.05 if face == 2 else bounds.size.x - 0.05, b * bounds.size.y, a * bounds.size.z)
				else: p += Vector3(a * bounds.size.x, b * bounds.size.y, 0.05 if face == 4 else bounds.size.z - 0.05)
				p = frame * p
				var total := 0.0
				for light: Light3D in lights:
					total += incident(light, p, frame.basis * normal, mask)
				values.append(total)
				panels[face if face < 2 else 2] += total
	var sum := 0.0
	for value: float in values: sum += value
	samples[circuit + "/" + id] = {"total": sum, "floor": panels[0], "ceiling": panels[1], "walls": panels[2], "samples": values}

func _vec(v: Vector3) -> Array:
	return [v.x, v.y, v.z]

func _rgb(c: Color) -> Array:
	return [c.r, c.g, c.b]

func incident(light: Light3D, point: Vector3, normal: Vector3, mask: int) -> float:
	if not _visible(light) or (light.light_cull_mask & mask) == 0: return 0.0
	assert(light is OmniLight3D, "inventory currently contains only omni lights")
	var delta := Surfaces.world_frame(light).origin - point
	var d := delta.length()
	var fade := maxf(1.0 - pow(d / light.omni_range, 4), 0.0)
	var color := light.light_color.srgb_to_linear()
	var luminance := color.r * 0.2126 + color.g * 0.7152 + color.b * 0.0722
	return light.light_energy * luminance * fade * fade * pow(maxf(d, 0.0001), -light.omni_attenuation) * maxf(normal.dot(delta.normalized()), 0.0)

func _fixture_error(light: Light3D) -> String:
	if not light.has_meta(&"fixture_emitter") or not light.has_meta(&"fixture_housing"): return "no emitter/housing binding"
	var emitter: MeshInstance3D = light.get_meta(&"fixture_emitter")
	var housing: MeshInstance3D = light.get_meta(&"fixture_housing")
	if emitter == null or housing == null: return "no emitter/housing binding"
	if emitter == housing or not _visible(emitter) or not _visible(housing): return "emitter or housing is hidden"
	if emitter.mesh is BoxMesh or housing.mesh == null: return "bare box lens or missing housing"
	var material := emitter.get_active_material(0) as BaseMaterial3D
	if material == null or not material.emission_enabled: return "emitter has no emission material"
	var point := emitter.mesh.get_aabb().get_center()
	if light.has_meta(&"emitter_point"):
		point = light.get_meta(&"emitter_point")
		if emitter.name != "PodStrips": return "only extended pod belts use centreline samples"
		var closest := INF
		for path: Array[Vector3] in [PodStrips.FLANK_DOME, PodStrips.FLANK_TRAY]:
			for index: int in range(path.size() - 1):
				closest = minf(closest, point.distance_to(Geometry3D.get_closest_point_to_segment(point, path[index], path[index + 1])))
		if closest > 0.001: return "belt source is off its measured emitter centreline"
	var gap := Surfaces.world_frame(light).origin.distance_to(Surfaces.world_frame(emitter) * point)
	if gap > 0.01: return "source is %.6f m from emitter centre" % gap
	var housing_bounds := Surfaces.world_frame(housing) * housing.mesh.get_aabb()
	if not housing_bounds.grow(0.04).has_point(Surfaces.world_frame(emitter) * point): return "housing does not enclose the emitter"
	var source_root: Node = light
	while source_root.get_parent() != null: source_root = source_root.get_parent()
	if not source_root.is_ancestor_of(emitter) or not source_root.is_ancestor_of(housing): return "fixture is outside the source scene"
	return ""

func _measure_adjacent(layout: ShipLayout, spec: ShipLayout.ConnectorSpec, lights: Array) -> void:
	var mask := Lighting.space_mask(layout, spec.id())
	_measure_bounds(String(spec.lift_id()), layout.lift(spec.lift_id()).bounds(), Transform3D.IDENTITY, mask, lights)
	_measure_bounds("%s/D%02d" % [spec.well_id(), spec.deck_number()], layout.well(spec.well_id()).landing_bounds(spec.deck_number()), Transform3D.IDENTITY, mask, lights)
