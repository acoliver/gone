class_name QuartersCapture
extends RefCounted

const REQUIRED: Array[String] = ["corridor-door", "remembered-doorway", "remembered-wide", "remembered-console", "remembered-bed", "console-corruption", "console-message", "console-fault", "present-doorway", "present-wide", "present-console", "present-bed", "remembered-bedside", "present-bedside", "remembered-table", "present-table", "remembered-desk", "present-desk", "remembered-boots", "present-boots"]

static func pose(camera: Camera3D, view: String) -> void:
	var plan := QuartersInventory.plan()
	var point: Vector3
	var target: Vector3
	if view == "doorway":
		point = Vector3(plan.camera.position[0], plan.camera.position[1], plan.camera.position[2])
		target = Vector3(plan.camera.look_at[0], plan.camera.look_at[1], plan.camera.look_at[2])
	elif view == "console":
		point = Vector3(6.1, 1.6, 2.6)
		target = Vector3(7.65, 1.05, 2.0)
	elif view == "bed":
		point = Vector3(2.5, 2.4, 2.25)
		target = Vector3(4.0, 0.3, 4.6)
	elif view == "bedside":
		point = Vector3(5.1, 0.95, 5.0)
		target = Vector3(5.14, 0.53, 5.74)
	elif view == "boots":
		point = Vector3(5.65, 0.65, 4.45)
		target = Vector3(5.06, 0.16, 5.28)
	elif view == "table":
		point = Vector3(4.2, 1.6, 0.9)
		target = Vector3(5.15, 0.78, 1.7)
	elif view == "desk":
		point = Vector3(6.6, 1.65, 3.25)
		target = Vector3(7.65, 0.9, 2.5)
	else:
		point = Vector3(0.75, 2.2, 0.10)
		target = Vector3(4.0, 1.15, 3.6)
	camera.keep_aspect = Camera3D.KEEP_WIDTH
	camera.fov = {"doorway": float(plan.camera.horizontal_fov_deg), "console": 65.0, "bed": 80.0, "wide": 132.0, "bedside": 40.0, "table": 50.0, "desk": 68.0, "boots": 58.0}[view]
	camera.global_position = QuartersLayout.to_world(point)
	camera.look_at(QuartersLayout.to_world(target))

static func verify(report, scenario: HarnessScenario) -> Array[String]:
	var failures: Array[String] = []
	for name: String in REQUIRED:
		if not report.beats.has(name): failures.append("quarters missing beat " + name)
	for beat: Dictionary in scenario.beats:
		var data: Dictionary = {}
		for event: Dictionary in report.events:
			if event.kind == "quarters" and event.name == beat.name: data = event.evidence
		if not data.has_all(["state", "elapsed", "door_open", "deck", "power_active", "remembered_visible", "present_visible", "console_presses", "foot", "camera_eye"]):
			failures.append("quarters evidence missing at " + beat.name)
			continue
		if data.deck != 16 or not data.power_active: failures.append("quarters start deck/power at " + beat.name)
		var expected := QuartersMemory.State.REMEMBERED
		if beat.name == "corridor-door": expected = QuartersMemory.State.UNSEEN
		elif String(beat.name).begins_with("present-"): expected = QuartersMemory.State.PRESENT
		elif String(beat.name).begins_with("console-"): expected = QuartersMemory.State.PLAYING
		if data.state != expected: failures.append("quarters state at " + beat.name)
		var remembering := expected in [QuartersMemory.State.REMEMBERED, QuartersMemory.State.PLAYING]
		if data.remembered_visible != remembering or data.present_visible == remembering:
			failures.append("quarters roots/lights disagree at " + beat.name)
		if data.door_open != (beat.name != "corridor-door"): failures.append("quarters manual door at " + beat.name)
		var played := String(beat.name).begins_with("console-") or expected == QuartersMemory.State.PRESENT
		if int(data.console_presses) != int(played): failures.append("quarters console press count at " + beat.name)
		var elapsed := int(data.elapsed)
		if beat.name == "console-corruption" and not (elapsed >= 0 and elapsed < QuartersMemory.CORRUPT_TICKS): failures.append("corruption timing")
		if beat.name == "console-message" and not (elapsed >= QuartersMemory.CORRUPT_TICKS and elapsed < QuartersMemory.CORRUPT_TICKS + QuartersMemory.MESSAGE_TICKS): failures.append("message timing")
		if beat.name == "console-fault" and not (elapsed >= QuartersMemory.CORRUPT_TICKS + QuartersMemory.MESSAGE_TICKS and elapsed < QuartersMemory.TOTAL_TICKS): failures.append("fault timing")
		if beat.get("quarters_view", "") == "doorway":
			var eye: Array = data.camera_eye
			var point: Array = QuartersInventory.plan().camera.position
			var expected_eye := QuartersLayout.to_world(Vector3(point[0], point[1], point[2]))
			if eye.size() != 3 or Vector3(eye[0], eye[1], eye[2]).distance_to(expected_eye) > 0.0001:
				failures.append("approved doorway camera at " + beat.name)
	return failures
