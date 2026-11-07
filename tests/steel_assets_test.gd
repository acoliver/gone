extends SimTestCase

const ROOT := "res://assets/surfaces/steel/"
const HASHES := {
	"r4-green_metal_rust-albedo.png": "9b5de492bdfdf3aa76d2d69c41a0e36350b72371ac8ebf125af219ff64533b7a",
	"r4-rusty_painted_metal-albedo.png": "d3838a76509131ca4bc3d152e9f6b09b3facc22c73a1a653cbef84e4f15adcff",
	"r4-rusty_metal_04-albedo.png": "e9cda2b8d6d1b5346c8ed1375b914d06fba311d33e2afa6b0191b3c0a974d418",
	"green_metal_rust_normal.jpg": "8ecb28b0ea4026b740ce492e3f606f61a76bdce1f78cb2e29287bf9a56c54a80",
	"green_metal_rust_orm.jpg": "c1a48da0c5bba8f490497bbedadf4cb21d5387de8b3d49988c065e4b16805434",
	"rusty_painted_metal_normal.jpg": "f3372e2f60517df2d0e02c1472eb24071d95182d771c30b7ecd8e1b5142768bb",
	"rusty_painted_metal_orm.jpg": "cd3ef3750348bd8afa552ac41120310f740cd4bfd3c303d81e68e3100bdf7fdd",
	"rusty_metal_04_normal.jpg": "9c432bee334e65e73ff0b20676dd3f0efbed3f91d261a13dc03b9c8c1a4f4eec",
	"rusty_metal_04_orm.jpg": "b040e35ed5e885d04b465761782a5d0ebd241175f562821f8fba35a12dccb789",
	"r3-rust_coarse_01-albedo.jpg": "369f69eb86a7dcc4e5b6e30b1f3a4da5ce6ba50cf417de937efb4f09101f88d4",
	"r3-rust_coarse_01-normal.jpg": "08ae69576b453b0970f5982d359897f09aae41c7cb18c19c02de37324160625c",
}

func test_approved_scan_inventory_and_bytes() -> void:
	assert_true(DirAccess.dir_exists_absolute(ROOT), "approved steel resources are shipped")
	if not DirAccess.dir_exists_absolute(ROOT): return
	var actual: Array[String] = []
	for file: String in DirAccess.get_files_at(ROOT):
		if file.ends_with(".jpg") or file.ends_with(".png"): actual.append(file)
	actual.sort()
	var expected := HASHES.keys()
	expected.sort()
	assert_true(actual == expected, "only the eleven sampled Round 5 images are runtime assets")
	for file: String in HASHES:
		assert_true(FileAccess.get_sha256(ROOT + file) == HASHES[file], "approved bytes: " + file)
		var image := Image.load_from_file(ROOT + file)
		assert_true(image != null and image.get_size() == Vector2i(1024, 1024), "1K scan: " + file)
	assert_true(FileAccess.file_exists(ROOT + "SOURCES.md"), "CC0 provenance ships beside textures")
	assert_true(FileAccess.file_exists(ROOT + "CC0-1.0.txt"), "full license ships beside textures")

func test_explicit_import_channels_mips_and_compression() -> void:
	for file: String in HASHES:
		var config := ConfigFile.new()
		assert_int_equal(config.load(ROOT + file + ".import"), OK, "import recipe: " + file)
		if not config.has_section("params"): continue
		var normal := "normal" in file
		assert_int_equal(config.get_value("params", "compress/mode"), 2, "VRAM compression")
		assert_true(config.get_value("params", "compress/high_quality") == (not normal), "BC7 colour/ORM and BC5 normals")
		assert_int_equal(config.get_value("params", "compress/normal_map"), 1 if normal else 2, "explicit normal/data interpretation")
		assert_true(config.get_value("params", "mipmaps/generate"), "mip chain")
		assert_int_equal(config.get_value("params", "mipmaps/limit"), -1, "full mip chain")
		assert_int_equal(config.get_value("params", "process/size_limit"), 1024, "bounded source dimensions")
		for option: String in ["process/fix_alpha_border", "process/premult_alpha", "process/normal_map_invert_y"]:
			assert_false(config.get_value("params", option), "no image reinterpretation: " + option)
		assert_int_equal(config.get_value("params", "detect_3d/compress_to"), 0, "no automatic reclassification")

func test_old_shipped_source_maps_retain_their_prepared_luminance() -> void:
	for entry: Array in [["wall", 94.95], ["floor", 84.13], ["ceiling", 77.81]]:
		var image := Image.load_from_file("res://assets/surfaces/%s/albedo.png" % entry[0])
		var total := 0.0
		for y: int in range(image.get_height()):
			for x: int in range(image.get_width()):
				var color := image.get_pixel(x, y)
				total += (color.r8 + color.g8 + color.b8) / 3.0
		assert_true(absf(total / (image.get_width() * image.get_height()) - entry[1]) <= 2.0 / 255.0, "retained legacy source fidelity: %s" % entry[0])
