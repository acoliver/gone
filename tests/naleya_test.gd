extends SimTestCase

const Writing = preload("res://app/naleya.gd")

func test_boxed_identifier_has_native_digits_and_exact_ink_padding() -> void:
	var result := Writing.layout("[16]", 100)
	assert_true(result != null, "boxed identifier lays out")
	if result == null:
		return
	assert_true(result.units.map(func(unit: Writing.Unit) -> String: return unit.value) == ["16"], "one unbreakable identifier unit")
	var box := result.strokes[-1]
	assert_true(box == PackedVector2Array([Vector2(0.36, -1.36), Vector2(19.38, -1.36), Vector2(19.38, 10.36), Vector2(0.36, 10.36), Vector2(0.36, -1.36)]), "box pads digit centerline bounds by one native unit")
	assert_float_equal(Writing.STROKE_WIDTH, 0.72, "box and signs share stroke")
	assert_float_equal(result.end.x, Vector2(19.74, 0).x, "advance includes both half-stroke extents")
	assert_int_equal(result.strokes.size(), Writing.glyph_paths("na").size() + Writing.glyph_paths("wi").size() + 1, "digits plus one rectangle, no font brackets")

func test_boxed_identifiers_wrap_whole_and_reject_malformed_markup() -> void:
	var result := Writing.layout("pa [16]", 30)
	assert_int_equal(result.rows, 2, "box wraps as a whole")
	assert_true(result.units[1].origin == Vector2(0, -16.5), "box starts next baseline")
	assert_true(Writing.layout("[16]", 19.0) == null, "box extent participates in width")
	for text: String in ["[", "]", "[]", "[16", "16]", "[[16]]", "[pa]", "[8]", "[19]", "[1 6]"]:
		assert_true(Writing.layout(text, 100) == null, "reject malformed identifier " + text)

# Independent transcription of the guide's tables, in its onset/vowel order.
const EXPECTED_ONSETS: Array = [
	[[[3, 6], [3, 9], [6, 9], [6, 6], [3, 6]]],
	[[[1, 4], [1, 9], [7, 9], [7, 6], [1, 6]]],
	[[[1, 9], [7, 9]], [[4, 9], [4, 4]], [[2, 4], [6, 4]]],
	[[[1, 4], [1, 9]], [[1, 6], [6, 6], [6, 9]], [[6, 6], [6, 4], [8, 4]]],
	[[[1, 4], [1, 9], [7, 9], [7, 4]], [[4, 9], [4, 6]]],
	[[[1, 9], [1, 4], [7, 4], [7, 9]]],
	[[[1, 9], [1, 4], [7, 4]]],
	[[[1, 9], [1, 4], [7, 4], [7, 9]], [[4, 4], [4, 7]]],
	[[[7, 9], [1, 9], [1, 6.5], [7, 6.5], [7, 4], [1, 4]]],
	[[[1, 4], [1, 9]], [[7, 4], [7, 9]], [[1, 6.5], [7, 6.5]]],
]
const EXPECTED_VOWELS: Array = [
	[[[1, 2], [1, 0], [7, 0], [7, 2]]],
	[[[1, 0], [1, 2], [7, 2], [7, 0]]],
	[[[1, 2], [1, 0], [7, 0]]],
	[[[1, 0], [1, 2], [7, 2], [7, 0], [1, 0]]],
	[[[1, 2], [7, 2], [7, 0]]],
]

func test_fifty_unique_ordered_syllables() -> void:
	var unique := {}
	var index := 0
	for onset: String in ["", "p", "t", "k", "m", "n", "l", "w", "sh", "ch"]:
		for vowel: String in ["a", "e", "i", "o", "u"]:
			assert_true(Writing.SYLLABLES[index] == onset + vowel, "syllable order %d" % index)
			unique[Writing.SYLLABLES[index]] = true
			index += 1
	assert_int_equal(Writing.SYLLABLES.size(), 50, "syllable count")
	assert_int_equal(unique.size(), 50, "unique syllables")

