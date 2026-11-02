class_name Naleya
extends RefCounted
## Native writing geometry and layout, without scene or font dependencies.
## Coordinates stay +y up, with the first baseline at zero. Callers apply
## scale and one y inversion when drawing to a downward-positive canvas.
## Invalid input reports push_error and returns no usable output: an empty
## array/string, or null for layout. Never render a failed word as Latin text.

const ONSETS: Array[String] = ["", "p", "t", "k", "m", "n", "l", "w", "sh", "ch"]
const VOWELS: String = "aeiou"
const SYLLABLES: Array[String] = [
	"a", "e", "i", "o", "u",
	"pa", "pe", "pi", "po", "pu",
	"ta", "te", "ti", "to", "tu",
	"ka", "ke", "ki", "ko", "ku",
	"ma", "me", "mi", "mo", "mu",
	"na", "ne", "ni", "no", "nu",
	"la", "le", "li", "lo", "lu",
	"wa", "we", "wi", "wo", "wu",
	"sha", "she", "shi", "sho", "shu",
	"cha", "che", "chi", "cho", "chu",
]
const DIGITS: Array[String] = ["mo", "na", "mu", "shi", "le", "chi", "wi", "shu"]

const CELL: float = 10.0
const STROKE_WIDTH: float = 0.72
const ADVANCE: float = 10.3
const WORD_GAP: float = 6.0
const LINE_HEIGHT: float = 16.5
const PUNCTUATION_ADVANCE: float = 3.5

const ONSET_PATHS: Dictionary = {
	"": [[Vector2(3, 6), Vector2(3, 9), Vector2(6, 9), Vector2(6, 6), Vector2(3, 6)]],
	"p": [[Vector2(1, 4), Vector2(1, 9), Vector2(7, 9), Vector2(7, 6), Vector2(1, 6)]],
	"t": [[Vector2(1, 9), Vector2(7, 9)], [Vector2(4, 9), Vector2(4, 4)], [Vector2(2, 4), Vector2(6, 4)]],
	"k": [[Vector2(1, 4), Vector2(1, 9)], [Vector2(1, 6), Vector2(6, 6), Vector2(6, 9)], [Vector2(6, 6), Vector2(6, 4), Vector2(8, 4)]],
	"m": [[Vector2(1, 4), Vector2(1, 9), Vector2(7, 9), Vector2(7, 4)], [Vector2(4, 9), Vector2(4, 6)]],
	"n": [[Vector2(1, 9), Vector2(1, 4), Vector2(7, 4), Vector2(7, 9)]],
	"l": [[Vector2(1, 9), Vector2(1, 4), Vector2(7, 4)]],
	"w": [[Vector2(1, 9), Vector2(1, 4), Vector2(7, 4), Vector2(7, 9)], [Vector2(4, 4), Vector2(4, 7)]],
	"sh": [[Vector2(7, 9), Vector2(1, 9), Vector2(1, 6.5), Vector2(7, 6.5), Vector2(7, 4), Vector2(1, 4)]],
	"ch": [[Vector2(1, 4), Vector2(1, 9)], [Vector2(7, 4), Vector2(7, 9)], [Vector2(1, 6.5), Vector2(7, 6.5)]],
}
const VOWEL_PATHS: Dictionary = {
	"a": [[Vector2(1, 2), Vector2(1, 0), Vector2(7, 0), Vector2(7, 2)]],
	"e": [[Vector2(1, 0), Vector2(1, 2), Vector2(7, 2), Vector2(7, 0)]],
	"i": [[Vector2(1, 2), Vector2(1, 0), Vector2(7, 0)]],
	"o": [[Vector2(1, 0), Vector2(1, 2), Vector2(7, 2), Vector2(7, 0), Vector2(1, 0)]],
	"u": [[Vector2(1, 2), Vector2(7, 2), Vector2(7, 0)]],
}

class Unit:
	extends RefCounted
	## A native syllable or editorial punctuation mark at its cell baseline.
	## Only kind == "punct" may be passed to an ordinary font renderer.
	var kind: String
	var value: String
	var origin: Vector2 = Vector2.ZERO

	func _init(unit_kind: String, unit_value: String) -> void:
		kind = unit_kind
		value = unit_value

class Layout:
	extends RefCounted
	var units: Array[Naleya.Unit] = []
	var strokes: Array[PackedVector2Array] = []
	var rows: int = 1
	var end: Vector2 = Vector2.ZERO

static func syllabify(word: String) -> Array[String]:
	var normalized := word.to_lower()
	var parts: Array[String] = []
	var cursor := 0
	while cursor < normalized.length():
		var start := cursor
		var digraph := normalized.substr(cursor, 2)
		if digraph == "sh" or digraph == "ch":
			cursor += 2
		elif normalized[cursor] in ["p", "t", "k", "m", "n", "l", "w"]:
			cursor += 1
		if cursor >= normalized.length() or not VOWELS.contains(normalized[cursor]):
			push_error("Naleya: invalid native word: %s" % word)
			return []
		cursor += 1
		parts.append(normalized.substr(start, cursor - start))
	if parts.is_empty():
		push_error("Naleya: invalid native word: %s" % word)
	return parts

static func glyph_paths(syllable: String) -> Array[PackedVector2Array]:
	if syllable not in SYLLABLES:
		push_error("Naleya: unknown syllable: %s" % syllable)
		return []
	var paths: Array[PackedVector2Array] = []
	var onset := syllable.substr(0, syllable.length() - 1)
	var vowel := syllable.right(1)
	for path: Array in ONSET_PATHS[onset] + VOWEL_PATHS[vowel]:
		paths.append(PackedVector2Array(path))
	return paths

