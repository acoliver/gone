extends SceneTree
## The harness runner, ported from gone_harness's bin (run.rs/app.rs):
## computes the identity hashes, spawns the WINDOWED app in harness mode
## with the env contract, waits, then machine-verifies the run — report
## version, hash echo, every declared beat's PNG decodes with a chip
## matching its (tick, frame), per-beat luminance/red-dominance stats,
## wake-phase progression, door-open and hallway-light evidence — and
## prints the two-stage verdict. Exit 0 only on machine PASS.
## Run: godot --headless --path . -s harness/run.gd -- <scenario.json> [--out <dir>]

const Protocol := preload("res://harness/protocol.gd")
const ScenarioModule := preload("res://harness/scenario.gd")
const ReportModule := preload("res://harness/report.gd")
const PerfPolicyModule := preload("res://harness/perf_policy.gd")
const CalibrationModule := preload("res://harness/calibration.gd")
const CalibrationAssertions := preload("res://harness/calibration_assertions.gd")

const TIMEOUT_SECONDS: float = 300.0
const PERF_POLICY_PATH: String = "res://harness/perf-policy.json"
const DARK_MAX_LUMA: float = 0.06
const LIT_MIN_LUMA: float = 0.008
const LIT_MIN_RED: float = 0.02
const BEAT_TICK_HEADROOM: int = 40
const WAKE_PROGRESSION: Array[String] = ["waking", "awake_in_pod", "exiting_pod", "standing"]

var project_root: String
var run_dir: String
var scenario_path: String
var scenario
var failures: Array[String] = []
var beat_lines: Array[String] = []
var perf_policy
var perf_policy_text: String = ""

func _initialize() -> void:
	project_root = ProjectSettings.globalize_path("res://")
	var args := ParsedArgs.parse(OS.get_cmdline_user_args())
	if args.error != "":
		print("harness/run: %s" % args.error)
		print("usage: godot --headless --path . -s harness/run.gd -- <scenario.json> [--out <dir>]")
		quit(2)
		return
	scenario_path = args.scenario
	if not scenario_path.is_absolute_path():
		scenario_path = ProjectSettings.globalize_path(scenario_path)
	var scenario_text := FileAccess.get_file_as_string(scenario_path)
	if scenario_text.is_empty():
		print("harness/run: cannot read scenario %s" % scenario_path)
		quit(2)
		return
	var parsed: Dictionary = ScenarioModule.parse(scenario_text)
	if parsed.error != "":
		print("harness/run: %s" % parsed.error)
		quit(2)
		return
	scenario = parsed.scenario
	var run_parent: String = args.out_dir
	if run_parent.is_empty():
		run_parent = ProjectSettings.globalize_path("tmp/harness").path_join(scenario.scenario_name)
	run_dir = run_parent.path_join("run-%d" % int(Time.get_unix_time_from_system()))
	DirAccess.make_dir_recursive_absolute(run_dir)
	DirAccess.make_dir_recursive_absolute(run_dir.path_join("beats"))
	var scenario_file := FileAccess.open(run_dir.path_join("scenario.json"), FileAccess.WRITE)
	scenario_file.store_string(scenario_text)
	scenario_file.close()
	_run()

