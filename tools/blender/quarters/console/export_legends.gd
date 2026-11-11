extends SceneTree
## Export exactly the native ink used by ShipTextCanvas, without a font path.

const Writing := preload("res://app/naleya.gd")
const TOKENS := "0 1 2 3 4 5 6 7 a e i o u pa pe pi po pu ta te ti to tu ka ke ki ko ku ma"

func _initialize() -> void:
	var keys: Array[Dictionary] = []
	var tokens := TOKENS.split(" ")
	for index: int in range(tokens.size()):
		var input := tokens[index]
		var layout := Writing.layout(input, Writing.ADVANCE)
		assert(layout != null and layout.units.size() == 1 and layout.units[0].kind == "glyph", "one valid native sign per key")
		var quads: Array = []
		for quad: PackedVector2Array in Writing.expand_strokes(layout.strokes):
			var points: Array = []
			for point: Vector2 in quad: points.append([point.x, point.y])
			quads.append(points)
		keys.append({"key": "Cap_%02d" % (index + 1), "design_index": index + 1, "input": input, "sign": layout.units[0].value, "quads": quads})
	var document := {"source": "app/naleya.gd: layout/glyph_paths/expand_strokes", "renderer": "app/ship_text_canvas.gd:_append_native", "syllables": Writing.SYLLABLES, "digits": Writing.DIGITS, "stroke_width": Writing.STROKE_WIDTH, "keys": keys}
	var file := FileAccess.open("res://tools/blender/quarters/console/legends.json", FileAccess.WRITE)
	assert(file != null, "native legend output")
	file.store_string(JSON.stringify(document, "  ") + "\n")
	print("Exported 29 native key legends using production Naleya layout and stroke expansion")
	quit()
