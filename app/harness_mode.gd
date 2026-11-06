extends SceneTree
## The harness lane's app side, ported from gone_app's bootstrap harness:
## when GONE_HARNESS=1 the game boots in driven mode — the scenario's
## fixed 60 Hz timeline feeds synthetic input through the shared
## InputPlane (the ScriptedAdapter the real player consumes; gameplay is
## never called directly), the frame-code chip paints the current
## (tick, frame) into the captured view, due beats are captured as
## beats/<name>.png, and report.json carries the protocol surface.
## Exits 0 on success, nonzero on failure. Spawned windowed by
## harness/run.gd.

const Protocol := preload("res://harness/protocol.gd")
const ScenarioModule := preload("res://harness/scenario.gd")
const ReportModule := preload("res://harness/report.gd")
const PerfPolicyModule := preload("res://harness/perf_policy.gd")

const WARMUP_FRAMES: int = 4
const SETTLE_TICKS: int = 5

var out_dir: String = ""
var scenario
var report
var game_step: GameStep
var game: Game
var player: Player
var rod: Rod
var hallway: Hallway
var power_room: PowerRoom
var stasis_lighting: Lighting
var adapter: InputPlane.ScriptedAdapter
var input
var chip: LaneChip
var pods_node: Node

var ready: bool = false
var failed: bool = false
var tick: int = 0
var frame: int = 0
var next_beat_index: int = 0
var pending_captures: Array = []
var busy_capturing: bool = false
var last_phase: String = ""
var perf_policy
var perf_samples_ms: Array[float] = []
var connector_evidence: ConnectorEvidence
var finished: bool = false
var last_batch_wait: String = ""

func _initialize() -> void:
	if OS.get_environment(Protocol.ENV_HARNESS) != "1":
		push_error("harness_mode: GONE_HARNESS != 1; refusing to run outside the harness")
		quit(2)
		return
	out_dir = OS.get_environment(Protocol.ENV_OUT_DIR)
	var scenario_path := OS.get_environment(Protocol.ENV_SCENARIO)
	if out_dir.is_empty() or scenario_path.is_empty():
		push_error("harness_mode: GONE_OUT_DIR/GONE_SCENARIO missing from the environment")
		quit(2)
		return
	var scenario_text := FileAccess.get_file_as_string(scenario_path)
	if scenario_text.is_empty():
		push_error("harness_mode: cannot read scenario %s" % scenario_path)
		quit(2)
		return
	var parsed: Dictionary = ScenarioModule.parse(scenario_text)
	if parsed.error != "":
		push_error("harness_mode: %s" % parsed.error)
		quit(2)
		return
	scenario = parsed.scenario
	if scenario.mode == "perf":
		var policy_path := OS.get_environment(Protocol.ENV_PERF_POLICY)
		var policy_text := FileAccess.get_file_as_string(policy_path)
		if policy_text.is_empty():
			push_error("harness_mode: cannot read perf policy %s" % policy_path)
			quit(2)
			return
		var parsed_policy: Dictionary = PerfPolicyModule.parse_policy(policy_text)
		if parsed_policy.error != "":
			push_error("harness_mode: %s" % parsed_policy.error)
			quit(2)
			return
		perf_policy = parsed_policy.policy
		DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	DirAccess.make_dir_recursive_absolute(out_dir)
	DirAccess.make_dir_recursive_absolute(out_dir.path_join("beats"))
	report = ReportModule.new(Protocol.PROTOCOL_VERSION,
		scenario.scenario_name, scenario.seed, {
			"app_hash": OS.get_environment(Protocol.ENV_APP_HASH),
			"scenario_hash": OS.get_environment(Protocol.ENV_SCENARIO_HASH),
			"config_hash": OS.get_environment(Protocol.ENV_CONFIG_HASH),
		})
	report.logical_steps_per_present = scenario.logical_steps_per_present
	if not scenario.connector.is_empty():
		connector_evidence = ConnectorEvidence.new()
	input = ScenarioModule.InputAdapter.new(
		scenario.actions, scenario.ticks_per_second)
	adapter = InputPlane.ScriptedAdapter.new()
	_build_scene()
	_boot()