func _run() -> void:
	var scenario_hash := Protocol.sha256_file(scenario_path)
	var config_hash := scenario_hash
	var app_hash := Protocol.app_hash(project_root)
	var app_script: String = project_root.path_join("app/harness_mode.gd")
	var resolution: String = "480x270"
	var policy_path: String = ""
	if scenario.mode == "calibration":
		app_script = project_root.path_join("app/calibration_mode.gd")
	elif scenario.mode == "perf":
		policy_path = ProjectSettings.globalize_path(PERF_POLICY_PATH)
		perf_policy_text = FileAccess.get_file_as_string(policy_path)
		var parsed_policy: Dictionary = PerfPolicyModule.parse_policy(perf_policy_text)
		if parsed_policy.error != "":
			_fail_setup(parsed_policy.error)
			return
		perf_policy = parsed_policy.policy
		resolution = "%dx%d" % [int(perf_policy.resolution.width), int(perf_policy.resolution.height)]
		OS.set_environment(Protocol.ENV_PERF_POLICY, policy_path)
	OS.set_environment(Protocol.ENV_HARNESS, "1")
	OS.set_environment(Protocol.ENV_SCENARIO, scenario_path)
	OS.set_environment(Protocol.ENV_OUT_DIR, run_dir)
	OS.set_environment(Protocol.ENV_APP_HASH, app_hash)
	OS.set_environment(Protocol.ENV_SCENARIO_HASH, scenario_hash)
	OS.set_environment(Protocol.ENV_CONFIG_HASH, config_hash)
	var arguments := PackedStringArray(["--path", project_root, "--resolution", resolution,
		"-s", app_script])
	var pid := OS.create_process(OS.get_executable_path(), arguments)
	if pid < 0:
		_fail_setup("cannot spawn the app process")
		return
	print("spawned app pid %d (scenario `%s`, out %s)" % [pid, scenario.scenario_name, run_dir])
	var waited: float = 0.0
	var timed_out := false
	while OS.is_process_running(pid):
		if waited >= TIMEOUT_SECONDS:
			timed_out = true
			OS.kill(pid)
			break
		await create_timer(0.5).timeout
		waited += 0.5
	for key: String in [Protocol.ENV_HARNESS, Protocol.ENV_SCENARIO, Protocol.ENV_OUT_DIR,
			Protocol.ENV_APP_HASH, Protocol.ENV_SCENARIO_HASH, Protocol.ENV_CONFIG_HASH,
			Protocol.ENV_PERF_POLICY]:
		OS.unset_environment(key)
	if timed_out:
		_fail_setup("app did not exit within %.0fs; killed" % TIMEOUT_SECONDS)
		return
	verify_run(app_hash, scenario_hash, config_hash)
	_verdict()

func _fail_setup(what: String) -> void:
	failures.append(what)
	_verdict()

func verify_run(app_hash: String, scenario_hash: String, config_hash: String) -> void:
	var path := run_dir.path_join("report.json")
	var text := FileAccess.get_file_as_string(path)
	if text.is_empty():
		failures.append("no report.json at %s" % path)
		return
	var parsed: Dictionary = ReportModule.parse(text)
	if parsed.error != "":
		failures.append(parsed.error)
		return
	var report = parsed.report
	if report.protocol_version != Protocol.PROTOCOL_VERSION:
		failures.append("protocol version %d != %d" % [report.protocol_version, Protocol.PROTOCOL_VERSION])
	if report.scenario != scenario.scenario_name:
		failures.append("report scenario `%s` != `%s`" % [report.scenario, scenario.scenario_name])
	if report.identity.app_hash != app_hash:
		failures.append("app hash echo mismatch")
	if report.identity.scenario_hash != scenario_hash:
		failures.append("scenario hash echo mismatch")
	if report.identity.config_hash != config_hash:
		failures.append("config hash echo mismatch")
	if report.ready_frame() < 0:
		failures.append("no ready event")
	if not report.first_failure().is_empty():
		failures.append("app reported failure: %s" % report.first_failure())
	var missing := Protocol.verify_beats(
		report.beats.keys().map(func(name: String) -> Dictionary:
			return {"name": name, "tick": report.beats[name].tick}),
		scenario.beats)
	if not missing.is_empty():
		failures.append(missing)
	for beat: Dictionary in scenario.beats:
		verify_beat(report, beat, scenario.mode == "capture")
	if scenario.mode == "capture":
		verify_wake_progression(report)
		verify_door_open(report)
		verify_hallway(report)
		verify_rod_pickup(report)
	elif scenario.mode == "perf":
		verify_perf(report)
	else:
		verify_calibration(report)

func verify_beat(report, beat: Dictionary, check_stats: bool) -> void:
	var name: String = beat.name
	if not report.beats.has(name):
		return
	var entry: Dictionary = report.beats[name]
	var path := run_dir.path_join(entry.file)
	var image := Image.new()
	if image.load(path) != OK:
		failures.append("beat `%s` PNG does not decode: %s" % [name, entry.file])
		return
	var decoded: Dictionary = Protocol.decode_chip(image)
	if not decoded.ok:
		failures.append("beat `%s` chip: %s" % [name, decoded.error])
		return
	if decoded.tick != entry.tick or decoded.frame != entry.frame:
		failures.append("beat `%s` chip (%d,%d) != report (%d,%d)" % [
			name, decoded.tick, decoded.frame, entry.tick, entry.frame])
	if entry.tick < beat.tick - 2 or entry.tick > beat.tick + BEAT_TICK_HEADROOM:
		failures.append("beat `%s` tick %d not correlated to scripted tick %d" % [
			name, entry.tick, beat.tick])
	if check_stats:
		verify_beat_stats(name, image, entry)

