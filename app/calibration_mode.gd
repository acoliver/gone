extends SceneTree
## The calibration-evidence lane's app side, ported from gone_app's
## bootstrap/calibration.rs: the scenario predeclares one luminance step,
## an equal-area bright-patch placement plan, a metering-mask selection,
## and the auto-exposure arm. This lane renders exactly that scene — an
## emissive wall and patch through a Camera3D with a LINEAR tonemapper —
## meters a 48x27 SubViewport view of the same world through the
## selected mask, adapts exposure in a closed loop when the arm is on,
## pins the scenario's beats as captures, and records the setup identity
## as a Calibration report event BEFORE any sample is pinned. It never
## measures luminance itself; the runner measures the capture PNGs.

const Protocol := preload("res://harness/protocol.gd")
const ScenarioModule := preload("res://harness/scenario.gd")
const ReportModule := preload("res://harness/report.gd")
const CalibrationModule := preload("res://harness/calibration.gd")

const WARMUP_FRAMES: int = 4
const SETTLE_TICKS: int = 5
const CALIBRATION_FOV: float = PI / 4.0
const WALL_DISTANCE: float = 5.0
const PATCH_FORWARD: float = 0.01
const EDGE_SLOT_FRACTION: float = 0.75
const PATCH_LEVEL_MULTIPLE: float = 10.0
const WALL_OVERSCAN: float = 3.0
const AE_TARGET_MEAN: float = 0.35
const METER_SIZE: Vector2i = Vector2i(48, 27)

var out_dir: String = ""
var scenario
var params: Dictionary
var report
var chip: LaneChip
var wall_material: StandardMaterial3D
var patch_material: StandardMaterial3D
var patch_node: MeshInstance3D
var attributes: CameraAttributesPractical
var meter_viewport: SubViewport
var meter_camera: Camera3D
var mask_image: Image

var ready: bool = false
var failed: bool = false
var tick: int = 0
var frame: int = 0
var next_beat_index: int = 0
var pending_captures: Array = []
var busy_capturing: bool = false
var evidence_recorded: bool = false
var exposure_ev: float = 0.0
var exposure_armed: bool = false
var input

func _initialize() -> void:
	if OS.get_environment(Protocol.ENV_HARNESS) != "1":
		push_error("calibration_mode: GONE_HARNESS != 1; refusing to run outside the harness")
		quit(2)
		return
	out_dir = OS.get_environment(Protocol.ENV_OUT_DIR)
	var scenario_path := OS.get_environment(Protocol.ENV_SCENARIO)
	if out_dir.is_empty() or scenario_path.is_empty():
		push_error("calibration_mode: GONE_OUT_DIR/GONE_SCENARIO missing from the environment")
		quit(2)
		return
	var scenario_text := FileAccess.get_file_as_string(scenario_path)
	if scenario_text.is_empty():
		push_error("calibration_mode: cannot read scenario %s" % scenario_path)
		quit(2)
		return
	var parsed: Dictionary = ScenarioModule.parse(scenario_text)
	if parsed.error != "":
		push_error("calibration_mode: %s" % parsed.error)
		quit(2)
		return
	scenario = parsed.scenario
	params = scenario.calibration
	input = ScenarioModule.InputAdapter.new(scenario.actions, scenario.ticks_per_second)
	DirAccess.make_dir_recursive_absolute(out_dir)
	DirAccess.make_dir_recursive_absolute(out_dir.path_join("beats"))
	report = ReportModule.new(Protocol.PROTOCOL_VERSION,
		scenario.scenario_name, scenario.seed, {
			"app_hash": OS.get_environment(Protocol.ENV_APP_HASH),
			"scenario_hash": OS.get_environment(Protocol.ENV_SCENARIO_HASH),
			"config_hash": OS.get_environment(Protocol.ENV_CONFIG_HASH),
		})
	_build_scene()
	_boot()

