class_name ShipText
extends RefCounted

const Writing = preload("res://app/naleya.gd")
const MESSAGES: Dictionary = {
	"navigation.deck": {"native": "lometa", "perceived_es": "CUBIERTA"},
	"navigation.section": {"native": "shelani paki", "perceived_es": "SECCIÓN"},
	"navigation.lift": {"native": "kotewa", "perceived_es": "ASCENSOR"},
	"navigation.hatch": {"native": "pana", "perceived_es": "ESCOTILLA"},
	"navigation.level": {"native": "lometa", "perceived_es": "NIVEL"},
	"navigation.bay": {"native": "pama", "perceived_es": "COMPARTIMENTO"},
	"secondary_power.room": {"native": "te mu nawa lina", "perceived_es": "ENERGÍA SECUNDARIA"},
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

static func sliding_label(layout: ShipLayout, door: ShipLayout.DoorSpec) -> LabelText:
	var section := layout.face(door.face_ids()[0]).destination_section()
	var bay := layout.door_bay_number(door.id())
	var native: PackedStringArray = []
	var perceived: PackedStringArray = []
	var terms := ["navigation.level", "navigation.section", "navigation.bay"]
	var values := [door.deck_number(), section, bay]
	for index: int in range(terms.size()):
		var term := message(terms[index])
		native.append("%s [%s]" % [term.native, Writing.octal(values[index])])
		perceived.append("%s %d" % [term.perceived_es, values[index]])
	if door.kind() == ShipLayout.DoorKind.POWER:
		native.append(message("secondary_power.room").native)
		perceived.append(message("secondary_power.room").perceived_es)
	return LabelText.new("\n".join(native), "\n".join(perceived))

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