## Build the real game content the same way capture_gameplay.gd does:
## the full stasis room, the player rig in scripted mode, the wake pass,
## plus the protocol chip overlay.
func _build_scene() -> void:
	game = Game.new(scenario.seed)
	var scene := Node3D.new()
	scene.name = "CaptureRoot"
	var ship := ShipScene.build_into(scene, game, false)
	pods_node = ship.pods_node
	stasis_lighting = ship.lighting
	rod = ship.rod
	hallway = ship.hallway
	power_room = ship.power_room
	player = Player.build(game, ship.hatch)
	player.scripted = true
	player.rod = rod
	player.power_room = power_room
	player.adapter = adapter
	scene.add_child(player)
	var driver := Driver.new()
	driver.mode = self
	root.add_child(driver)
	root.add_child(scene)
	game_step = GameStep.new(game, player)
	game_step.door_views = ship.door_views
	game_step.ship_scene = ship
	game_step.fixtures.assign([stasis_lighting, hallway, power_room])
	var layer := CanvasLayer.new()
	layer.layer = 128
	chip = LaneChip.new()
	layer.add_child(chip)
	root.add_child(layer)

## Readiness gating: the pass/present wire up after the first frame, the
## first fully-closed frame is captured separately as readiness-proof.png,
## and the driven clock starts only after that proof exists.
func _boot() -> void:
	for _warmup: int in range(WARMUP_FRAMES):
		await process_frame
	var wake_pass := WakePass.build()
	root.get_node("CaptureRoot").add_child(wake_pass)
	var wake_present := WakePresent.build(game, player.camera, wake_pass, player)
	root.get_node("CaptureRoot").add_child(wake_present)
	await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw
	observe_room()
	var proof := root.get_texture().get_image()
	var proof_error := proof.save_png(out_dir.path_join("readiness-proof.png"))
	if proof_error != OK:
		_fail("readiness proof capture failed: %d" % proof_error)
		return
	report.add_event({"kind": "ready", "frame": frame})
	report.checkpoints.append("ready at frame %d" % frame)
	last_phase = phase_name(game.phase.current())
	report.add_event({"kind": "wake_phase", "tick": tick, "frame": frame,
		"phase": last_phase})
	print("GONE_READY %d %d" % [Protocol.PROTOCOL_VERSION, frame])
	ready = true
	if scenario.mode == "perf":
		await _run_perf_window()
		_finish(true)

## The perf lane's measurement window: after readiness the populated room
## runs the scripted camera route while WARMUP rendered frames pass
## unmeasured, then SAMPLE rendered frames are wall-clock timed (vsync
## disabled, presentation Uncapped). No captures, no beats: the report's
## perf section carries the samples and their statistics.
func _run_perf_window() -> void:
	for _warmup: int in range(int(perf_policy.warmup_frames)):
		await process_frame
	for _sample: int in range(int(perf_policy.sample_frames)):
		var started := Time.get_ticks_usec()
		await process_frame
		perf_samples_ms.append(float(Time.get_ticks_usec() - started) / 1000.0)
	var stats: Dictionary = PerfPolicyModule.stats_from_samples(perf_samples_ms)
	report.perf = {
		"warmup_frames": int(perf_policy.warmup_frames),
		"sample_frames": int(perf_policy.sample_frames),
		"presentation": String(perf_policy.presentation),
		"resolution": {"width": int(perf_policy.resolution.width),
			"height": int(perf_policy.resolution.height)},
		"samples_ms": perf_samples_ms.duplicate(),
		"stats": stats,
		"stream": {"remote_rooms_built": game_step.ship_scene.stream.constructed_rooms, "shafts": game_step.ship_scene.stream.shaft_count(), "pending_rooms": game_step.ship_scene.stream.pending_count(), "rasterized_pairs": game_step.ship_scene.text_cache.rasterized_pairs},
	}
	print("GONE_PERF %s" % PerfPolicyModule.distribution_line(stats))

func observe_room() -> void:
	var pods_expected: int = game.registry.pods().size()
	var pods_present: int = pods_node.get_child_count()
	report.add_event({"kind": "room_check", "frame": frame,
		"pods_expected": pods_expected, "pods_present": pods_present})
	if pods_expected != pods_present:
		_fail("stasis room mismatch: the registry builds %d pods but %d are present" % [
			pods_expected, pods_present])

func _fail(what: String) -> void:
	if failed:
		return
	failed = true
	report.add_event({"kind": "failure", "frame": frame, "what": what})
	_finish(false)