## The calibration scene: a camera at the origin facing an emissive wall
## 5 units away (45-degree vertical FOV), the bright patch in front of
## the wall, a meter SubViewport sharing the world (the chip lives on the
## root only, so metering never sees it), and the protocol chip overlay.
func _build_scene() -> void:
	var scene := Node3D.new()
	scene.name = "CalibrationRoot"
	var environment := Environment.new()
	environment.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	scene.add_child(WorldEnvironment.new())
	scene.get_child(0).environment = environment
	var extent := frame_extents()
	var wall := MeshInstance3D.new()
	wall.mesh = QuadMesh.new()
	(wall.mesh as QuadMesh).size = Vector2(extent.x * WALL_OVERSCAN, extent.y * WALL_OVERSCAN)
	wall.position = Vector3(0.0, 0.0, -WALL_DISTANCE)
	wall_material = _level_material(float(params.initial_level))
	wall.material_override = wall_material
	scene.add_child(wall)
	var side := patch_side(float(params.patch_area_fraction))
	patch_node = MeshInstance3D.new()
	patch_node.mesh = QuadMesh.new()
	(patch_node.mesh as QuadMesh).size = Vector2(side, side)
	patch_material = _level_material(float(params.initial_level) * PATCH_LEVEL_MULTIPLE)
	patch_node.material_override = patch_material
	patch_node.position = patch_translation(CalibrationModule.patch_slot_at(params.patch, 0))
	scene.add_child(patch_node)
	var camera := Camera3D.new()
	camera.fov = rad_to_deg(CALIBRATION_FOV)
	camera.near = 0.05
	camera.far = 100.0
	camera.current = true
	attributes = CameraAttributesPractical.new()
	attributes.auto_exposure_enabled = false
	camera.attributes = attributes
	scene.add_child(camera)
	meter_viewport = SubViewport.new()
	meter_viewport.size = METER_SIZE
	meter_viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	meter_camera = Camera3D.new()
	meter_camera.fov = rad_to_deg(CALIBRATION_FOV)
	meter_camera.near = 0.05
	meter_camera.far = 100.0
	var meter_attributes := CameraAttributesPractical.new()
	meter_attributes.auto_exposure_enabled = false
	meter_camera.attributes = meter_attributes
	meter_viewport.add_child(meter_camera)
	scene.add_child(meter_viewport)
	root.add_child(scene)
	var driver := CalibrationDriver.new()
	driver.mode = self
	root.add_child(driver)
	var layer := CanvasLayer.new()
	layer.layer = 128
	chip = LaneChip.new()
	layer.add_child(chip)
	root.add_child(layer)

func _boot() -> void:
	mask_image = Image.new()
	var mask_bytes := FileAccess.get_file_as_bytes(ProjectSettings.globalize_path(
		CalibrationModule.mask_path(String(params.mask))))
	if mask_bytes.is_empty() or mask_image.load_png_from_buffer(mask_bytes) != OK:
		_fail("metering mask failed to load")
		return
	for _warmup: int in range(WARMUP_FRAMES):
		await process_frame
	meter_viewport.world_3d = root.get_world_3d()
	await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw
	await _prime_exposure()
	var sample_ticks: Array = scenario.beats.map(func(beat: Dictionary) -> int: return int(beat.tick))
	sample_ticks.sort()
	report.add_event({"kind": "ready", "frame": frame})
	report.add_event({"kind": "calibration", "tick": tick, "frame": frame,
		"evidence": {
			"mask": String(params.mask),
			"mask_sha256": Protocol.sha256_hex(mask_image.get_data()),
			"auto_exposure": CalibrationModule.auto_exposure_evidence(bool(params.auto_exposure)),
			"authored_exposure_ev100": 0.0,
			"patch_area_fraction": float(params.patch_area_fraction),
			"patch_placements": CalibrationModule.patch_placements(params.patch),
			"initial_level": float(params.initial_level),
			"step_tick": int(params.step.tick),
			"step_level": float(params.step.level),
			"sample_ticks": sample_ticks,
		}})
	report.checkpoints.append("calibration evidence recorded before samples pinned")
	evidence_recorded = true
	print("GONE_READY %d %d" % [Protocol.PROTOCOL_VERSION, frame])
	ready = true