## The perf lane's machine checks: the report's perf section must match
## the frozen policy's shape (window echoed, resolution echoed, sample
## count met) and every recorded statistic must hold its threshold. The
## verdict lands in perf-verdict.json beside the report.
func verify_perf(report) -> void:
	var shape: String = PerfPolicyModule.verify_run_shape(perf_policy, report.perf)
	if not shape.is_empty():
		failures.append(shape)
	var stats: Dictionary = report.perf.get("stats", {})
	var breaches: Array = PerfPolicyModule.violations(perf_policy.thresholds, stats)
	for breach: Dictionary in breaches:
		failures.append("perf threshold breach: %s %.3f exceeds limit %.3f" % [
			breach.statistic, breach.observed_ms, breach.limit_ms])
	var verdict := {
		"passed": shape.is_empty() and breaches.is_empty(),
		"policy": PerfPolicyModule.policy_identity(perf_policy,
			Protocol.sha256_hex(perf_policy_text.to_utf8_buffer())),
		"violations": breaches,
		"stats": stats,
	}
	var file := FileAccess.open(run_dir.path_join("perf-verdict.json"), FileAccess.WRITE)
	if file != null:
		file.store_string(JSON.stringify(verdict, "	"))
		file.close()
	beat_lines.append(PerfPolicyModule.distribution_line(stats))
	beat_lines.append("perf policy `%s` (warmup %d, samples %d, %dx%d)" % [
		perf_policy.policy_version, int(perf_policy.warmup_frames),
		int(perf_policy.sample_frames), int(perf_policy.resolution.width),
		int(perf_policy.resolution.height)])

## The calibration lane's machine checks, ported from calibration_lane:
## the setup evidence (Calibration event) must precede the first pinned
## sample, the mask identity must match the shipped mask's pixels, the
## placements must match the plan, and the predeclared assertion table
## must pass over the measured capture sequence.
func verify_calibration(report) -> void:
	var params: Dictionary = scenario.calibration
	var calibration_index := -1
	var first_beat_index := -1
	for index: int in range(report.events.size()):
		var kind: String = String(report.events[index].kind)
		if kind == "calibration" and calibration_index < 0:
			calibration_index = index
		elif kind == "beat" and first_beat_index < 0:
			first_beat_index = index
	if calibration_index < 0:
		failures.append("no calibration event: the setup evidence is missing")
		return
	if first_beat_index >= 0 and calibration_index > first_beat_index:
		failures.append("calibration evidence was recorded after the first pinned sample")
	var evidence: Dictionary = report.events[calibration_index].evidence
	var mask_image := Image.new()
	var mask_bytes := FileAccess.get_file_as_bytes(ProjectSettings.globalize_path(
		CalibrationModule.mask_path(String(params.mask))))
	if mask_bytes.is_empty() or mask_image.load_png_from_buffer(mask_bytes) != OK:
		failures.append("runner cannot decode the shipped metering mask")
		return
	var mask_sha := Protocol.sha256_hex(mask_image.get_data())
	if mask_sha != String(evidence.mask_sha256):
		failures.append("calibration mask sha256 %s != evidence %s" % [mask_sha, evidence.mask_sha256])
	var beat_ticks: Array = scenario.beats.map(func(beat: Dictionary) -> int: return int(beat.tick))
	beat_ticks.sort()
	var evidence_ticks: Array = []
	for value in evidence.sample_ticks:
		evidence_ticks.append(int(value))
	if evidence_ticks != beat_ticks:
		failures.append("calibration sample_ticks %s != scenario beat ticks %s" % [
			str(evidence_ticks), str(beat_ticks)])
	var plan_placements := CalibrationModule.patch_placements(params.patch).map(
		func(placement: Dictionary) -> Array: return [int(placement.tick), String(placement.slot)])
	var evidence_placements: Array = []
	for placement: Dictionary in evidence.patch_placements:
		evidence_placements.append([int(placement.tick), String(placement.slot)])
	if evidence_placements != plan_placements:
		failures.append("calibration patch placements %s != plan %s" % [
			str(evidence_placements), str(plan_placements)])
	var samples: Array = []
	for beat: Dictionary in scenario.beats:
		var entry: Dictionary = report.beats.get(beat.name, {})
		if entry.is_empty():
			continue
		var image := Image.new()
		if image.load(run_dir.path_join(entry.file)) != OK:
			failures.append("beat `%s` PNG does not decode: %s" % [beat.name, entry.file])
			return
		samples.append({"tick": int(entry.tick), "mean_linear": measure_mean_linear(image)})
	if samples.size() != scenario.beats.size():
		failures.append("calibration measured %d of %d declared samples" % [
			samples.size(), scenario.beats.size()])
		return
	var perturb_tick := int(params.step.tick)
	if String(params.cell) == "C" or String(params.cell) == "D":
		var move_at = CalibrationModule.move_tick(params.patch)
		if move_at != null:
			perturb_tick = int(move_at)
	var outcomes: Array = CalibrationAssertions.evaluate_cell(String(params.cell), samples, perturb_tick)
	for outcome: Dictionary in outcomes:
		if not outcome.passed:
			failures.append("calibration assertion `%s` failed: expected %s; %s" % [
				outcome.name, outcome.expected, outcome.measured])
	beat_lines.append_array(CalibrationAssertions.summarize(outcomes))
	beat_lines.append("calibration mask `%s` sha256 %s (auto_exposure %s, cell %s)" % [
		params.mask, mask_sha.left(16), str(params.auto_exposure), params.cell])

