extends SceneTree
## Native windowed render truth. Green behind opaque closed steel must never reach the aperture.

const EYES: Array[Vector2] = [Vector2(0, 1.4), Vector2(-0.4, 0.6), Vector2(0.4, 0.6), Vector2(-0.4, 2.2), Vector2(0.4, 2.2)]
var camera: Camera3D
var backdrop: MeshInstance3D
var total_green := 0
var samples := 0
var checks := 0

func _initialize() -> void: call_deferred("run")

func run() -> void:
	assert(DisplayServer.get_name() != "headless", "render truth requires a native window")
	var scene := Node3D.new()
	root.add_child(scene)
	camera = Camera3D.new()
	scene.add_child(camera)
	camera.current = true
	var environment := WorldEnvironment.new()
	environment.environment = Environment.new()
	environment.environment.background_mode = Environment.BG_COLOR
	environment.environment.background_color = Color.BLACK
	scene.add_child(environment)
	var green := StandardMaterial3D.new()
	green.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	green.albedo_color = Color.GREEN
	green.cull_mode = BaseMaterial3D.CULL_DISABLED
	backdrop = HatchModel.mesh_piece(HatchModel.box_mesh(Vector3(10, 10, 0.02)), Transform3D.IDENTITY, 1, green)
	scene.add_child(backdrop)
	var layout := ShipLayout.authored().layout
	var hatches := 0
	for id: StringName in layout.door_ids():
		var spec := layout.door(id)
		if spec.animation() != ShipLayout.AnimationRecipe.HINGE: continue
		hatches += 1
		var view := DoorView.build(spec)
		if OS.has_environment("GONE_SEAL_NEGATIVE_CONTROL"):
			preload("res://tests/hatch_mesh_ranges.gd").remove_seals(view)
		scene.add_child(view)
		var walls := Node3D.new()
		walls.transform = spec.frame()
		scene.add_child(walls)
		var solids := ShipGeometry.doorway_wall_solids(layout) if id == ShipLayout.BAY_DOOR_ID else ShipGeometry.hatch_wall_solids(spec)
		for solid: ShipGeometry.SolidSpec in solids: walls.add_child(DoorView.split_surface(solid, spec.frame(), 1, 1))
		# The expanded corner check reaches the floor line. Include the floor
		# at its production datum so oblique rays cannot pass below the room.
		var floor_piece := HatchModel.mesh_piece(HatchModel.box_mesh(Vector3(8, ShipLayout.WALL, 8)), spec.frame() * Transform3D(Basis(), Vector3(0, -ShipLayout.WALL / 2, 0)), 1, HatchModel.flat_grey(0.2))
		scene.add_child(floor_piece)
		var inverse := spec.frame().affine_inverse()
		var aperture := spec.aperture()
		for side: int in [-1, 1]:
			backdrop.transform = spec.frame() * Transform3D(Basis(), Vector3(0, aperture.y / 2, ShipLayout.WALL / 2 - side * 1.0))
			for eye: Vector2 in EYES:
				camera.position = spec.frame() * Vector3(eye.x, eye.y, ShipLayout.WALL / 2 + side * 2.0)
				camera.look_at(spec.frame() * Vector3(0, aperture.y / 2, ShipLayout.WALL / 2))
				view.visible = false
				walls.visible = false
				floor_piece.visible = false
				await process_frame
				await RenderingServer.frame_post_draw
				var control := root.get_texture().get_image()
				var control_color := control.get_pixelv(camera.unproject_position(spec.frame() * Vector3(0, aperture.y / 2, ShipLayout.WALL / 2)))
				assert(control_color.g > 0.9 and control_color.r < 0.1 and control_color.b < 0.1, "uncovered aperture must see the green backdrop: %s" % control_color)
				view.visible = true
				walls.visible = true
				floor_piece.visible = true
				await process_frame
				await RenderingServer.frame_post_draw
				var image := root.get_texture().get_image()
				var green_pixels := 0
				var covered := 0
				# Project each pixel back onto the aperture plane, not a guessed screen crop.
				for y: int in range(image.get_height()):
					for x: int in range(image.get_width()):
						var pixel := Vector2(x + 0.5, y + 0.5)
						var origin := inverse * camera.project_ray_origin(pixel)
						var direction := inverse.basis * camera.project_ray_normal(pixel)
						var distance := (ShipLayout.WALL / 2 - origin.z) / direction.z
						var hit := origin + direction * distance
						# Include the whole former square pocket and the outer crown,
						# so rounded wall corners cannot escape the green check.
						if absf(hit.x) >= aperture.x / 2 + ShipGeometry.HATCH_RING_WIDTH or hit.y <= 0 or hit.y >= aperture.y + ShipGeometry.HATCH_RING_WIDTH: continue
						covered += 1
						var color := image.get_pixel(x, y)
						if color.g > 0.9 and color.r < 0.1 and color.b < 0.1: green_pixels += 1
				assert(covered > 1000, "aperture must occupy enough pixels to test")
				total_green += green_pixels
				samples += covered
				checks += 1
				print("RENDER_SEAL %s face=%+d eye=%s samples=%d green=%d" % [id, side, eye, covered, green_pixels])
				if green_pixels > 0:
					var args := OS.get_cmdline_user_args()
					var out := args[0].trim_suffix("/") + "/" if args.size() == 1 else "res://tmp/slit/render-red/"
					DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(out))
					if hatches <= 3: image.save_png(out + "%s-%d-%d.png" % [id, side, EYES.find(eye)])
		view.free()
		walls.free()
		floor_piece.free()
	print("RENDER_SEAL COMPLETE hatches=%d faces=%d checks=%d samples=%d green=%d" % [hatches, hatches * 2, checks, samples, total_green])
	quit(1 if total_green > 0 else 0)
