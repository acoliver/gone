class_name HarnessProtocol
extends RefCounted
## The harness wire protocol shared by the app lane (app/harness_mode.gd)
## and the runner (harness/run.gd), ported from the Rust harness module
## (gone_app harness/{mod,frame,beat,report}.rs, PROTOCOL_VERSION 4).
## One truth for the frame-code chip encoding, the sha256 identity
## contract, the event schema's canonical order, and beat accounting.
## Pure logic: no Node or scene types, so tests cover it headless.
##
## JSON shape (both directions):
##   report = {
##     "protocol_version": int, "scenario": String, "seed": int,
##     "events": [event], "checkpoints": [String],
##     "frame_stats": {"frames": int, "mean_us": float, "p95_us": float,
##                     "median_us": float},
##     "beats": {name: {"file": String, "tick": int, "frame": int,
##                      "request_id": int}},
##     "identity": {"app_hash": String, "scenario_hash": String,
##                  "config_hash": String}}
##   event = flat dictionary with a "kind" tag:
##     ready{frame} room_check{frame,pods_expected,pods_present}
##     input{tick,frame,what} beat{name,tick,frame,request_id}
##     wake_phase{tick,frame,phase} player_yaw{tick,frame,yaw_degrees}
##     player_position{tick,frame,x,y,z} door_open{tick,frame,openings,open}
##     hallway{tick,frame,lit,level} rod_pickup{tick,frame,carried,rod_visible}
##     complete{frame} failure{frame,what}
##
## Env contract (the runner sets, the app echoes):
##   GONE_HARNESS=1  GONE_SCENARIO=<abs scenario.json>
##   GONE_OUT_DIR=<abs run dir>  GONE_APP_HASH / GONE_SCENARIO_HASH /
##   GONE_CONFIG_HASH = lowercase sha256 hex. The app hashes nothing
##   itself: it echoes the runner's values, so a stale pairing fails.
##   The runner hashes: scenario/config = the scenario file's exact
##   bytes; app = sha256 over every *.gd under app/, sim/, harness/
##   (sorted by relative path, each prefixed by its UTF-8 relative
##   path + one NUL byte + its exact file bytes).

const PROTOCOL_VERSION: int = 4

const ENV_HARNESS: String = "GONE_HARNESS"
const ENV_SCENARIO: String = "GONE_SCENARIO"
const ENV_OUT_DIR: String = "GONE_OUT_DIR"
const ENV_APP_HASH: String = "GONE_APP_HASH"
const ENV_SCENARIO_HASH: String = "GONE_SCENARIO_HASH"
const ENV_CONFIG_HASH: String = "GONE_CONFIG_HASH"
const ENV_PERF_POLICY: String = "GONE_PERF_POLICY"

## Chip geometry, ported from Rust frame.rs: 6 digit cells per band, a
## cell is a 3x3 digit lattice in a 4x5 pixel cell, two bands (tick over
## frame). PIXEL_SCALE is the Godot-side render multiplier: each chip
## pixel paints as a SCALE x SCALE square so the lattice survives the
## viewport; decode samples each lattice cell's block center.
const CELL_W: int = 4
const CELL_H: int = 5
const DIGITS: int = 6
const ROWS: int = 3
const COLS: int = 3
const IS_ON_MIN: float = 60.0 / 255.0
const ON_COLOR: Color = Color(0x7f / 255.0, 0xb8 / 255.0, 0xff / 255.0)
const OFF_COLOR: Color = Color(0x05 / 255.0, 0x05 / 255.0, 0x06 / 255.0)
const PIXEL_SCALE: int = 4

static func chip_size() -> Vector2i:
	return Vector2i(DIGITS * CELL_W * PIXEL_SCALE, 2 * CELL_H * PIXEL_SCALE)

## A digit's 3x3 lattice, row then column.
static func digit_pattern(digit: int) -> Array:
	match digit:
		0: return [[true, true, true], [true, false, true], [true, true, true]]
		1: return [[false, true, false], [false, true, false], [false, true, false]]
		2: return [[true, true, true], [false, true, true], [true, true, false]]
		3: return [[true, true, true], [false, true, true], [true, true, true]]
		4: return [[true, false, true], [true, true, true], [false, false, true]]
		5: return [[true, true, false], [true, true, true], [true, true, true]]
		6: return [[true, true, false], [true, true, true], [true, false, true]]
		7: return [[true, true, true], [false, false, true], [false, false, true]]
		8: return [[true, true, true], [true, true, true], [true, true, true]]
		_: return [[true, true, true], [true, true, true], [false, false, true]]

## Split a value into DIGITS cells, most significant first, zero-padded;
## values at or above 10^DIGITS keep the low DIGITS digits.
static func digit_cells(value: int) -> Array[int]:
	var cells: Array[int] = []
	var remaining: int = value
	for _slot: int in range(DIGITS):
		cells.append(0)
	for index: int in range(DIGITS - 1, -1, -1):
		cells[index] = remaining % 10
		remaining /= 10
	return cells

static func number_from_cells(cells: Array[int]) -> int:
	var value: int = 0
	for cell: int in cells:
		value = value * 10 + cell
	return value

## The chip pixel color at local lattice coordinates (px, py) inside the
## unscaled DIGITS*CELL_W x 2*CELL_H block.
static func chip_pixel(tick: int, frame: int, px: int, py: int) -> Color:
	if px >= DIGITS * CELL_W or py >= 2 * CELL_H:
		return OFF_COLOR
	var band: int = tick if py < CELL_H else frame
	var py_in_band: int = py % CELL_H
	var cell: int = px / CELL_W
	var inner_col: int = px % CELL_W
	if inner_col >= COLS or py_in_band >= ROWS:
		return OFF_COLOR
	var digit: int = digit_cells(band)[cell]
	if digit_pattern(digit)[py_in_band][inner_col]:
		return ON_COLOR
	return OFF_COLOR

