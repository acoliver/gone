extends SceneTree
## Windowed raster boundary, independent of logical-time tests.

func _initialize() -> void:
	_run.call_deferred()

func _run() -> void:
	var cache := ShipTextCache.new()
	root.add_child(cache)
	var hatch := cache.acquire(ShipText.hatch_label(14, 41), &"navigation")
	var lift := cache.acquire(ShipText.deck_label(14), &"navigation")
	var inactive := cache.acquire(ShipText.LabelText.new("te mu nawa lina\npalo", "SISTEMA DE ENERGÍA SECUNDARIO\nINACTIVO"), &"console")
	var active := cache.acquire(ShipText.LabelText.new("te mu nawa lina\nshenu", "SISTEMA DE ENERGÍA SECUNDARIO\nEN FUNCIONAMIENTO"), &"console")
	var frames := 0
	while cache.pending_count() > 0:
		await process_frame
		frames += 1
		assert(frames < 120, "raster queue must complete")
	assert(cache.raster_viewport_count() == 2, "one shared pair of raster viewports")
	assert(hatch.native_texture() is ImageTexture and hatch.perceived_texture() is ImageTexture, "immutable image textures")
	var original := hatch.native_texture().get_image().get_data()
	assert(original != hatch.perceived_texture().get_image().get_data(), "native and Spanish are separate pixels")
	assert(inactive.native_texture().get_image().get_data() != active.native_texture().get_image().get_data(), "console state raster differs")
	assert(_ink_pixels(hatch.native_texture().get_image()) > 1000, "native raster contains ink")
	assert(_ink_pixels(hatch.perceived_texture().get_image()) > 1000, "perceived raster contains ink")
	var later := cache.acquire(ShipText.hatch_label(30, 43), &"navigation")
	while not later.ready(): await process_frame
	assert(hatch.native_texture().get_image().get_data() == original, "later raster does not alias earlier pixels")
	assert(cache.acquire(ShipText.hatch_label(14, 41), &"navigation") == hatch, "hit reuses completed pair")
	assert(cache.pending_count() == 0, "hit performs no raster work")
	var proof := Image.create(2304, 1296, false, Image.FORMAT_RGBA8)
	proof.fill(Color(0.025, 0.03, 0.04, 1))
	for row: int in range(2):
		var pair := hatch if row == 0 else lift
		var native := pair.native_texture().get_image()
		var perceived := pair.perceived_texture().get_image()
		if row == 1:
			# Flatten the cached lift raster at its actual 4:1 sign aspect ratio.
			native.resize(1024, 256, Image.INTERPOLATE_LANCZOS)
			perceived.resize(1024, 256, Image.INTERPOLATE_LANCZOS)
		proof.blend_rect(native, Rect2i(Vector2i.ZERO, native.get_size()), Vector2i(64, 64 + row * 576))
		proof.blend_rect(perceived, Rect2i(Vector2i.ZERO, perceived.get_size()), Vector2i(1216, 64 + row * 576))
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path("res://tmp/connectors/s7-captures"))
	assert(proof.save_png("res://tmp/connectors/s7-captures/label-proof.png") == OK)
	print("CACHE INTEGRATION PASS: immutable pairs, distinct raster layers, two viewports, no aliasing; proof saved")
	quit(0)

func _ink_pixels(image: Image) -> int:
	var count := 0
	for y: int in range(image.get_height()):
		for x: int in range(image.get_width()):
			if image.get_pixel(x, y).a > 0.5: count += 1
	return count
