extends SceneTree
## Copies presentation images without altering the harness's decoded originals.

const BEATS := [
	"corridor-door", "remembered-doorway", "remembered-wide", "present-doorway", "present-wide",
	"remembered-console", "present-console", "console-corruption", "console-message", "console-fault",
	"remembered-bed", "present-bed",
]

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	assert(args.size() == 2, "usage: -s tools/quarters_presentation.gd -- <harness-run-dir> <presentation-dir>")
	var source := ProjectSettings.globalize_path(args[0])
	var output := ProjectSettings.globalize_path(args[1])
	assert(DirAccess.make_dir_recursive_absolute(output) == OK, "presentation output directory")
	var top := HarnessProtocol.chip_size().y
	for beat: String in BEATS:
		var image := Image.load_from_file(source.path_join("beats/" + beat + ".png"))
		assert(image != null and image.get_height() > top, "valid capture for " + beat)
		var crop := image.get_region(Rect2i(0, top, image.get_width(), image.get_height() - top))
		assert(crop.save_png(output.path_join(beat + ".png")) == OK, "presentation output for " + beat)
	print("PRESENTATION images=%d cropped_top=%d originals_unchanged=true" % [BEATS.size(), top])
	quit()