## Rec.709 mean linear luminance over a whole capture (sRGB-decoded),
## the calibration lane's measurement, ported from measurement.rs.
func measure_mean_linear(image: Image) -> float:
	var total: float = 0.0
	var count: int = 0
	for y: int in range(image.get_height()):
		for x: int in range(image.get_width()):
			var color := image.get_pixel(x, y).srgb_to_linear()
			total += 0.2126 * color.r + 0.7152 * color.g + 0.0722 * color.b
			count += 1
	return total / float(count) if count > 0 else 0.0

## Per-beat machine checks on the view outside the chip: the eyes-closed
## beat is dark (the eyelid pass closes over an unlit room) and the
## hall-dark beat is dark (the hallway is unlit until its switch flips),
## while every other lit beat is nonblack and red-dominant (the rooms'
## emergency lighting).
func verify_beat_stats(name: String, image: Image, entry: Dictionary) -> void:
	var chip: Vector2i = Protocol.chip_size()
	var samples: int = 0
	var luma_sum: float = 0.0
	var red_sum: float = 0.0
	var green_sum: float = 0.0
	var blue_sum: float = 0.0
	for y: int in range(image.get_height()):
		for x: int in range(chip.x, image.get_width()):
			var color := image.get_pixel(x, y)
			luma_sum += color.get_luminance()
			red_sum += color.r
			green_sum += color.g
			blue_sum += color.b
			samples += 1
	if samples == 0:
		failures.append("beat `%s` has no pixels outside the chip" % name)
		return
	var luma := luma_sum / samples
	var red := red_sum / samples
	var green := green_sum / samples
	var blue := blue_sum / samples
	beat_lines.append("beat `%s` tick %d frame %d: luma %.4f r/g/b %.4f/%.4f/%.4f" % [
		name, entry.tick, entry.frame, luma, red, green, blue])
	if name == "eyes-closed" or name == "hall-dark":
		if luma >= DARK_MAX_LUMA:
			failures.append("beat `%s` not dark: luma %.4f >= %.2f" % [name, luma, DARK_MAX_LUMA])
		return
	if luma <= LIT_MIN_LUMA:
		failures.append("beat `%s` is black: luma %.4f" % [name, luma])
	if red < LIT_MIN_RED or red < green or red < blue:
		failures.append("beat `%s` not red-dominant: r/g/b %.4f/%.4f/%.4f" % [name, red, green, blue])

func verify_wake_progression(report) -> void:
	var names: Array = []
	var last_tick := -1
	for event: Dictionary in report.events:
		if event.kind == "wake_phase":
			names.append(event.phase)
			if int(event.tick) < last_tick:
				failures.append("wake phase ticks regress at `%s` (tick %d after %d)" % [
					event.phase, event.tick, last_tick])
			last_tick = int(event.tick)
	if names != WAKE_PROGRESSION:
		failures.append("wake progression %s != %s" % [str(names), str(WAKE_PROGRESSION)])