## Set the exposure to the settled value for the initial level so the
## pre-perturbation window starts adapted (the loop then only has to
## handle the declared perturbations).
## Set the exposure to its settled value for the initial scene so the
## pre-perturbation window starts adapted. The meter reads the exposure
## the capture shows (the gain is in the emissions), so the fixed point
## is metered == target; reach it through rendered frames with a damped
## log-space step that tolerates the clamped, superlinear meter response.
func _prime_exposure() -> void:
	exposure_armed = true
	var level := CalibrationModule.wall_level(params, 0)
	for _attempt: int in range(30):
		var metered := meter_mean_linear()
		if metered > 0.0:
			var residual := log(AE_TARGET_MEAN / metered) / log(2.0)
			if absf(residual) < 0.004:
				break
			exposure_ev += residual / 3.0
			_apply_levels(level)
		await RenderingServer.frame_post_draw

## Apply the tick's wall/patch emission at the current exposure gain;
## exposure is applied through the emission exactly once (the camera's
## own multiplier stays 1.0).
func _apply_levels(level: float) -> void:
	var gain := pow(2.0, exposure_ev)
	wall_material.emission = Color(level * gain, level * gain, level * gain)
	var patch_level := level * PATCH_LEVEL_MULTIPLE
	patch_material.emission = Color(patch_level * gain, patch_level * gain, patch_level * gain)

## Mask-weighted mean linear luminance of the meter view. The meter
## camera renders the same world at exposure 1.0, so this is the raw
## scene radiance the mask meters.
func meter_mean_linear() -> float:
	var image := meter_viewport.get_texture().get_image()
	if image == null or image.is_empty():
		return 0.0
	var total: float = 0.0
	var weight_total: float = 0.0
	var mask_data := mask_image.get_data()
	for y: int in range(image.get_height()):
		for x: int in range(image.get_width()):
			var color := image.get_pixel(x, y).srgb_to_linear()
			## Meter in the LDR domain the assertions measure: the captured
			## PNG clamps at 1.0 after tonemapping, so an HDR patch value
			## above white must not steer the loop either.
			var luma: float = minf(0.2126 * color.r + 0.7152 * color.g + 0.0722 * color.b, 1.0)
			var mask_index: int = (y % mask_image.get_height()) * mask_image.get_width() + (x % mask_image.get_width())
			var weight: float = float(mask_data[mask_index]) / 255.0
			total += luma * weight
			weight_total += weight
	return total / weight_total if weight_total > 0.0 else 0.0

func _fail(what: String) -> void:
	if failed:
		return
	failed = true
	report.add_event({"kind": "failure", "frame": frame, "what": what})
	_finish(false)

func _finish(success: bool) -> void:
	if success:
		report.add_event({"kind": "complete", "frame": frame})
	report.frame_stats = {"frames": frame, "mean_us": 0.0, "p95_us": 0.0,
		"median_us": 0.0}
	var text: String = report.to_json()
	var path := out_dir.path_join("report.json")
	var file := FileAccess.open(path, FileAccess.WRITE)
	if file == null:
		push_error("calibration_mode: cannot write report %s" % path)
		quit(1)
		return
	file.store_string(text)
	file.close()
	print("REPORT %s" % path)
	quit(0 if success else 1)