func _finish(success: bool) -> void:
	finished = true
	report.logical_ticks = tick
	if connector_evidence != null:
		report.logical_digest = connector_evidence.finish_digest()
	if success:
		report.add_event({"kind": "complete", "frame": frame})
	report.frame_stats = {"frames": frame, "mean_us": 0.0, "p95_us": 0.0,
		"median_us": 0.0}
	var text: String = report.to_json()
	var path := out_dir.path_join("report.json")
	var file := FileAccess.open(path, FileAccess.WRITE)
	if file == null:
		push_error("harness_mode: cannot write report %s" % path)
		quit(1)
		return
	file.store_string(text)
	file.close()
	print("REPORT %s" % path)
	quit(0 if success else 1)

static func phase_name(phase: int) -> String:
	match phase:
		Phase.Wake.WAKING:
			return "waking"
		Phase.Wake.AWAKE_IN_POD:
			return "awake_in_pod"
		Phase.Wake.EXITING_POD:
			return "exiting_pod"
		_:
			return "standing"

## The fixed-timeline driver: added to the root before the game scene,
## so its physics tick runs first and the scripted input is on the plane
## before the player's tick consumes it. Default lanes use one physics tick
## per scenario tick. Accelerated captures use _process instead, with the same
## fixed GameStep and a separate input/evidence sample for each logical tick.
class Driver:
	extends Node

	## Untyped on purpose: dynamic dispatch into the SceneTree lane's
	## members, which are not Node/SceneTree API.
	var mode

	func _physics_process(_delta: float) -> void:
		var harness = mode
		if not harness.ready or harness.failed or harness.busy_capturing or not harness.pending_captures.is_empty():
			return
		if harness.scenario.logical_steps_per_present == 1:
			harness.drive_tick()

	func _process(_delta: float) -> void:
		var harness = mode
		if harness.failed or harness.finished or harness.busy_capturing:
			return
		if harness.ready and harness.scenario.logical_steps_per_present > 1:
			harness.observe_batch_wait()
			CaptureBatch.advance(harness.scenario.logical_steps_per_present, harness.drive_tick, harness.batch_boundary)
		harness.frame += 1
		harness.chip.set_code(harness.tick, harness.frame)
		# The lane renders roughly two frames per fixed tick, so the
		# runaway guard must scale with the scenario's own tick budget
		# or it fires before late beats (the hallway lane's switch flip
		# lands past tick 3000).
		if harness.frame > harness.scenario.max_frames * 2 + 900:
			harness._fail("hard frame budget exhausted")
			return
		if not harness.ready or harness.busy_capturing or harness.pending_captures.is_empty():
			return
		harness.capture_next_beat()

## One driven fixed tick. Input flows only through the ScriptedAdapter
## onto the shared plane; gameplay functions are never called directly.
func drive_tick() -> void:
	var step: Dictionary = input.step()
	var any_input: bool = false
	for edge: Dictionary in step.edges:
		adapter.press(_button(edge.button))
		report.add_event({"kind": "input", "tick": tick, "frame": frame,
			"what": "%s %s" % [edge.button, edge.edge]})
		any_input = true
	var look: Vector2 = step.look_deg
	if look != Vector2.ZERO:
		adapter.look(deg_to_rad(look.x), deg_to_rad(look.y))
		report.add_event({"kind": "input", "tick": tick, "frame": frame,
			"what": "look %.4f %.4f" % [look.x, look.y]})
		any_input = true
	var key_turn: float = step.key_turn
	if key_turn != 0.0:
		# The device producer's expression for a held look key, so
		# scripted turning matches the keyboard exactly.
		var yaw_delta := -key_turn * InputPlane.TURN_SPEED / float(scenario.ticks_per_second)
		adapter.look(yaw_delta, 0.0)
		report.add_event({"kind": "input", "tick": tick, "frame": frame,
			"what": "key_turn %.4f" % rad_to_deg(yaw_delta)})
		any_input = true
	var key_pitch: float = step.key_pitch
	if key_pitch != 0.0:
		# The device producer's expression for a held pitch key, so
		# scripted pitching matches the keyboard exactly.
		var pitch_delta := key_pitch * InputPlane.PITCH_SPEED / float(scenario.ticks_per_second)
		adapter.look(0.0, pitch_delta)
		report.add_event({"kind": "input", "tick": tick, "frame": frame,
			"what": "key_pitch %.4f" % rad_to_deg(pitch_delta)})
		any_input = true
	var movement: Vector2 = step.movement
	if movement != Vector2.ZERO:
		# Scripted movement stays in the sim's yaw frame (+Z forward);
		# only the device producer bridges Godot's -Z view (player.gd).
		adapter.hold(movement.x, movement.y)
		report.add_event({"kind": "input", "tick": tick, "frame": frame,
			"what": "move %.4f %.4f" % [movement.x, movement.y]})
		any_input = true
	else:
		adapter.release()
	if not player.motion.failure().is_empty():
		_fail("motion failure: %s" % player.motion.failure())
		return
	if step.climb != null:
		adapter.climb(step.climb)
	if step.objective != null:
		adapter.objective(step.objective)
		report.add_event({"kind": "input", "tick": tick, "frame": frame, "what": "objective %s" % step.objective.target_id})
	game_step.advance()
	observe_phase()
	tick += 1
	if connector_evidence != null:
		for event: Dictionary in connector_evidence.observe(player, tick, frame):
			report.add_event(event)
	while next_beat_index < scenario.beats.size() and scenario.beats[next_beat_index].tick < tick:
		pending_captures.append(scenario.beats[next_beat_index])
		next_beat_index += 1
	if pending_captures.is_empty() and next_beat_index >= scenario.beats.size() \
			and input.is_complete() and not failed:
		if scenario.mode == "perf":
			return
		if tick >= last_beat_tick() + SETTLE_TICKS:
			_finish(true)
		return
	if tick >= scenario.max_frames and not failed:
		var missing: Array = []
		for index: int in range(next_beat_index, scenario.beats.size()):
			missing.append(scenario.beats[index].name)
		_fail("max_frames deadline passed at tick %d; uncaptured beats: %s" % [
			tick, ", ".join(missing)])

