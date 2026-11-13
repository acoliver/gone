extends SceneTree
## Diagnostic camera over main.tscn. Does not replace or alter normal startup.

const OUT := "res://tmp/verify-stasis-wiring/seat-production/"
var main: Node3D
var camera: Camera3D
var views: Array[Dictionary] = []

func _init() -> void:
	_run.call_deferred()

func _v(p: Vector3) -> Array:
	return [p.x,p.y,p.z]

func _shot(label: String, eye: Vector3, target: Vector3, fov: float) -> void:
	var frame := (main.game as Game).layout.bay_to_world()
	camera.global_position = frame*eye
	camera.look_at(frame*target)
	camera.fov = fov
	camera.current = true
	for i in range(12): await process_frame
	RenderingServer.call_deferred("force_draw",false)
	await RenderingServer.frame_post_draw
	await process_frame
	RenderingServer.call_deferred("force_draw",false)
	await RenderingServer.frame_post_draw
	var image := root.get_texture().get_image()
	assert(image != null and image.get_size()==Vector2i(1280,900),"native readback at requested size")
	var path := OUT+label+".png"
	assert(image.save_png(path)==OK,"fresh production capture")
	views.append({"file":path.trim_prefix("res://"),"sha256":FileAccess.get_sha256(path),"bay_eye_m":_v(eye),"bay_target_m":_v(target),"fov_degrees":fov,"native_materials":true,"additional_lights":0})

func _run() -> void:
	assert(DisplayServer.get_name()!="headless","native GPU production captures required")
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	root.size = Vector2i(1280,900)
	root.content_scale_mode = Window.CONTENT_SCALE_MODE_VIEWPORT
	root.content_scale_size = root.size
	DisplayServer.window_set_size(root.size)
	DirAccess.make_dir_recursive_absolute(OUT)
	main = (load("res://main.tscn") as PackedScene).instantiate()
	root.add_child(main)
	# Freeze the diagnostic instance, then inspect past its presentation overlay.
	# The production entry scene still constructs every normal opening system.
	main.process_mode = Node.PROCESS_MODE_DISABLED
	main.wake_pass.visible = false
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	camera = Camera3D.new()
	camera.near = 0.01
	camera.far = 50
	root.add_child(camera)
	var lighting := main.find_child("Lighting",true,false) as Lighting
	assert(lighting!=null,"actual main room lighting exists")
	for i in range(60): lighting.process_frame(1.0/60.0)
	await _shot("production-emergency-red",Vector3(1.4,1.65,0.8),Vector3(-0.6,1.50,-1.1),105)
	assert(main.game.press_console(),"diagnostic secondary power advance")
	for i in range(60): lighting.process_frame(1.0/60.0)
	await _shot("production-secondary-white",Vector3(1.4,1.65,0.8),Vector3(-0.6,1.50,-1.1),105)
	await _shot("production-ceiling-detail",Vector3(-0.6,2.30,-0.95),Vector3(-0.6,3.00,-0.6),85)
	await _shot("production-floor-pickup",Vector3(-0.9,0.70,-0.7),Vector3(-0.6,0.022,-1.4),65)
	var sources := {}
	for file: String in ["app/main.gd","main.tscn","app/rod.gd","app/bay_ceiling.gd","app/seat_rail_mesh.gd","app/seat_rail_component.gd","app/lighting.gd","assets/props/stasis-wiring/seat-rail/manifest.json","assets/props/stasis-wiring/seat-rail/full.glb","assets/props/stasis-wiring/seat-rail/left.glb","assets/props/stasis-wiring/seat-rail/middle.glb","assets/props/stasis-wiring/seat-rail/right.glb"]:
		sources[file] = FileAccess.get_sha256("res://"+file)
	var manifest := {"root":"res://main.tscn","diagnostic_only":true,"normal_game_launch":false,"diagnostic_changes":["freeze instance processing","hide eyelid overlay for inspection camera","press console for white circuit"],"lighting":"production fixtures and materials, no inspection lights or overrides","size":[1280,900],"display":DisplayServer.get_name(),"adapter":RenderingServer.get_video_adapter_name(),"captures":views,"sources_sha256":sources,"visual_judgment":"Parent image-comparer pending; capture tool makes no image-quality judgment.","performance":"No performance claim; concurrent sibling render jobs may contend."}
	FileAccess.open(OUT+"capture-manifest.json",FileAccess.WRITE).store_string(JSON.stringify(manifest,"\t")+"\n")
	print("SEAT_PRODUCTION_CAPTURE_PASS root=main.tscn captures=4 native_materials=true diagnostic_only=true")
	for light: Light3D in main.find_children("*","Light3D",true,false): light.hide()
	for i in range(3): await process_frame
	RenderingServer.call_deferred("force_draw",false)
	await RenderingServer.frame_post_draw
	quit(0)
