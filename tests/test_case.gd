class_name SimTestCase
extends RefCounted
## Minimal assert helper. The first failed assertion of the current test
## is recorded in `failure`; the runner resets it per test and reads it
## afterwards. Only the first message per test is kept, matching the
## Rust assert's first-failure abort.

var failure: String = ""

func begin_test() -> void:
	failure = ""

func _fail(message: String) -> void:
	if failure == "":
		failure = message

func assert_true(condition: bool, message: String = "expected true") -> void:
	if not condition:
		_fail(message)

func assert_false(condition: bool, message: String = "expected false") -> void:
	if condition:
		_fail(message)

func assert_int_equal(actual: int, expected: int, message: String) -> void:
	if actual != expected:
		_fail("%s: expected %d, got %d" % [message, expected, actual])

func assert_float_equal(actual: float, expected: float, message: String) -> void:
	if actual != expected:
		_fail("%s: expected %s, got %s" % [message, str(expected), str(actual)])

func assert_vec3_equal(actual: Vector3, expected: Vector3, message: String) -> void:
	if actual != expected:
		_fail("%s: expected %s, got %s" % [message, str(expected), str(actual)])

func assert_close(actual: Vector3, expected: Vector3, message: String) -> void:
	var drift: Vector3 = (actual - expected).abs()
	if not (drift.x < 1e-3 and drift.y < 1e-3 and drift.z < 1e-3):
		_fail("%s: expected %s, resolved %s" % [message, str(expected), str(actual)])

func assert_vec3_array_equal(actual: Array, expected: Array, message: String) -> void:
	if actual.size() != expected.size():
		_fail("%s: expected %d normals, got %d" % [message, expected.size(), actual.size()])
		return
	for index: int in range(expected.size()):
		if actual[index] != expected[index]:
			_fail("%s: expected %s, got %s" % [message, str(expected[index]), str(actual[index])])
			return

func assert_float_in_range(value: float, low: float, high: float, message: String) -> void:
	if not (low <= value and value <= high):
		_fail("%s: %s not in [%s, %s]" % [message, str(value), str(low), str(high)])