## One driven tick: apply the tick's scene state (wall level from the
## step plan, patch at its plan slot), then adapt exposure toward the
## mask-weighted target when the arm is on.
func drive_tick() -> void:
	var level := CalibrationModule.wall_level(params, tick)
	_apply_levels(level)
	patch_node.position = patch_translation(CalibrationModule.patch_slot_at(params.patch, tick))
	if params.auto_exposure and exposure_armed:
		var metered := meter_mean_linear()
		if metered > 0.0:
			var delta := log(AE_TARGET_MEAN / metered) / log(2.0)
			var dt := 1.0 / float(scenario.ticks_per_second)
			exposure_ev += clampf(delta, -CalibrationModule.AE_SPEED_BRIGHTEN * dt,
				CalibrationModule.AE_SPEED_DARKEN * dt)
			_apply_levels(level)
	tick += 1
	if OS.get_environment("GONE_CAL_DEBUG") == "1" and tick % 30 == 0:
		print("CAL tick %d ev %.4f mult %.4f metered %.4f wall %.3f" % [tick, exposure_ev,
			pow(2.0, exposure_ev), meter_mean_linear(),
			CalibrationModule.wall_level(params, tick)])
	while next_beat_index < scenario.beats.size() and scenario.beats[next_beat_index].tick < tick:
		pending_captures.append(scenario.beats[next_beat_index])
		next_beat_index += 1
	if pending_captures.is_empty() and next_beat_index >= scenario.beats.size() \
			and not failed:
		if tick >= last_beat_tick() + SETTLE_TICKS:
			_finish(true)
		return
	if tick >= scenario.max_frames and not failed:
		var missing: Array = []
		for index: int in range(next_beat_index, scenario.beats.size()):
			missing.append(scenario.beats[index].name)
		_fail("max_frames deadline passed at tick %d; uncaptured beats: %s" % [
			tick, ", ".join(missing)])

func last_beat_tick() -> int:
	if scenario.beats.is_empty():
		return 0
	return int(scenario.beats[scenario.beats.size() - 1].tick)

## Capture one pinned beat exactly as the capture lane does: chip pinned
## to (tick, frame), draw, save, record.
func capture_next_beat() -> void:
	busy_capturing = true
	var beat: Dictionary = pending_captures.pop_front()
	var pinned_tick: int = tick
	var pinned_frame: int = frame
	chip.set_code(pinned_tick, pinned_frame)
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
	busy_capturing = false

## Scene geometry, ported from bootstrap/calibration.rs: the pinned frame
## extents at the wall plane, the equal-area patch side, and the two
## slot positions.
func frame_extents() -> Vector2:
	var aspect := float(root.size.x) / float(root.size.y)
	var height := 2.0 * WALL_DISTANCE * tan(CALIBRATION_FOV / 2.0)
	return Vector2(height * aspect, height)

func patch_side(fraction: float) -> float:
	var extent := frame_extents()
	return sqrt(fraction * extent.x * extent.y)

func patch_translation(slot: String) -> Vector3:
	var extent := frame_extents()
	if slot == "edge":
		return Vector3(EDGE_SLOT_FRACTION * extent.x / 2.0,
			EDGE_SLOT_FRACTION * extent.y / 2.0, -WALL_DISTANCE + PATCH_FORWARD)
	return Vector3(0.0, 0.0, -WALL_DISTANCE + PATCH_FORWARD)

func _level_material(level: float) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.albedo_color = Color.BLACK
	material.emission_enabled = true
	material.emission = Color(level, level, level)
	return material

## The per-tick driver, mirroring the capture lane's: physics ticks run
## the scenario clock (the input adapter drains any authored waits),
## process frames paint the chip and pin due beats.
class CalibrationDriver:
	extends Node

	var mode

	func _physics_process(_delta: float) -> void:
		var harness = mode
		if not harness.ready or harness.failed or harness.busy_capturing:
			return
		harness.drive_tick()

	func _process(_delta: float) -> void:
		var harness = mode
		if harness.failed:
			return
		harness.frame += 1
		harness.chip.set_code(harness.tick, harness.frame)
		if harness.frame > harness.scenario.max_frames + 900:
			harness._fail("hard frame budget exhausted")
			return
		if not harness.ready or harness.busy_capturing or harness.pending_captures.is_empty():
			return
		harness.capture_next_beat()
