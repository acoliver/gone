extends SceneTree
## Auto-discovering test runner. Loads every tests/*_test.gd, runs each
## test_* method, prints per-failure file/function/message plus a final
## "passed=X failed=Y" tally, and exits with code 1 on any failure.
## Run: godot --headless --path . -s tests/run_tests.gd
##
## Script-error guard (issue #51): a GDScript runtime error (reading a
## nonexistent property, out-of-bounds index, ...) aborts the test method,
## but Object.call() swallows the abort, so the runner counted the test as
## passed while Godot only printed "SCRIPT ERROR: ..." on stderr. A
## process cannot capture its own stderr, so the runner re-execs itself
## through /bin/sh as a guarded child (GONE_TEST_RUNNER_CHILD=1), captures
## the child's stdout/stderr into files, re-streams them, and fails the
## run when the captured output matches the violation rules pinning
## classify_line(): script errors, and "Godot 3.x ... remapped parameter
## not found" warnings (silently dropped property assignments).

const _GUARD_ENV := "GONE_TEST_RUNNER_CHILD"

func _init() -> void:
	if OS.get_environment(_GUARD_ENV) == "1":
		_run_tests()
	else:
		_run_guarded()

func _run_guarded() -> void:
	var project_dir := ProjectSettings.globalize_path("res://")
	var script_path := ProjectSettings.globalize_path(get_script().resource_path)
	var log_dir := ProjectSettings.globalize_path("user://test-runner/%d" % OS.get_process_id())
	if DirAccess.make_dir_recursive_absolute(log_dir) != OK:
		push_error("test runner: cannot create %s" % log_dir)
		quit(1)
		return
	var out_path := log_dir + "/child.out"
	var err_path := log_dir + "/child.err"
	# OS.execute routes capture-mode spawns through a shell layer whose
	# quoting drops extra argv operands (and mangles double quotes), so
	# the whole command must live in one single-quoted -c string. The
	# VAR=1 prefix exports the guard to the exec'd child only; the two
	# redirections keep the child's stdout and stderr separate so the
	# parent can re-emit each on the matching stream.
	var command := "%s=1 exec %s --headless --path %s -s %s > %s 2> %s" % [
		_GUARD_ENV,
		_shell_quote(OS.get_executable_path()),
		_shell_quote(project_dir),
		_shell_quote(script_path),
		_shell_quote(out_path),
		_shell_quote(err_path),
	]
	var captured: Array = []
	var exit_code := OS.execute("/bin/sh", ["-c", command], captured, false)
	var child_stdout := FileAccess.get_file_as_string(out_path)
	var child_stderr := FileAccess.get_file_as_string(err_path)
	DirAccess.remove_absolute(out_path)
	DirAccess.remove_absolute(err_path)
	DirAccess.remove_absolute(log_dir)
	var tally_passed := -1
	var tally_failed := -1
	var violations := 0
	for line: String in _lines(child_stdout):
		if line.begins_with("passed=") and " failed=" in line:
			var fields := line.split(" ")
			if fields.size() == 2:
				tally_passed = fields[0].trim_prefix("passed=").to_int()
				tally_failed = fields[1].trim_prefix("failed=").to_int()
				continue
		print(line)
		var stdout_rule := classify_line(line)
		if stdout_rule != "":
			violations += 1
			print("RUNNER VIOLATION (%s): %s" % [stdout_rule, line])
	for line: String in _lines(child_stderr):
		printerr(line)
		var stderr_rule := classify_line(line)
		if stderr_rule != "":
			violations += 1
			print("RUNNER VIOLATION (%s): %s" % [stderr_rule, line])
	if tally_passed >= 0:
		print("passed=%d failed=%d" % [tally_passed, tally_failed + violations])
	elif violations > 0:
		print("passed=0 failed=%d" % violations)
	if violations > 0 and exit_code == 0:
		exit_code = 1
	quit(exit_code)

func _run_tests() -> void:
	var passed := 0
	var failed := 0
	var test_files: Array[String] = []
	var directory := DirAccess.open("res://tests")
	if directory == null:
		push_error("cannot open res://tests")
		quit(1)
		return
	directory.list_dir_begin()
	var entry := directory.get_next()
	while entry != "":
		if entry.ends_with("_test.gd"):
			test_files.append(entry)
		entry = directory.get_next()
	directory.list_dir_end()
	test_files.sort()
	for test_file: String in test_files:
		var script: GDScript = load("res://tests/" + test_file)
		if script == null or not script.can_instantiate():
			print("FAIL %s :: <load> :: cannot load test script" % test_file)
			failed += 1
			continue
		var instance: SimTestCase = script.new()
		var method_names: Array[String] = []
		for method: Dictionary in script.get_script_method_list():
			var method_name: String = method["name"]
			if method_name.begins_with("test_"):
				method_names.append(method_name)
		method_names.sort()
		for method_name: String in method_names:
			instance.begin_test()
			instance.call(method_name)
			if instance.failure == "":
				passed += 1
			else:
				failed += 1
				print("FAIL %s :: %s :: %s" % [test_file, method_name, instance.failure])
	print("passed=%d failed=%d" % [passed, failed])
	quit(1 if failed > 0 else 0)

static func classify_line(line: String) -> String:
	## Classifies one captured output line: "" for clean output,
	## "script-error" or "remap-warning" when the line must fail the run.
	if _intentional_json_noise(line):
		return ""
	if line.contains("SCRIPT ERROR:"):
		return "script-error"
	if line.contains("Godot 3.x") and line.contains("remapped parameter not found"):
		return "remap-warning"
	return ""

static func _intentional_json_noise(line: String) -> bool:
	## harness_test.gd (test_report_parse_rejects_malformed_input) and
	## perf_test.gd (test_policy_parse_rejects_malformed_json) feed
	## malformed JSON to JSON.parse_string on purpose; the engine's parse
	## failure line is expected noise, not a failure.
	return line.begins_with("ERROR: Parse JSON failed.")

static func _lines(text: String) -> PackedStringArray:
	if text == "":
		return PackedStringArray()
	return text.trim_suffix("\n").split("\n")

static func _shell_quote(path: String) -> String:
	return "'" + path.replace("'", "'\\''") + "'"