func test_every_glyph_matches_exact_guide_paths() -> void:
	for index: int in range(50):
		var expected: Array = EXPECTED_ONSETS[index / 5] + EXPECTED_VOWELS[index % 5]
		var paths: Array[PackedVector2Array] = Writing.glyph_paths(Writing.SYLLABLES[index])
		assert_int_equal(paths.size(), expected.size(), "path count for %s" % Writing.SYLLABLES[index])
		if paths.size() != expected.size():
			continue
		for path_index: int in range(expected.size()):
			var points := PackedVector2Array()
			for point: Array in expected[path_index]:
				points.append(Vector2(point[0], point[1]))
			assert_true(paths[path_index] == points, "exact points for %s path %d" % [Writing.SYLLABLES[index], path_index])

func test_glyph_paths_do_not_expose_shared_mutable_geometry() -> void:
	var paths: Array[PackedVector2Array] = Writing.glyph_paths("a")
	paths[0][0] = Vector2(99, 99)
	assert_true(Writing.glyph_paths("a")[0][0] == Vector2(3, 6), "caller edits stay local")

func test_minimum_syllabification_checks() -> void:
	assert_true(Writing.syllabify("shasha") == ["sha", "sha"], "digraph repetition")
	assert_true(Writing.syllabify("peshupa") == ["pe", "shu", "pa"], "attached suffix")
	assert_true(Writing.syllabify("mokepopu") == ["mo", "ke", "po", "pu"], "four signs")
	assert_true(Writing.syllabify("Tewa") == ["te", "wa"], "lowercase normalization")
	assert_true(Writing.syllabify("aeiou") == ["a", "e", "i", "o", "u"], "vowel-only signs")
	assert_true(Writing.syllabify("ti tumino").is_empty(), "spaces are not part of a word")
	assert_true(Writing.syllabify("titumino") == ["ti", "tu", "mi", "no"], "all chart signs remain available")

func test_syllabify_rejects_invalid_words_without_partial_output() -> void:
	for word: String in ["hello", "veseo", "tierra", "psha", "pesh-u", "", "p", "sh", "ateh", "pa8", "ñu"]:
		assert_true(Writing.syllabify(word).is_empty(), "reject %s" % word)

func test_glyph_lookup_rejects_unknown_signs() -> void:
	for syllable: String in ["", "hello", "TE", "papa", "8", "9"]:
		assert_true(Writing.glyph_paths(syllable).is_empty(), "reject glyph %s" % syllable)

func test_minimum_octal_checks_and_padding() -> void:
	assert_true(Writing.octal(8) == "10", "eight")
	assert_true(Writing.octal(64) == "100", "sixty-four")
	assert_true(Writing.octal(512) == "1000", "five hundred twelve")
	assert_true(Writing.octal(0) == "0", "explicit zero")
	assert_true(Writing.octal(5, 3) == "005", "minimum width")
	assert_true(Writing.octal(64, 1) == "100", "padding never truncates")
	assert_true(Writing.octal(8, -1) == "10", "negative padding matches reference zfill")
	assert_true(Writing.octal(9223372036854775807) == "777777777777777777777", "largest integer")

func test_octal_rejects_non_integer_quantities() -> void:
	for value: Variant in [-1, 1.5, 8.0, true, false, "10", null]:
		assert_true(Writing.octal(value) == "", "reject quantity %s" % str(value))

func test_minimum_clock_checks() -> void:
	assert_true(Writing.clock(7, 16) == "07:20", "first clock example")
	assert_true(Writing.clock(20, 3) == "24:03", "second clock example")
	assert_true(Writing.clock(16, 0, 0) == "20:00:00", "midday")
	assert_true(Writing.clock(31, 63, 63) == "37:77:77", "last beat of day")
	assert_true(Writing.clock(0, 0, 0) == "00:00:00", "midnight")

func test_clock_rejects_out_of_range_and_non_integer_fields() -> void:
	for fields: Array in [[32, 0, 0], [-1, 0, 0], [0, 64, 0], [0, -1, 0], [0, 0, 64], [0, 0, -1], [true, 0, 0], [0, 1.0, 0], [0, 0, false], [null, 0, 0]]:
		assert_true(Writing.clock(fields[0], fields[1], fields[2]) == "", "reject clock %s" % str(fields))

func test_minimum_numeric_chunk_check() -> void:
	var units: Array = Writing.chunk_units("07")
	assert_int_equal(units.size(), 2, "two written digits")
	assert_true(units[0].kind == "glyph" and units[0].value == "mo", "zero sign")
	assert_true(units[1].kind == "glyph" and units[1].value == "shu", "seven sign")

