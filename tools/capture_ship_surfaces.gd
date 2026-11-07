extends SceneTree
## Production scene and circuits only. Neutral inspection belongs to capture_steel_probe.
## Run: godot --path . -s tools/capture_ship_surfaces.gd -- <output-dir>
const Protocol := preload("res://harness/protocol.gd")

static func capture_identity() -> Dictionary:
	var hashes: Dictionary = {}
	for file: String in Surfaces.IMAGES:
		for suffix: String in ["", ".import"]:
			var path := "assets/surfaces/steel/" + file + suffix
			hashes[path] = FileAccess.get_sha256("res://" + path)
	for path: String in ["app/surfaces.gd", "app/lighting.gd", "app/hallway.gd", "app/power_room.gd", "app/ship_scene.gd", "tools/capture_ship_surfaces.gd", "app/shaders/weathered_steel.gdshader", "app/shaders/steel_sampling.gdshaderinc", "app/shaders/weathered_tape.gdshader", "assets/surfaces/steel/manifest.json", "assets/surfaces/hatch/leaf-weather.png", "assets/surfaces/hatch/leaf-weather.png.import"]:
		hashes[path] = FileAccess.get_sha256("res://" + path)
	for path: String in [HatchAsset.SOURCE, HatchAsset.SOURCE + ".import", HatchAsset.MANIFEST]:
		hashes[path.trim_prefix("res://")] = FileAccess.get_sha256(path)
	for texture: Texture2D in Surfaces.hatch_runtime_textures().values():
		for suffix: String in ["", ".import"]:
			var path := texture.resource_path + suffix
			hashes[path.trim_prefix("res://")] = FileAccess.get_sha256(path)
	return {"app_hash": Protocol.app_hash(ProjectSettings.globalize_path("res://")), "resources": hashes, "lighting": {
		"key_color": [Lighting.EMERGENCY_RED.r, Lighting.EMERGENCY_RED.g, Lighting.EMERGENCY_RED.b],
		"fill_color": [Lighting.EMERGENCY_FILL_COLOR.r, Lighting.EMERGENCY_FILL_COLOR.g, Lighting.EMERGENCY_FILL_COLOR.b],
		"lens_base_color": str(Lighting.LENS_BASE_COLOR), "lens_emission": str(Lighting.emergency_emission(1.0)),
		"key_energy": Lighting.emergency_energy(), "fill_energy": Lighting.emergency_energy() * Lighting.EMERGENCY_FILL_SHARE,
		"fill_counts": [6, 8, 6],
		"key_range": Lighting.EMERGENCY_POOL_RANGE, "key_attenuation": Lighting.FIXTURE_ATTENUATION,
		"bay_key_range": Lighting.BAY_POOL_RANGE, "bay_key_attenuation": Lighting.BAY_POOL_ATTENUATION,
		"bay_hatch_range": Lighting.BAY_HATCH_POOL_RANGE, "bay_hatch_attenuation": Lighting.BAY_HATCH_ATTENUATION,
		"smoke_emission": [Lighting.SMOKE_EMISSION.r, Lighting.SMOKE_EMISSION.g, Lighting.SMOKE_EMISSION.b],
		"bay_fill_energy": Lighting.emergency_energy() * Lighting.EMERGENCY_BAY_FILL_SHARE,
		"end_fill_energy": Lighting.emergency_energy() * Lighting.EMERGENCY_END_FILL_SHARE,
		"end_fill_color": [Lighting.EMERGENCY_END_FILL_COLOR.r, Lighting.EMERGENCY_END_FILL_COLOR.g, Lighting.EMERGENCY_END_FILL_COLOR.b],
		"no_fill_multiplier": Lighting.EMERGENCY_NO_FILL_KEY_MULTIPLIER, "fill_range": Lighting.EMERGENCY_FILL_RANGE,
		"fill_ceiling_drop": ShipLayout.EMERGENCY_FILL_CEILING_DROP,
		"key_shadows": false, "fill_shadows": false,
		"fill_masks": [Lighting.BAY_FILL_MASK, Lighting.HALL_FILL_MASK, Lighting.POWER_FILL_MASK],
		"fill_rooms": "D14 bay/hall/power only; remote connectors remain independent under secondary power",
	}}


