extends SimTestCase

class PowerVerifier:
	extends "res://harness/run.gd"
	func _initialize() -> void:
		pass

func _report(red: float, white: float) -> Dictionary:
	return {
		"beats": {"hall-white": {"tick": 100}},
		"events": [
			{"kind": "hallway", "tick": 100, "white": true, "white_level": 1.0},
			{"kind": "power", "tick": 100, "stasis_red_level": red,
			 "stasis_white_level": white, "power_white_level": 1.0, "bay_smoke_density": 0.0},
		],
	}

func test_power_evidence_requires_bay_white_instead_of_emergency_red() -> void:
	var verifier := PowerVerifier.new()
	verifier.verify_power(_report(0.0, 1.0))
	assert_int_equal(verifier.failures.size(), 0, "white bay and power room pass")
	verifier.free()

func test_power_evidence_rejects_remaining_bay_smoke() -> void:
	var report := _report(0.0, 1.0)
	report.events[1].bay_smoke_density = 0.1
	var verifier := PowerVerifier.new()
	verifier.verify_power(report)
	assert_int_equal(verifier.failures.size(), 1, "settled bay cannot retain smoke")
	verifier.free()

func test_power_evidence_rejects_bay_red_and_darkness() -> void:
	for levels: Vector2 in [Vector2(1, 0), Vector2(1, 1), Vector2(0, 0)]:
		var verifier := PowerVerifier.new()
		verifier.verify_power(_report(levels.x, levels.y))
		assert_int_equal(verifier.failures.size(), 1, "bay must extinguish red and light white")
		verifier.free()

func test_inactive_capture_precedes_the_first_console_press() -> void:
	for press_tick: int in [100, 101]:
		var verifier := PowerVerifier.new()
		verifier.verify_power({
			"beats": {"console-inactive": {"tick": 100}},
			"events": [
				{"kind": "console", "tick": 1, "presses": 0, "state": "inactive", "native_label": "te mu nawa lina palo", "perceived_label": "SISTEMA DE ENERGÍA SECUNDARIO INACTIVO"},
				{"kind": "console", "tick": press_tick, "presses": 1, "state": "active", "native_label": "te mu nawa lina shenu", "perceived_label": "SISTEMA DE ENERGÍA SECUNDARIO EN FUNCIONAMIENTO"},
			],
		})
		assert_int_equal(verifier.failures.size(), 1 if press_tick == 100 else 0, "arrival capture must precede activation, not merely have an earlier inactive event")
		verifier.free()
