class_name ShipTextCache
extends Node
## A scene's shared raster queue. Completed pairs never retain viewport textures.

const MAX_UNREFERENCED: int = 32

class Pair:
	extends RefCounted
	var key: String
	var native: String
	var perceived_es: String
	var style: StringName
	var _native: ImageTexture
	var _perceived: ImageTexture
	func ready() -> bool:
		return _native != null
	func native_texture() -> ImageTexture:
		assert(ready(), "pair has completed rasterization")
		return _native
	func perceived_texture() -> ImageTexture:
		assert(ready(), "pair has completed rasterization")
		return _perceived

class Entry:
	extends RefCounted
	var pair: Pair
	var references: int = 0
	var touched: int = 0

signal pair_ready(key: String)
var _entries: Dictionary = {}
var _queue: Array[String] = []
var _views: Array[SubViewport] = []
var _canvases: Array[ShipTextCanvas] = []
var _clock: int = 0
var _rendering: String = ""
var rasterized_pairs: int = 0

func acquire(text: ShipText.LabelText, style: StringName) -> Pair:
	var size := ShipTextCanvas.size_for(style)
	var key := JSON.stringify([text.native, text.perceived_es, String(style), size.x, size.y, ShipTextCanvas.LAYOUT_VERSION, ThemeDB.fallback_font.get_instance_id()])
	if not _entries.has(key):
		var entry := Entry.new()
		entry.pair = Pair.new()
		entry.pair.key = key
		entry.pair.native = text.native
		entry.pair.perceived_es = text.perceived_es
		entry.pair.style = style
		_entries[key] = entry
		_queue.append(key)
	var entry: Entry = _entries[key]
	entry.references += 1
	_clock += 1
	entry.touched = _clock
	return entry.pair

func release(key: String) -> void:
	var entry: Entry = _entries[key]
	assert(entry.references > 0, "release balances acquire")
	entry.references -= 1
	_clock += 1
	entry.touched = _clock
	_trim()

func _trim() -> void:
	var idle: Array[String] = []
	for key: String in _entries:
		if _entries[key].references == 0 and key != _rendering:
			idle.append(key)
	idle.sort_custom(func(a: String, b: String) -> bool: return _entries[a].touched < _entries[b].touched)
	while idle.size() > MAX_UNREFERENCED:
		var key: String = idle.pop_front()
		_queue.erase(key)
		_entries.erase(key)

func pending_count() -> int:
	return _queue.size() + (0 if _rendering.is_empty() else 1)

func unreferenced_count() -> int:
	var count := 0
	for entry: Entry in _entries.values():
		if entry.references == 0:
			count += 1
	return count

func raster_viewport_count() -> int:
	return _views.size()

## Also the headless seam: unit tests supply raster images without awaiting a GPU.
func complete(key: String, native: Image, perceived: Image) -> void:
	var pair: Pair = _entries[key].pair
	assert(not pair.ready(), "completed pairs are immutable")
	assert(not native.is_empty() and native.get_size() == perceived.get_size(), "raster pair dimensions match")
	pair._native = ImageTexture.create_from_image(native)
	pair._perceived = ImageTexture.create_from_image(perceived)
	_queue.erase(key)
	rasterized_pairs += 1
	pair_ready.emit(key)

func _process(_delta: float) -> void:
	if DisplayServer.get_name() == "headless" or not _rendering.is_empty() or _queue.is_empty():
		return
	_raster_next()

func _raster_next() -> void:
	_rendering = _queue.pop_front()
	var pair: Pair = _entries[_rendering].pair
	if _views.is_empty():
		for index: int in range(2):
			var view := SubViewport.new()
			view.name = "NativeRaster" if index == 0 else "PerceivedRaster"
			view.transparent_bg = true
			view.disable_3d = true
			view.render_target_update_mode = SubViewport.UPDATE_DISABLED
			add_child(view)
			var canvas := ShipTextCanvas.new()
			canvas.native = index == 0
			view.add_child(canvas)
			_views.append(view)
			_canvases.append(canvas)
	for index: int in range(2):
		_views[index].size = ShipTextCanvas.size_for(pair.style)
		_canvases[index].set_lines(pair.native if index == 0 else pair.perceived_es, pair.style)
		_views[index].render_target_update_mode = SubViewport.UPDATE_ONCE
	await RenderingServer.frame_post_draw
	complete(_rendering, _views[0].get_texture().get_image(), _views[1].get_texture().get_image())
	_rendering = ""
	_trim()
