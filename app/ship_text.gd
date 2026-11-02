class_name ShipText
extends RefCounted

const Writing = preload("res://app/naleya.gd")
const MESSAGES: Dictionary = {
	"secondary_power.heading": {
		"native": "te mu nawa lina",
		"perceived_es": "SISTEMA DE ENERGÍA SECUNDARIO",
	},
	"secondary_power.inactive": {
		"native": "palo",
		"perceived_es": "INACTIVO",
	},
	"secondary_power.active": {
		"native": "shenu",
		"perceived_es": "EN FUNCIONAMIENTO",
	},
}

static var VALID: bool = _validate()

static func _validate() -> bool:
	for id: String in MESSAGES:
		var entry: Dictionary = MESSAGES[id]
		if entry.native.is_empty() or entry.perceived_es.is_empty():
			push_error("ShipText: missing authored text for %s" % id)
			return false
		for word: String in entry.native.split(" "):
			if Writing.syllabify(word).is_empty():
				push_error("ShipText: invalid native text for %s" % id)
				return false
	return true

static func message(id: String) -> Dictionary:
	assert(VALID, "the ship-text catalog must validate before use")
	if not MESSAGES.has(id):
		push_error("ShipText: missing message %s" % id)
		assert(false, "missing ship-text message")
		return {}
	return MESSAGES[id].duplicate()