## Quantities are integer local units, not already formatted digit strings.
## Variant prevents Godot's implicit float/bool-to-int coercion at this boundary.
static func octal(value: Variant, min_digits: int = 1) -> String:
	if typeof(value) != TYPE_INT or value < 0:
		push_error("Naleya: expected a nonnegative integer")
		return ""
	var remaining: int = value
	var digits := ""
	while true:
		digits = str(remaining & 7) + digits
		remaining = remaining >> 3
		if remaining == 0:
			break
	return digits.lpad(min_digits, "0")

static func clock(hour: Variant, interval: Variant, beat: Variant = null) -> String:
	var fields: Array = [[hour, 32], [interval, 64]]
	if beat != null:
		fields.append([beat, 64])
	var formatted := PackedStringArray()
	for field: Array in fields:
		if typeof(field[0]) != TYPE_INT or field[0] < 0 or field[0] >= field[1]:
			push_error("Naleya: clock field outside the full-day range")
			return ""
		formatted.append(octal(field[0], 2))
	return ":".join(formatted)

## One unbreakable chunk. Numeric text is already octal; no radix conversion.
static func chunk_units(chunk: String) -> Array[Naleya.Unit]:
	var pattern := RegEx.new()
	pattern.compile('[A-Za-z]+|[0-7]+|[.,:;!?()"]')
	var units: Array[Naleya.Unit] = []
	var cursor := 0
	for token: RegExMatch in pattern.search_all(chunk):
		if token.get_start() != cursor:
			push_error("Naleya: unsupported text in chunk: %s" % chunk)
			return []
		var text := token.get_string()
		var first := text.unicode_at(0)
		if (first >= 65 and first <= 90) or (first >= 97 and first <= 122):
			var syllables := syllabify(text)
			if syllables.is_empty():
				return []
			for syllable: String in syllables:
				units.append(Unit.new("glyph", syllable))
		elif first >= 48 and first <= 55:
			for digit: String in text:
				units.append(Unit.new("glyph", DIGITS[digit.to_int()]))
		else:
			units.append(Unit.new("punct", text))
		cursor = token.get_end()
	if cursor != chunk.length():
		push_error("Naleya: unsupported text in chunk: %s" % chunk)
		return []
	return units

## Width is the available advance space in native units, excluding padding.
## Ink can extend half a stroke below a baseline. Editorial marks have an
## origin and advance but no native strokes; the caller supplies their font.
static func layout(native_text: String, width: float) -> Naleya.Layout:
	if not is_finite(width) or width <= 0.0:
		push_error("Naleya: invalid layout width")
		return null
	var result := Layout.new()
	var pattern := RegEx.new()
	pattern.compile("\\n|[ \\t]+|[^\\s]+")
	var row := 0
	var cursor := 0.0
	var pending_space := false
	for token_match: RegExMatch in pattern.search_all(native_text):
		var token := token_match.get_string()
		if token == "\n":
			row += 1
			cursor = 0.0
			pending_space = false
			continue
		if token.strip_edges() == "":
			pending_space = true
			continue
		var units := chunk_units(token)
		if units.is_empty():
			return null
		var token_width := 0.0
		for unit: Naleya.Unit in units:
			token_width += ADVANCE if unit.kind == "glyph" else PUNCTUATION_ADVANCE
		if token_width > width:
			push_error("Naleya: word or number exceeds line width: %s" % token)
			return null
		var gap := WORD_GAP if pending_space and cursor != 0.0 else 0.0
		if cursor != 0.0 and cursor + gap + token_width > width:
			row += 1
			cursor = 0.0
			gap = 0.0
		cursor += gap
		pending_space = false
		for unit: Naleya.Unit in units:
			unit.origin = Vector2(cursor, -row * LINE_HEIGHT)
			result.units.append(unit)
			if unit.kind == "glyph":
				for path: PackedVector2Array in glyph_paths(unit.value):
					var positioned := PackedVector2Array()
					for point: Vector2 in path:
						positioned.append(point + unit.origin)
					result.strokes.append(positioned)
				cursor += ADVANCE
			else:
				cursor += PUNCTUATION_ADVANCE
	result.rows = row + 1
	result.end = Vector2(cursor, -row * LINE_HEIGHT)
	return result

## One filled quad per orthogonal segment. Only neighbors in the same
## polyline join; a repeated endpoint also joins the first and last segments.
static func expand_strokes(paths: Array[PackedVector2Array]) -> Array[PackedVector2Array]:
	var quads: Array[PackedVector2Array] = []
	var half := STROKE_WIDTH / 2.0
	for path: PackedVector2Array in paths:
		if path.size() < 2:
			push_error("Naleya: a stroke needs at least two points")
			return []
		var closed := path[0] == path[path.size() - 1]
		for index: int in range(path.size() - 1):
			var start := path[index]
			var finish := path[index + 1]
			var delta := finish - start
			if delta == Vector2.ZERO or (delta.x != 0.0 and delta.y != 0.0):
				push_error("Naleya: stroke segments must be nonzero and orthogonal")
				return []
			var direction := delta.normalized()
			var normal := Vector2(-direction.y, direction.x) * half
			if closed or index > 0:
				start -= direction * half
			if closed or index < path.size() - 2:
				finish += direction * half
			quads.append(PackedVector2Array([
				start + normal, start - normal, finish - normal, finish + normal,
			]))
	return quads
