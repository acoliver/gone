extends SimTestCase
## Pins the test runner's captured-output classifier (issue #51): script
## errors and silently-dropped 3.x property sets must fail the run, while
## the intentional malformed-JSON test noise and ordinary engine output
## must stay clean.

const Runner := preload("res://tests/run_tests.gd")

func test_script_error_lines_are_violations() -> void:
	assert_true(Runner.classify_line("SCRIPT ERROR: Invalid access to property or key 'uv1_triplanar_enabled' on a base object of type 'StandardMaterial3D'.") == "script-error", "runtime property-access abort must be a violation")
	assert_true(Runner.classify_line("SCRIPT ERROR: Out of bounds get index '1' (on base: 'Array')") == "script-error", "runtime index abort must be a violation")
	assert_true(Runner.classify_line("SCRIPT ERROR: Parse Error: Native class \"BaseMaterial3D\" cannot be constructed as it is abstract.") == "script-error", "load-time parse errors must be a violation")
	assert_true(Runner.classify_line("USER SCRIPT ERROR: deliberate push_error output") == "script-error", "push_error output must be a violation")

func test_remap_warning_is_a_violation() -> void:
	assert_true(Runner.classify_line("WARNING: Godot 3.x SpatialMaterial remapped parameter not found: uv1_triplanar_enabled") == "remap-warning", "silently dropped 3.x property set must be a violation")

func test_intentional_json_noise_is_clean() -> void:
	assert_true(Runner.classify_line("ERROR: Parse JSON failed. Error at line 0: Expected key") == "", "malformed-JSON test noise must stay clean")

func test_ordinary_output_is_clean() -> void:
	assert_true(Runner.classify_line("Godot Engine v4.7.2.stable.official.ed1daf0bf - https://godotengineering.org") == "", "engine banner must stay clean")
	assert_true(Runner.classify_line("passed=238 failed=0") == "", "tally line must stay clean")
	assert_true(Runner.classify_line("   at: parse_string (core/io/json.cpp:629)") == "", "engine backtrace lines must stay clean")
	assert_true(Runner.classify_line("WARNING: 9 RIDs of type \"Canvas\" were leaked.") == "", "engine teardown warnings must stay clean")
	assert_true(Runner.classify_line("ERROR: 180 RID allocations of type 'N17RendererSceneCull8InstanceE' were leaked at exit.") == "", "engine teardown errors must stay clean")
	assert_true(Runner.classify_line("") == "", "empty lines must stay clean")
