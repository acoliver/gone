extends SimTestCase

class Lane:
	extends RefCounted
	var ready: bool = true
	var failed: bool = false
	var busy_capturing: bool = false
	var pending_captures: Array = []
	var ticks: int = 0
	func drive_tick() -> void:
		ticks += 1

func test_queued_label_capture_stops_physics_before_render_starts_capture() -> void:
	var driver = load("res://app/harness_mode.gd").Driver.new()
	var lane := Lane.new()
	driver.mode = lane
	driver._physics_process(Sim.LOGICAL_TICK_SECS)
	assert_int_equal(lane.ticks, 1, "ordinary physics advances")
	lane.pending_captures.append({"name": "console-inactive", "tick": 3043})
	for tick: int in range(8): driver._physics_process(Sim.LOGICAL_TICK_SECS)
	assert_int_equal(lane.ticks, 1, "a queued capture freezes later input before _process can start readback")
	lane.pending_captures.clear()
	lane.busy_capturing = true
	driver._physics_process(Sim.LOGICAL_TICK_SECS)
	assert_int_equal(lane.ticks, 1, "in-flight readback still freezes physics")
	lane.busy_capturing = false
	driver._physics_process(Sim.LOGICAL_TICK_SECS)
	assert_int_equal(lane.ticks, 2, "physics resumes after capture")
	driver.free()
