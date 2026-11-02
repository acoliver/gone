extends SimTestCase

const Catalog = preload("res://app/ship_text.gd")
const Writing = preload("res://app/naleya.gd")

func test_catalog_validates_every_native_word_on_load() -> void:
	assert_true(Catalog.VALID, "the loaded catalog is valid")
	assert_int_equal(Catalog.MESSAGES.size(), 3, "three authored console messages")
	for id: String in Catalog.MESSAGES:
		var message: Dictionary = Catalog.message(id)
		assert_false(message.native.is_empty(), "native text required for " + id)
		assert_false(message.perceived_es.is_empty(), "Spanish text required for " + id)
		for word: String in message.native.split(" "):
			assert_false(Writing.syllabify(word).is_empty(), "valid native word " + word)

func test_console_catalog_preserves_authored_meanings() -> void:
	assert_true(Catalog.message("secondary_power.heading") == {"native": "te mu nawa lina", "perceived_es": "SISTEMA DE ENERGÍA SECUNDARIO"}, "heading pair")
	assert_true(Catalog.message("secondary_power.inactive") == {"native": "palo", "perceived_es": "INACTIVO"}, "off without a defect")
	assert_true(Catalog.message("secondary_power.active") == {"native": "shenu", "perceived_es": "EN FUNCIONAMIENTO"}, "running")
