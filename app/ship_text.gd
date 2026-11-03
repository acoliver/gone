class_name ShipText
extends RefCounted

const Writing = preload("res://app/naleya.gd")
const MESSAGES: Dictionary = {
	"navigation.deck": {"native": "lometa", "perceived_es": "CUBIERTA"},
	"navigation.section": {"native": "shelani paki", "perceived_es": "SECCIÓN"},
	"navigation.lift": {"native": "kotewa", "perceived_es": "ASCENSOR"},
	"navigation.hatch": {"native": "pana", "perceived_es": "ESCOTILLA"},
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

class LabelText:
	extends RefCounted
	var native: String
	var perceived_es: String
	func _init(p_native: String, p_perceived_es: String) -> void:
		native = p_native
		perceived_es = p_perceived_es

static func deck_label(deck: int) -> LabelText:
	assert(deck > 0, "deck identifiers are positive")
	var term := message("navigation.deck")
	return LabelText.new("%s [%s]" % [term.native, Writing.octal(deck)], "%s %d" % [term.perceived_es, deck])

static func hatch_label(deck: int, section: int) -> LabelText:
	assert(section > 0, "section identifiers are positive")
	var result := deck_label(deck)
	var term := message("navigation.section")
	return LabelText.new(result.native + "\n%s [%s]" % [term.native, Writing.octal(section)], result.perceived_es + "\n%s %d" % [term.perceived_es, section])

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