const SEED: int = 91
var output_dir: String
var world: Node3D
var scene: ShipScene
var game: Game
var camera: Camera3D
var records: Array[Dictionary] = []

func _init() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() != 1 or args[0].strip_edges().is_empty():
		printerr("usage: godot --path . -s tools/capture_ship_surfaces.gd -- <output-dir>")
		quit(2)
		return
	output_dir = args[0]
	_run.call_deferred()

func _run() -> void:
	assert(DisplayServer.get_name() != "headless", "windowed native captures required")
	DirAccess.make_dir_recursive_absolute(output_dir)
	root.content_scale_mode = Window.CONTENT_SCALE_MODE_VIEWPORT
	root.content_scale_size = Vector2i(2304, 1296)
	root.size = root.content_scale_size
	DisplayServer.window_set_size(root.size)
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	root.msaa_3d = Viewport.MSAA_2X
	var identity := capture_identity()
	for white: bool in [false, true]:
		game = Game.new(SEED)
		game.light_hallway()
		if white:
			game.press_console()
			for tick: int in range(BayVentilation.CLEAR_TICKS): game.ventilation.tick(true)
		world = Node3D.new()
		root.add_child(world)
		scene = ShipScene.build_into(world, game, false)
		scene.prepare_near(Vector3(10, 0, 0))
		scene.prepare_near(Vector3(26, 0, 0))
		camera = Camera3D.new()
		world.add_child(camera)
		camera.current = true
		camera.fov = 76
		await _settle(36)
		var circuit := "secondary-white" if white else "emergency-red-orange"
		var hall_bounds := game.layout.section(&"D14-S-041").bounds()
		camera.fov = 68
		await _shot(circuit, "section41-approved-view", &"D14-S-041", hall_bounds.position + Vector3(4, 1.62, hall_bounds.size.z / 2 + 0.06), Vector3(hall_bounds.end.x, hall_bounds.position.y + 1.50, hall_bounds.get_center().z))
		camera.fov = 76
		await _shot(circuit, "grate-grazing", &"D14-S-041", Vector3(hall_bounds.position.x + 5, hall_bounds.position.y + 0.25, 0), Vector3(hall_bounds.end.x - 1, hall_bounds.position.y, 0))
		await _shot(circuit, "section41-corridor", &"D14-S-041", Vector3(18, 1.6, 0.25), Vector3(29.6, 1.5, 0))
		await _shot(circuit, "section41-detail", &"D14-S-041", Vector3(18, 1.6, -0.4), Vector3(18.2, 1.5, -1.5))
		await _shot(circuit, "section41-end-hatch", &"D14-C-001-H-FORE", Vector3(27.5, 1.6, 0), Vector3(30, 1.4, 0))
		camera.fov = 86
		await _shot(circuit, "hatch-close", &"D14-C-001-H-FORE", Vector3(28.45, 1.30, 0.03), Vector3(29.92, 1.30, 0))
		camera.fov = 76
		await _shot(circuit, "hatch-three-quarter", &"D14-C-001-H-FORE", Vector3(28.05, 1.40, -1.16), Vector3(29.92, 1.30, 0))
		var bay_frame := game.layout.bay_to_world()
		await _shot(circuit, "bay", ShipLayout.BAY_ID, bay_frame * Vector3(-0.4, 1.6, 1.49), bay_frame * Vector3(5.8, 1.5, 0))
		await _shot(circuit, "power-doorway", ShipLayout.POWER_ID, Vector3(25.5, 1.6, -0.1), Vector3(27, 1.4, -1.6))
		await _sliding_views(circuit)
		await _shot(circuit, "connector-aft", &"D14-C-001", Vector3(32.8, 1.6, 0), Vector3(30, 1.4, 0))
		await _shot(circuit, "connector-fore", &"D14-C-000", Vector3(3.5, 1.6, 0), Vector3(6, 1.4, 0))
		await _shot(circuit, "section40", &"D14-S-040", Vector3(-12, 1.6, 0.25), Vector3(-0.2, 1.5, 0))
		await _shot(circuit, "section42", &"D14-S-042", Vector3(46, 1.6, 0.25), Vector3(59.8, 1.5, 0))
		for id: StringName in [ShipLayout.BAY_DOOR_ID, &"D14-C-000-H-AFT", &"D14-C-001-H-FORE"]:
			await _faces(circuit, id, "closed")
		for hinge_id: StringName in [ShipLayout.BAY_DOOR_ID, &"D14-C-001-H-FORE"]:
			await _hinge_views(circuit, hinge_id, "closed")
		var id := &"D14-C-001-H-FORE"
		var context := Doors.Context.new()
		context.face_id = game.layout.door(id).face_ids()[0]
		game.doors.press(id, context)
		for tick: int in range(3): game.advance_doors()
		_present()
		await _faces(circuit, id, "cranking")
		while game.doors.snapshot(id).state != Doors.State.OPENING:
			for tick: int in range(Doors.WHEEL_TICKS): game.advance_doors()
			if game.doors.snapshot(id).state != Doors.State.OPENING: game.doors.press(id, context)
		for tick: int in range(Doors.SWING_TICKS / 2): game.advance_doors()
		_present()
		await _faces(circuit, id, "swing")
		for tick: int in range(Doors.SWING_TICKS): game.advance_doors()
		_present()
		await _faces(circuit, id, "parked")
		for open_id: StringName in [ShipLayout.BAY_DOOR_ID, &"D14-C-001-H-FORE"]:
			await _open_rest_views(circuit, open_id)
		for deck: int in [1, 30]:
			var spec := game.layout.connector(ShipLayout.connector_id(deck, 1))
			var remote := scene.build_remote(spec)
			var bounds := spec.bounds()
			await _shot(circuit, "deck%02d-connector" % deck, spec.id(), bounds.get_center() + Vector3(0.6, 0, 0), Vector3(bounds.position.x, bounds.position.y + 1.4, 0))
			scene.remove_remote(spec, remote)
		world.free()
		await process_frame
	if identity != capture_identity():
		push_error("Capture inputs changed during rendering; capture set is inconsistent")
		quit(1)
		return
	identity.merge({"seed": SEED, "material": "round5-steel-v1", "captures": records})
	FileAccess.open(output_dir.path_join("captures.json"), FileAccess.WRITE).store_string(JSON.stringify(identity, "\t") + "\n")
	print("SHIP SURFACES COMPLETE captures=", records.size())
	quit(0)