## The door-opened beat's machine check: the beat needs a door_open
## event with the opening counted and the doorway open, captured with
## the beat. Scenarios without the beat skip it.
func verify_door_open(report) -> void:
	if not report.beats.has("door-opened"):
		return
	var door_tick: int = report.beats["door-opened"].tick
	for event: Dictionary in report.events:
		if event.kind == "door_open" and int(event.openings) >= 1 and bool(event.open) \
				and int(event.tick) <= door_tick + BEAT_TICK_HEADROOM:
			return
	failures.append("door-opened beat has no open-door evidence at or before tick %d" % door_tick)

## The hallway beats' machine checks, in the same shape: hall-dark needs
## hallway evidence with the circuit still unlit at or before the beat,
## hall-lit needs evidence with the circuit on. Scenarios without the
## beats skip them.
func verify_hallway(report) -> void:
	if report.beats.has("hall-dark"):
		var dark_tick: int = report.beats["hall-dark"].tick
		var dark_ok := false
		for event: Dictionary in report.events:
			if event.kind == "hallway" and not bool(event.lit) \
					and int(event.tick) <= dark_tick + BEAT_TICK_HEADROOM:
				dark_ok = true
				break
		if not dark_ok:
			failures.append("hall-dark beat has no unlit-hallway evidence at or before tick %d" % dark_tick)
	if report.beats.has("hall-lit"):
		var lit_tick: int = report.beats["hall-lit"].tick
		var lit_ok := false
		for event: Dictionary in report.events:
			if event.kind == "hallway" and bool(event.lit) \
					and int(event.tick) <= lit_tick + BEAT_TICK_HEADROOM:
				lit_ok = true
				break
		if not lit_ok:
			failures.append("hall-lit beat has no lit-hallway evidence at or before tick %d" % lit_tick)

## The rod-pickup beat's machine check, mirroring the refusal evidence:
## the beat needs a rod_pickup event with the carried flag set, captured
## with the beat. Scenarios without the beat (gameplay-full) skip it.
func verify_rod_pickup(report) -> void:
	if not report.beats.has("rod-picked-up"):
		return
	var beat_tick: int = report.beats["rod-picked-up"].tick
	for event: Dictionary in report.events:
		if event.kind == "rod_pickup" and bool(event.carried) and int(event.tick) <= beat_tick + BEAT_TICK_HEADROOM:
			return
	failures.append("rod-picked-up beat has no carried evidence at or before tick %d" % beat_tick)

func _verdict() -> void:
	var passed := failures.is_empty()
	var verdict := "scenario `%s`: %s\n%s\nmachine: %s\nvisual: PENDING (needs Eyes subagent)" % [
		scenario.scenario_name,
		"machine checks passed, visual verification pending" if passed else "machine checks failed",
		"\n".join(failures) if not passed else "",
		"PASS" if passed else "FAIL"]
	for line: String in beat_lines:
		verdict += "\n" + line
	verdict += "\nARTIFACTS: %s" % run_dir
	var file := FileAccess.open(run_dir.path_join("verdict.txt"), FileAccess.WRITE)
	if file != null:
		file.store_string(verdict + "\n")
		file.close()
	print(verdict)
	quit(0 if passed else 1)

## Tiny CLI parse: first non-flag argument is the scenario path, --out
## names the parent output directory.
class ParsedArgs:
	extends RefCounted

	var scenario: String = ""
	var out_dir: String = ""
	var error: String = ""

	static func parse(args: PackedStringArray) -> ParsedArgs:
		var result := new()
		var index := 0
		while index < args.size():
			var arg := args[index]
			if arg == "--out":
				index += 1
				if index >= args.size():
					result.error = "--out needs a value"
					return result
				result.out_dir = args[index]
			elif arg.begins_with("--"):
				result.error = "unknown flag `%s`" % arg
				return result
			elif result.scenario.is_empty():
				result.scenario = arg
			else:
				result.error = "unexpected argument `%s`" % arg
				return result
			index += 1
		if result.scenario.is_empty():
			result.error = "no scenario given"
		if not result.out_dir.is_empty():
			result.out_dir = ProjectSettings.globalize_path(result.out_dir)
		return result
