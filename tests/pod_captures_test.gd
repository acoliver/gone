extends SimTestCase

const Captures := preload("res://tools/pod_captures.gd")

func test_red_clipping_distinguishes_hdr_clipping_from_png_rounding() -> void:
	var linear := _image(Image.FORMAT_RGBH,Color.BLACK)
	var png := _image(Image.FORMAT_RGB8,Color.BLACK)
	var mask := _image(Image.FORMAT_RGB8,Color.WHITE)
	linear.set_pixel(4,4,Color(.9995,0,0))
	linear.set_pixel(5,5,Color(1.0,0,0))
	png.set_pixel(4,4,Color.RED)
	png.set_pixel(5,5,Color.RED)
	var stats := Captures._red_clipping(linear,png,mask,mask)
	assert_int_equal(stats.pixels,36,"the aperture excludes its two-pixel border")
	assert_int_equal(stats.clipped_pixels,1,"only half-float red at or above one is clipped")
	assert_int_equal(stats.png_saturated_pixels,2,"PNG saturation includes near-white rounding")
	assert_float_equal(stats.clipped_fraction,1.0/36.0,"clipping uses the selected fabric's pixel count")

func test_red_clipping_excludes_other_geometry_and_the_pane_boundary() -> void:
	var linear := _image(Image.FORMAT_RGBH,Color.RED)
	var png := _image(Image.FORMAT_RGB8,Color.RED)
	var mask := _image(Image.FORMAT_RGB8,Color.BLACK)
	var aperture := _image(Image.FORMAT_RGB8,Color.WHITE)
	mask.set_pixel(4,4,Color.WHITE)
	linear.set_pixel(4,4,Color.BLACK)
	png.set_pixel(4,4,Color.BLACK)
	var stats := Captures._red_clipping(linear,png,mask,aperture)
	assert_int_equal(stats.pixels,1,"only selected fabric enters the measurement")
	assert_int_equal(stats.clipped_pixels,0,"bright fixtures outside the fabric mask are excluded from the measurement")
	aperture.set_pixel(6,4,Color.BLACK)
	stats = Captures._red_clipping(linear,png,mask,aperture)
	assert_int_equal(stats.pixels,0,"fabric beside the pane boundary is excluded")

func _image(format: Image.Format,color: Color) -> Image:
	var image := Image.create(10,10,false,format)
	image.fill(color)
	return image