func test_all_digits_use_existing_syllable_signs() -> void:
	var expected := ["mo", "na", "mu", "shi", "le", "chi", "wi", "shu"]
	assert_true(Writing.DIGITS == expected, "digit table")
	var result: Writing.Layout = Writing.layout("01234567", 100)
	assert_true(result != null, "valid octal run")
	if result == null:
		return
	for index: int in range(8):
		assert_true(result.units[index].value == expected[index], "digit sign %d" % index)

func test_chunk_and_layout_reject_digits_eight_and_nine() -> void:
	for text: String in ["8", "9", "078", "19", "07:89", "pa9", "hello", "pesh-u", "pa/ta", "pa_", "paé"]:
		assert_true(Writing.chunk_units(text).is_empty(), "reject whole chunk %s" % text)
		assert_true(Writing.layout(text, 100) == null, "reject layout %s" % text)

func test_layout_fixed_advance_word_gap_and_positioned_strokes() -> void:
	var result: Writing.Layout = Writing.layout("tala pama", 100)
	assert_true(result != null, "valid phrase")
	if result == null:
		return
	var expected := [0.0, 10.3, 26.6, 36.9]
	for index: int in range(4):
		assert_true(result.units[index].origin.is_equal_approx(Vector2(expected[index], 0)), "cell origin %d" % index)
	assert_true(result.end.is_equal_approx(Vector2(47.2, 0)), "final cursor includes advance")
	assert_true(result.strokes[0] == Writing.glyph_paths("ta")[0], "first path uses native coordinates")
	assert_true(result.strokes[4][0].is_equal_approx(Vector2(11.3, 9)), "next glyph translated without centering or y flip")

func test_layout_wraps_only_at_word_boundaries() -> void:
	var result: Writing.Layout = Writing.layout("tala pama", 47.1)
	assert_true(result != null, "valid wrap")
	if result == null:
		return
	assert_int_equal(result.rows, 2, "wrapped rows")
	assert_true(result.units[2].origin == Vector2(0, -16.5), "whole next word starts new row without gap")
	assert_true(result.units[3].origin.is_equal_approx(Vector2(10.3, -16.5)), "word not split")
	assert_true(Writing.layout("tala pama", 47.2).rows == 1, "exact fit stays on line")
	assert_true(Writing.layout("peshupa", 30.8) == null, "oversized word rejected, suffix not split")
	assert_true(Writing.layout("000", 30.8) == null, "oversized number rejected")

func test_layout_preserves_newlines_and_collapses_horizontal_spaces() -> void:
	var result: Writing.Layout = Writing.layout(" \tta  \tla\n\n pa\n", 100)
	assert_true(result != null, "whitespace layout")
	if result == null:
		return
	assert_int_equal(result.rows, 4, "explicit blank and trailing lines")
	assert_true(result.units[0].origin == Vector2.ZERO, "no leading gap")
	assert_true(result.units[1].origin.is_equal_approx(Vector2(16.3, 0)), "one word gap for a space run")
	assert_true(result.units[2].origin == Vector2(0, -33), "blank line preserved")
	assert_true(result.end == Vector2(0, -49.5), "trailing newline preserved")

func test_layout_editorial_punctuation_is_separate_from_native_strokes() -> void:
	var result: Writing.Layout = Writing.layout("pa.,:;!?()\"", 100)
	assert_true(result != null, "supported punctuation")
	if result == null:
		return
	assert_int_equal(result.units.size(), 10, "one glyph and nine marks")
	assert_int_equal(result.strokes.size(), 2, "punctuation does not invent native paths")
	for index: int in range(1, 10):
		assert_true(result.units[index].kind == "punct", "editorial mark kind")
		assert_true(result.units[index].origin.is_equal_approx(Vector2(10.3 + (index - 1) * 3.5, 0)), "punctuation advance")
	assert_true(result.end.is_equal_approx(Vector2(41.8, 0)), "punctuation width")

