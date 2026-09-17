extends SceneTree
## The harness runner, ported from gone_harness's bin (run.rs/app.rs):
## computes the identity hashes, spawns the WINDOWED app in harness mode
## with the env contract, waits, then machine-verifies the run — report
## version, hash echo, every declared beat's PNG decodes with a chip
## matching its (tick, frame), per-beat luminance/red-dominance stats,
## wake-phase progression, refusal evidence — and prints the two-stage
## verdict. Exit 0 only on machine PASS.
## Run: godot --headless --path . -s harness/run.gd -- <scenario.json> [--out <dir>]

const Protocol := preload("res://harness/protocol.gd")
const ScenarioModule := preload("res://harness/scenario.gd")
const ReportModule := preload("res://harness/report.gd")

const TIMEOUT_SECONDS: float = 300.0
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
	OS.set_environment(Protocol.ENV_HARNESS, "1")
	OS.set_environment(Protocol.ENV_SCENARIO, scenario_path)
	OS.set_environment(Protocol.ENV_OUT_DIR, run_dir)
	OS.set_environment(Protocol.ENV_APP_HASH, app_hash)
	OS.set_environment(Protocol.ENV_SCENARIO_HASH, scenario_hash)
	OS.set_environment(Protocol.ENV_CONFIG_HASH, config_hash)
	var arguments := PackedStringArray(["--path", project_root, "--resolution", "480x270",
		"-s", project_root.path_join("app/harness_mode.gd")])
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
			Protocol.ENV_APP_HASH, Protocol.ENV_SCENARIO_HASH, Protocol.ENV_CONFIG_HASH]:
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
		verify_beat(report, beat)
	verify_wake_progression(report)
	verify_refusal(report)

func verify_beat(report, beat: Dictionary) -> void:
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
	verify_beat_stats(name, image, entry)

## Per-beat machine checks on the view outside the chip: the eyes-closed
## beat is dark (the eyelid pass closes over an unlit room), every lit
## beat is nonblack and red-dominant (the room's emergency lighting).
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
	if name == "eyes-closed":
		if luma >= DARK_MAX_LUMA:
			failures.append("beat `eyes-closed` not dark: luma %.4f >= %.2f" % [luma, DARK_MAX_LUMA])
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

func verify_refusal(report) -> void:
	if not report.beats.has("door-refused"):
		return
	var door_tick: int = report.beats["door-refused"].tick
	for event: Dictionary in report.events:
		if event.kind == "refusal" and int(event.count) >= 1 and int(event.tick) <= door_tick + BEAT_TICK_HEADROOM:
			return
	failures.append("door-refused beat has no refusal evidence at or before tick %d" % door_tick)

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