func observe_phase() -> void:
	var current := phase_name(game.phase.current())
	if current != last_phase:
		last_phase = current
		report.add_event({"kind": "wake_phase", "tick": tick, "frame": frame,
			"phase": current})

func last_beat_tick() -> int:
	if scenario.beats.is_empty():
		return 0
	return scenario.beats[scenario.beats.size() - 1].tick

## Capture one pinned beat: paint the chip with the pinned numbers, wait
## for the draw, save the PNG, and record the beat plus the pose samples
## stamped with exactly those numbers.
func capture_next_beat() -> void:
	busy_capturing = true
	var beat: Dictionary = pending_captures.pop_front()
	var pinned_tick: int = tick
	var pinned_frame: int = frame
	chip.set_code(pinned_tick, pinned_frame)
	if connector_evidence != null:
		print("GONE_CONNECTOR_CAPTURE %s tick=%d frame=%d" % [beat.name, pinned_tick, pinned_frame])
	# A pinned, motionless capture still needs a draw on render-on-change backends.
	RenderingServer.call_deferred("force_draw", false)
	await RenderingServer.frame_post_draw
	var image := root.get_texture().get_image()
	var file := "beats/%s.png" % beat.name
	var error := image.save_png(out_dir.path_join(file))
	if error != OK:
		_fail("beat `%s` capture failed: %d" % [beat.name, error])
		return
	var request_id: int = report.beats.size() + 1
	report.beats[beat.name] = {"file": file, "tick": pinned_tick,
		"frame": pinned_frame, "request_id": request_id}
	report.add_event({"kind": "beat", "name": beat.name, "tick": pinned_tick,
		"frame": pinned_frame, "request_id": request_id})
	report.checkpoints.append("beat `%s` captured at tick %d frame %d" % [
		beat.name, pinned_tick, pinned_frame])
	var angles := player.look_angles()
	report.add_event({"kind": "player_yaw", "tick": pinned_tick,
		"frame": pinned_frame, "yaw_degrees": rad_to_deg(angles.x)})
	var eye := player.motion.eye(game)
	report.add_event({"kind": "player_position", "tick": pinned_tick,
		"frame": pinned_frame, "x": eye.x, "y": eye.y, "z": eye.z})
	if beat.name == "door-opened":
		report.add_event({"kind": "door_open", "tick": pinned_tick,
			"frame": pinned_frame, "openings": game.doors.snapshot(ShipLayout.BAY_DOOR_ID).releases,
			"open": game.door_open})
	elif beat.name == "rod-picked-up":
		report.add_event({"kind": "rod_pickup", "tick": pinned_tick,
			"frame": pinned_frame, "carried": player.motion.rod_carried,
			"rod_visible": rod.visible})
	elif beat.name == "power-door-opened":
		report.add_event({"kind": "power_door", "tick": pinned_tick,
			"frame": pinned_frame, "openings": game.doors.snapshot(ShipLayout.POWER_DOOR_ID).releases,
			"open": game.power_door_open})
	elif beat.name == "console-inactive" or beat.name == "power-active":
		report.add_event({"kind": "console", "tick": pinned_tick,
			"frame": pinned_frame, "presses": player.motion.console_presses,
			"state": PowerRoom.console_state_name(game.console_state),
			"native_label": PowerRoom.console_labels(game.console_state).native,
			"perceived_label": PowerRoom.console_labels(game.console_state).perceived_es})
		report.add_event({"kind": "power", "tick": pinned_tick,
			"frame": pinned_frame, "active": game.power_active,
			"generator_lit": power_room.generator_lit(),
			"hallway_lit": game.hallway_lit,
			"hall_red_level": hallway.level(),
			"hall_white_level": hallway.white_level(),
			"power_red_level": power_room.level(),
			"power_white_level": power_room.white_level(),
				"stasis_red_level": stasis_lighting.level(),
				"stasis_white_level": stasis_lighting.white_level(),
				"bay_smoke_density": game.ventilation.density()})
	elif beat.name == "hall-dark" or beat.name == "hall-lit" or beat.name == "hall-white":
		report.add_event({"kind": "hallway", "tick": pinned_tick,
			"frame": pinned_frame, "lit": game.hallway_lit,
			"level": hallway.level(),
			"white": game.power_active,
			"white_level": hallway.white_level()})
		if beat.name == "hall-white":
			report.add_event({"kind": "power", "tick": pinned_tick,
				"frame": pinned_frame, "active": game.power_active,
				"generator_lit": power_room.generator_lit(),
				"hallway_lit": game.hallway_lit,
				"hall_red_level": hallway.level(),
				"hall_white_level": hallway.white_level(),
				"power_red_level": power_room.level(),
				"power_white_level": power_room.white_level(),
			"stasis_red_level": stasis_lighting.level(),
			"stasis_white_level": stasis_lighting.white_level(),
			"bay_smoke_density": game.ventilation.density()})
	if connector_evidence != null:
		var ship := game_step.ship_scene
		var residency := ConnectorEvidence.pose(player)
		var doors: Dictionary = {}
		for id: StringName in game.layout.door_ids():
			if game.layout.door(id).deck_number() == int(residency.deck):
				var state := game.doors.snapshot(id)
				doors[String(id)] = {"state": state.state, "attempt": state.attempt, "work": state.work, "wheel_angle": state.wheel_angle, "releases": state.releases}
		residency.doors = doors
		residency.merge({"kind": "residency", "beat": beat.name, "tick": pinned_tick, "frame": pinned_frame, "rooms": ship.stream.resident_ids(), "pending_rooms": ship.stream.pending_count(), "pending_labels": ship.text_cache.pending_count(), "remote_lights": ship.stream.remote_light_count(), "build_usec": ship.stream.last_build_usec})
		report.add_event(residency)
		if scenario.connector.labels.has(beat.name):
			var id := StringName(scenario.connector.labels[beat.name].id)
			if not ship.labels.has(id):
				_fail("capture missing label %s" % id)
				return
			report.add_event(ConnectorEvidence.label(ship.labels[id], game.layout, beat.name, pinned_tick, pinned_frame, player))
	busy_capturing = false

func observe_batch_wait() -> void:
	var rooms := game_step.ship_scene.stream.pending_count()
	var labels := game_step.ship_scene.text_cache.pending_count()
	var waiting := "%d:%d:%d" % [tick, rooms, labels] if rooms > 0 or labels > 0 else ""
	if waiting != last_batch_wait:
		last_batch_wait = waiting
		print("GONE_CONNECTOR_QUEUE tick=%d rooms=%d labels=%d" % [tick, rooms, labels])

func batch_boundary() -> bool:
	return finished or failed or busy_capturing or not pending_captures.is_empty() or game_step.ship_scene.stream.pending_count() > 0 or game_step.ship_scene.text_cache.pending_count() > 0

func _button(name: String) -> int:
	match name:
		"activate":
			return InputPlane.Buttons.ACTIVATE
		"interact":
			return InputPlane.Buttons.INTERACT
		_:
			return InputPlane.Buttons.EXIT