func test_layout_empty_text_and_invalid_widths() -> void:
	var empty: Writing.Layout = Writing.layout("", 10)
	assert_true(empty != null and empty.units.is_empty() and empty.strokes.is_empty(), "reference permits an empty layout")
	for width: float in [0.0, -1.0, NAN, INF]:
		assert_true(Writing.layout("pa", width) == null, "invalid layout width")

func test_layout_clock_punctuation_and_digit_signs() -> void:
	var result: Writing.Layout = Writing.layout(Writing.clock(7, 16), 100)
	assert_true(result != null, "formatted clock layout")
	if result == null:
		return
	var expected := ["mo", "shu", ":", "mu", "mo"]
	for index: int in range(5):
		assert_true(result.units[index].value == expected[index], "clock unit %d" % index)
	assert_true(result.units[3].origin.is_equal_approx(Vector2(24.1, 0)), "colon uses editorial advance")

func test_closed_carrier_and_o_expand_with_miters_at_every_end() -> void:
	var paths: Array[PackedVector2Array] = Writing.glyph_paths("o")
	var carrier: Array[PackedVector2Array] = Writing.expand_strokes([paths[0]])
	var vowel: Array[PackedVector2Array] = Writing.expand_strokes([paths[1]])
	assert_int_equal(carrier.size(), 4, "four carrier segments")
	assert_int_equal(vowel.size(), 4, "four vowel segments")
	_assert_quad_bounds(carrier[0], Vector2(2.64, 5.64), Vector2(3.36, 9.36), "carrier closing join")
	_assert_quad_bounds(carrier[3], Vector2(2.64, 5.64), Vector2(6.36, 6.36), "carrier last segment")
	_assert_quad_bounds(vowel[0], Vector2(0.64, -0.36), Vector2(1.36, 2.36), "o first segment")
	_assert_quad_bounds(vowel[3], Vector2(0.64, -0.36), Vector2(7.36, 0.36), "o closing segment")

func test_open_i_expansion_has_butt_caps_and_internal_miter() -> void:
	var vowel: PackedVector2Array = Writing.glyph_paths("i")[1]
	var quads: Array[PackedVector2Array] = Writing.expand_strokes([vowel])
	assert_int_equal(quads.size(), 2, "two open segments")
	_assert_quad_bounds(quads[0], Vector2(0.64, -0.36), Vector2(1.36, 2), "i first open cap")
	_assert_quad_bounds(quads[1], Vector2(0.64, -0.36), Vector2(7, 0.36), "i last open cap")

func test_t_keeps_separate_polylines_butt_capped() -> void:
	var paths: Array[PackedVector2Array] = Writing.glyph_paths("ti")
	var quads: Array[PackedVector2Array] = Writing.expand_strokes(paths.slice(0, 3))
	assert_int_equal(quads.size(), 3, "three separate t strokes")
	_assert_quad_bounds(quads[0], Vector2(1, 8.64), Vector2(7, 9.36), "top bar")
	_assert_quad_bounds(quads[1], Vector2(3.64, 4), Vector2(4.36, 9), "stem remains butt capped at other polylines")
	_assert_quad_bounds(quads[2], Vector2(2, 3.64), Vector2(6, 4.36), "bottom bar")

func test_expansion_handles_positioned_layout_without_y_flip() -> void:
	var result: Writing.Layout = Writing.layout("i\ni", 20)
	var quads: Array[PackedVector2Array] = Writing.expand_strokes(result.strokes)
	assert_int_equal(quads.size(), 12, "six rectangles per i")
	_assert_quad_bounds(quads[10], Vector2(0.64, -16.86), Vector2(1.36, -14.5), "translated open stroke")

func _assert_quad_bounds(quad: PackedVector2Array, lo: Vector2, hi: Vector2, label: String) -> void:
	assert_int_equal(quad.size(), 4, label + " quad vertices")
	var actual_lo := Vector2(INF, INF)
	var actual_hi := Vector2(-INF, -INF)
	for point: Vector2 in quad:
		actual_lo = actual_lo.min(point)
		actual_hi = actual_hi.max(point)
	assert_true(actual_lo.is_equal_approx(lo) and actual_hi.is_equal_approx(hi), "%s bounds expected %s..%s got %s..%s" % [label, lo, hi, actual_lo, actual_hi])
	assert_int_equal(Geometry2D.triangulate_polygon(quad).size(), 6, label + " drawable quad")
