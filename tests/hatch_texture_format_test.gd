extends SimTestCase

const ROOT := "res://assets/props/hatch/"

func test_albedo_is_bc7_with_full_mips() -> void:
	_assert_texture("hatch_albedo.png", Image.FORMAT_BPTC_RGBA)

func test_normal_is_bc5_with_full_mips() -> void:
	_assert_texture("hatch_normal.png", Image.FORMAT_RGTC_RG)

func test_orm_is_bc7_with_full_mips() -> void:
	_assert_texture("hatch_orm.png", Image.FORMAT_BPTC_RGBA)

func _assert_texture(file: String, expected_format: int) -> void:
	var texture: Texture2D = load(ROOT + file)
	assert_true(texture != null, "imported texture: " + file)
	if texture == null: return
	var image := texture.get_image()
	assert_true(image != null, "imported image: " + file)
	if image == null: return
	print("TEXTURE %s format=%d bytes=%d mips=%d size=%s" % [
		file, image.get_format(), image.get_data().size(),
		image.get_mipmap_count(), image.get_size(),
	])
	assert_int_equal(image.get_format(), expected_format, "actual compressed format: " + file)
	assert_true(image.get_size() == Vector2i(2048, 2048), "required atlas resolution: " + file)
	assert_true(image.has_mipmaps(), "actual mipmaps: " + file)
	assert_int_equal(image.get_mipmap_count(), 11, "complete mip chain to 1x1: " + file)
	assert_int_equal(image.get_data().size(), 5592432, "actual block-compressed bytes with full mips: " + file)