func _sliding_views(circuit: String) -> void:
	var spec := game.layout.door(ShipLayout.POWER_DOOR_ID)
	var context := Doors.Context.new()
	context.face_id = spec.face_ids()[0]
	for state: String in ["closed", "half-open", "open"]:
		if state == "half-open": game.doors.press(spec.id(), context)
		if state != "closed":
			for tick: int in range(Doors.SWING_TICKS / 2): game.advance_doors()
		_present()
		for side: int in [-1, 1]:
			await _shot(circuit, "power-door-%s-%s" % ["hall" if side < 0 else "room", state], spec.id(), spec.frame() * Vector3(0.35, 1.55, side * 1.50), spec.frame() * Vector3(0.15, 1.10, ShipLayout.WALL / 2))
	var side_door := game.layout.door(&"D14-S-041-SIDE-015-PORT")
	await _shot(circuit, "side-door-close", side_door.id(), side_door.frame() * Vector3(-0.15, 1.55, -1.25), side_door.frame() * Vector3(0, 1.15, 0))

func _open_rest_views(circuit: String, id: StringName) -> void:
	var spec := game.layout.door(id)
	var context := Doors.Context.new()
	context.face_id = spec.face_ids()[0]
	context.rod_carried = true
	for attempt: int in range(HatchResistance.schedule(SEED, id).weights.size() + 1):
		if game.doors.snapshot(id).state == Doors.State.OPEN: break
		game.doors.press(id, context)
		for tick: int in range(Doors.WHEEL_TICKS + Doors.SWING_TICKS): game.advance_doors()
	assert(game.doors.snapshot(id).state == Doors.State.OPEN, "open-rest capture follows the real store")
	_present()
	var leaf: Node3D
	for view: DoorView in scene.door_views:
		if view.door_id() == id: leaf = view.label_leaf()
	assert(leaf != null, "open-rest leaf exists")
	var pose := Surfaces.world_frame(leaf)
	var into := signf(spec.hinge_frame().origin.z - ShipLayout.WALL / 2)
	var mid_depth := -into * (HatchParts.APPROACH_SLAB_DEPTH - HatchParts.REVERSE_SLAB_DEPTH) / 2
	var centre := pose * Vector3(spec.leaf_aperture().x / 2 + HatchParts.HINGE_OUTSET, 1.25, mid_depth)
	# The free-edge eye stays inside the connector; a wider lens fits the slab height.
	var previous_fov := camera.fov
	camera.fov = 100
	await _shot(circuit, "%s-open-rest-edge-on" % id, id, centre + pose.basis.x * 1.15, centre)
	camera.fov = previous_fov
	var eye := spec.frame() * Vector3(0.8, 1.40, spec.hinge_frame().origin.z + into * 2.1)
	await _shot(circuit, "%s-open-rest-swing-three-quarter" % id, id, eye, centre)
	await _hinge_views(circuit, id, "open")

