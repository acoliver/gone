class_name HatchResistance
extends RefCounted
## Versioned UTF-8 FNV-1a and a private xorshift32 stream. Modulo draws retain
## their tiny integer bias so replay never depends on an engine RNG version.

const MASK: int = 0xffffffff
const ZERO_SEED: int = 0x6d2b79f5
const OPEN_ANGLE: float = 270.0

class Stream:
	extends RefCounted
	var state: int
	func _init(seed: int) -> void:
		state = seed & HatchResistance.MASK
		if state == 0:
			state = HatchResistance.ZERO_SEED
	func next() -> int:
		state = (state ^ (state << 13)) & HatchResistance.MASK
		state = (state ^ (state >> 17)) & HatchResistance.MASK
		state = (state ^ (state << 5)) & HatchResistance.MASK
		return state

class Schedule:
	extends RefCounted
	var weights: Array[int] = []
	var total_weight: int = 0
	func angle_after(attempt: int) -> float:
		assert(attempt >= 0 and attempt <= weights.size(), "attempt belongs to finite schedule")
		var work: int = 0
		for index: int in range(attempt):
			work += weights[index]
		return HatchResistance.OPEN_ANGLE * float(work) / float(total_weight)

static func hash_bytes(text: String) -> int:
	var value: int = 2166136261
	for byte: int in text.to_utf8_buffer():
		value = ((value ^ byte) * 16777619) & MASK
	return value

static func seed_for(run_seed: int, id: StringName) -> int:
	return hash_bytes("hatch-v1|%d|%s" % [run_seed, id])

static func schedule(run_seed: int, id: StringName) -> Schedule:
	var stream := Stream.new(seed_for(run_seed, id))
	var category := stream.next() % 100
	var attempts := (5 if category < 85 else 11) + stream.next() % 6
	var first_stall := stream.next() % (attempts - 1)
	var second_stall: int = -1
	if stream.next() % 4 == 0:
		second_stall = stream.next() % (attempts - 2)
		if second_stall >= first_stall:
			second_stall += 1
	var result := Schedule.new()
	for index: int in range(attempts):
		var weight: int = 0 if index == first_stall or index == second_stall else 1 + stream.next() % 5
		result.weights.append(weight)
		result.total_weight += weight
	result.weights.make_read_only()
	return result