static func is_on(color: Color) -> bool:
	return color.r > IS_ON_MIN and color.g > IS_ON_MIN and color.b > IS_ON_MIN

## Decode the chip from the top-left of a captured image. The chip's
## on/off lattice reads at PIXEL_SCALE block centers. Returns
## {"ok": bool, "tick": int, "frame": int, "error": String}.
static func decode_chip(image: Image) -> Dictionary:
	var chip: Vector2i = chip_size()
	if image.get_width() < chip.x or image.get_height() < chip.y:
		return {"ok": false, "tick": 0, "frame": 0,
			"error": "image %dx%d too small for the %dx%d chip" % [
				image.get_width(), image.get_height(), chip.x, chip.y]}
	var read_band := func(py_base: int) -> Dictionary:
		var value: int = 0
		for cell: int in range(DIGITS):
			var lattice: Array = [[false, false, false], [false, false, false], [false, false, false]]
			for row: int in range(ROWS):
				for col: int in range(COLS):
					var px: int = (cell * CELL_W + col) * PIXEL_SCALE + PIXEL_SCALE / 2
					var py: int = (py_base + row) * PIXEL_SCALE + PIXEL_SCALE / 2
					lattice[row][col] = is_on(image.get_pixel(px, py))
			var matched: int = -1
			for digit: int in range(10):
				if _patterns_equal(lattice, digit_pattern(digit)):
					matched = digit
					break
			if matched < 0:
				return {"ok": false, "value": 0,
					"error": "chip lattice does not match any digit (capture does not show the chip)"}
			value = value * 10 + matched
		return {"ok": true, "value": value, "error": ""}
	var tick_band: Dictionary = read_band.call(0)
	if not tick_band.ok:
		return {"ok": false, "tick": 0, "frame": 0, "error": tick_band.error}
	var frame_band: Dictionary = read_band.call(CELL_H)
	if not frame_band.ok:
		return {"ok": false, "tick": 0, "frame": 0, "error": frame_band.error}
	return {"ok": true, "tick": tick_band.value, "frame": frame_band.value, "error": ""}

static func _patterns_equal(a: Array, b: Array) -> bool:
	for row: int in range(ROWS):
		for col: int in range(COLS):
			if a[row][col] != b[row][col]:
				return false
	return true

## sha256 of exact bytes, lowercase hex, via HashingContext (headless-safe).
static func sha256_hex(data: PackedByteArray) -> String:
	var context := HashingContext.new()
	if context.start(HashingContext.HASH_SHA256) != OK:
		return ""
	if data.size() > 0 and context.update(data) != OK:
		return ""
	return context.finish().hex_encode()

## sha256 of a file's exact bytes.
static func sha256_file(path: String) -> String:
	return FileAccess.get_sha256(path)

## The app hash: sha256 over every *.gd under app/, sim/, harness/ of
## the project root, sorted by relative path, each contributed as its
## UTF-8 relative path, one NUL byte, then its exact file bytes. The
## recipe (not a binary hash) is the Godot port's app identity: the
## scripts are the build.
static func app_hash(project_root: String) -> String:
	var context := HashingContext.new()
	if context.start(HashingContext.HASH_SHA256) != OK:
		return ""
	var paths: Array[String] = []
	for directory: String in ["app", "sim", "harness"]:
		var dir := DirAccess.open(project_root.path_join(directory))
		if dir == null:
			continue
		dir.list_dir_begin()
		var entry := dir.get_next()
		while not entry.is_empty():
			if entry.ends_with(".gd"):
				paths.append(directory.path_join(entry))
			entry = dir.get_next()
		dir.list_dir_end()
	paths.sort()
	for relative: String in paths:
		context.update(relative.to_utf8_buffer())
		context.update(PackedByteArray([0]))
		var bytes := FileAccess.get_file_as_bytes(project_root.path_join(relative))
		if bytes.size() > 0:
			context.update(bytes)
	return context.finish().hex_encode()

## The canonical report event order, ported from Rust report.rs
## order_key: the ready boundary first, run events by tick then frame
## (room_check shares tick 0), terminal events last. Stable on ties.
static func event_order_key(event: Dictionary) -> Array:
	match event.kind:
		"ready":
			return [0, 0, event.frame]
		"room_check":
			return [1, 0, event.frame]
		"input", "beat", "wake_phase", "player_yaw", "player_position", "door_open", "power_door", "hallway", "rod_pickup", "console", "power", "calibration":
			return [1, event.tick, event.frame]
		_:
			return [2, 9223372036854775807, event.frame]

static func sort_events(events: Array) -> void:
	events.sort_custom(func(a: Dictionary, b: Dictionary) -> bool:
		var key_a := event_order_key(a)
		var key_b := event_order_key(b)
		if key_a[0] != key_b[0]:
			return key_a[0] < key_b[0]
		if key_a[1] != key_b[1]:
			return key_a[1] < key_b[1]
		return key_a[2] < key_b[2])

## Verify every expected beat name happened, ported from Rust
## beat.rs verify_beats. Returns "" or an error naming the first gap.
static func verify_beats(happened: Array, expected: Array) -> String:
	var present := {}
	for beat: Dictionary in happened:
		present[beat.name] = true
	for beat: Dictionary in expected:
		if not present.has(beat.name):
			return "missing beat `%s` (expected tick %d)" % [beat.name, beat.tick]
	return ""