func _hinge_views(circuit: String, id: StringName, state: String) -> void:
	var spec := game.layout.door(id)
	var axis := spec.hinge_frame().origin
	var into := signf(axis.z - ShipLayout.WALL / 2)
	var previous_fov := camera.fov
	camera.fov = 60
	for station: int in range(HatchParts.HINGE_HEIGHTS.size()):
		var target := axis + Vector3.UP * HatchParts.HINGE_HEIGHTS[station]
		var eye := target + Vector3(-0.75, 0.08, into * 0.65)
		await _shot(circuit, "%s-hinge-%d-%s" % [id, station, state], id, spec.frame() * eye, spec.frame() * target)
	camera.fov = previous_fov

func _present() -> void:
	for view: DoorView in scene.door_views: view.present(game.doors.snapshot(view.door_id()))

func _faces(circuit: String, id: StringName, pose: String) -> void:
	var spec := game.layout.door(id)
	var view: DoorView
	for candidate: DoorView in scene.door_views:
		if candidate.door_id() == id: view = candidate
	assert(view != null, "capture door exists")
	var frame := Surfaces.world_frame(view.label_leaf())
	for side: int in [-1, 1]:
		var depth := spec.leaf_face_depth(0 if side < 0 else 1)
		var center := frame * Vector3(spec.leaf_aperture().x / 2 + HatchParts.HINGE_OUTSET, 1.25, side * depth)
		await _shot(circuit, "%s-%s-%s" % [id, "fore" if side < 0 else "aft", pose], id, center + frame.basis.z * side * 1.85, center)

func _shot(circuit: String, name: String, owner: StringName, eye: Vector3, target: Vector3) -> void:
	camera.position = eye
	camera.look_at(target)
	await _settle(12)
	var path := output_dir.path_join("%s-%s.png" % [circuit, name])
	var image := root.get_texture().get_image()
	assert(image.get_size() == Vector2i(2304, 1296), "native capture resolution")
	assert(image.save_png(path) == OK, "capture saved: " + path)
	var state: Dictionary = {}
	if owner in game.layout.door_ids():
		var snapshot := game.doors.snapshot(owner)
		state = {"state": snapshot.state, "wheel_degrees": snapshot.wheel_angle, "leaf_fraction": snapshot.leaf_fraction, "rest_radians": snapshot.open_radians}
	records.append({"path": path, "owner": owner, "circuit": circuit, "eye": [eye.x, eye.y, eye.z], "camera_transform": str(camera.transform), "fov": camera.fov, "snapshot": state})
	print("SHIP CAPTURE ", path)

func _settle(count: int) -> void:
	for index: int in range(count): await process_frame
	await RenderingServer.frame_post_draw
