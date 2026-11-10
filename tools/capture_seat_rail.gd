extends SceneTree
## Six current-material proof sheets, isolated from normal startup and lighting.

const Presenter = preload("res://app/stasis_wiring.gd")
const Rail = preload("res://app/seat_rail_component.gd")
const OUT := "res://tmp/verify-stasis-wiring/seat-rail/"
var captures: Array[Dictionary] = []

func _init() -> void:
	_run.call_deferred()

func _meshes(node: Node, result: Array[MeshInstance3D]) -> void:
	if node is MeshInstance3D: result.append(node as MeshInstance3D)
	for child: Node in node.get_children(): _meshes(child,result)

func _world(mode: String) -> Node3D:
	var world := Node3D.new()
	root.add_child(world)
	if mode == "study":
		var study := (load(Rail.DIR + "study.glb") as PackedScene).instantiate() as Node3D
		world.add_child(study)
		var pieces: Array[MeshInstance3D] = []
		_meshes(study,pieces)
		for piece: MeshInstance3D in pieces: piece.material_override = Rail.material()
	else:
		var proof := Presenter.build(&"fault-frame-pair")
		world.add_child(proof)
		if mode == "isolated": Presenter.isolate_fragment(proof)
		if mode == "healthy" or mode == "missing":
			var pieces: Array[MeshInstance3D] = []
			_meshes(proof,pieces)
			for piece: MeshInstance3D in pieces:
				if String(piece.name).begins_with("fallen_fragment"): piece.visible = false
		if mode == "healthy":
			var middle := Rail.build(&"middle")
			middle.position = BayCeiling.FAILED_SEAT_CENTER
			world.add_child(middle)
			Presenter._panel(proof.get_node("ProofContext"),Vector3(-0.6,2.99,-0.9))
	return world

func _view(mode: String, eye: Vector3, target: Vector3, size: Vector2i, fov: float, red: bool = false) -> Image:
	root.size = size
	root.content_scale_mode = Window.CONTENT_SCALE_MODE_VIEWPORT
	root.content_scale_size = size
	DisplayServer.window_set_size(size)
	var world := _world(mode)
	var environment := WorldEnvironment.new()
	environment.environment = Environment.new()
	environment.environment.background_mode = Environment.BG_COLOR
	environment.environment.background_color = Color(0.64,0.66,0.68) if mode == "study" else Color(0.025,0.028,0.032)
	environment.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.environment.ambient_light_color = Color(0.55,0.60,0.68)
	environment.environment.ambient_light_energy = 0.10
	world.add_child(environment)
	var center := target if mode in ["study","isolated"] else Vector3(-0.6,1.65,-0.9)
	var offsets: Array[Vector3] = [Vector3(0.2,0.7,1.5),Vector3(-1.5,0.2,0.5),Vector3(1.0,0.9,-0.3)]
	for index: int in range(3):
		var light := OmniLight3D.new()
		light.position = center+offsets[index]
		light.omni_range = 5.0
		light.omni_attenuation = 1.6
		light.light_energy = [3.8,2.2,1.4][index]
		light.light_color = Color(1.0,0.035,0.012) if red else Color(1.0,0.95,0.86)
		light.shadow_enabled = true
		world.add_child(light)
	var camera := Camera3D.new()
	camera.near = 0.003
	camera.far = 20
	camera.fov = fov
	camera.keep_aspect = Camera3D.KEEP_WIDTH
	world.add_child(camera)
	camera.position = eye
	camera.look_at(target)
	camera.current = true
	for frame: int in range(12): await process_frame
	RenderingServer.force_draw(false)
	await RenderingServer.frame_post_draw
	await process_frame
	RenderingServer.force_draw(false)
	await RenderingServer.frame_post_draw
	var image := root.get_texture().get_image()
	assert(image != null and image.get_size() == size,"actual current-size GPU readback")
	var low := 1.0
	var high := 0.0
	var total := 0.0
	var squared := 0.0
	var count := 0
	for y: int in range(0,size.y,8):
		for x: int in range(0,size.x,8):
			var color := image.get_pixel(x,y)
			var value := (color.r+color.g+color.b)/3.0
			low = minf(low,value)
			high = maxf(high,value)
			total += value
			squared += value*value
			count += 1
	var variance := squared/count-pow(total/count,2)
	assert(high-low >= 0.015 and variance >= 0.00001,"non-uniform, non-black proof readback")
	var row := {"mode":mode,"eye":[eye.x,eye.y,eye.z],"target":[target.x,target.y,target.z],"size":[size.x,size.y],"fov":fov,"red":red,"readback_range":high-low,"readback_variance":variance}
	captures.append(row)
	world.free()
	await process_frame
	return image

func _save(image: Image, name: String) -> void:
	var path := OUT+name+".png"
	assert(not FileAccess.file_exists(path),"keep existing proof captures immutable")
	assert(image.save_png(path)==OK,"save rendered proof")

func _join(images: Array[Image], widths: Array[int]) -> Image:
	var result := Image.create(1280,960,false,Image.FORMAT_RGBA8)
	result.fill(Color(0.09,0.10,0.12))
	var x := 0
	for index: int in range(images.size()):
		var image := images[index]
		image.convert(Image.FORMAT_RGBA8)
		image.resize(widths[index],960,Image.INTERPOLATE_LANCZOS)
		result.blit_rect(image,Rect2i(Vector2i.ZERO,image.get_size()),Vector2i(x,0))
		x += widths[index]
	return result

func _hashes() -> Dictionary:
	var hashes: Dictionary = {}
	var paths: Array[String] = ["res://tools/capture_seat_rail.gd","res://app/seat_rail_component.gd","res://app/stasis_wiring.gd","res://tools/seat_rail.py","res://tools/build_seat_rail.py","res://tools/seat_rail_proof.py","res://tools/stasis_wiring_assemblies.py","res://tools/build_stasis_wiring.py","res://tools/blender/seat_rail.py","res://tools/blender/stasis_wiring_proofs.py","res://assets/props/stasis-wiring/fault-frame-pair.glb","res://assets/props/stasis-wiring/proof-assemblies.json","res://assets/props/stasis-wiring/stasis-wiring-enclosure.glb","res://assets/props/bay-ceiling/intact.glb","res://app/bay_ceiling_material.gd","res://app/surfaces.gd","res://app/shaders/weathered_steel.gdshader","res://art-source/stasis-wiring/seat-rail/concept.png","res://art-source/stasis-wiring/seat-rail/guide.glb"]
	for name: String in ["full.glb","left.glb","middle.glb","right.glb","study.glb","steel-albedo.png","steel-orm.png","steel-normal.png","manifest.json"]: paths.append(Rail.DIR+name)
	for name: String in DirAccess.get_files_at(Rail.DIR):
		if name.ends_with(".png"): paths.append(Rail.DIR+name)
	for path: String in paths:
		assert(FileAccess.file_exists(path),"capture source exists: "+path)
		hashes[path]=FileAccess.get_sha256(path)
	return hashes

func _run() -> void:
	assert(DisplayServer.get_name()!="headless","actual GPU rendering required")
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	root.msaa_3d = Viewport.MSAA_4X
	var before := _hashes()
	var study := await _view("study",Vector3(-0.27,-0.13,0.24),Vector3(0,-0.009,0),Vector2i(640,960),43)
	var concept := Image.load_from_file("res://art-source/stasis-wiring/seat-rail/concept.png")
	assert(concept != null,"new concept loads")
	# Preserve the whole concept image with letterboxing rather than stretching it.
	concept.resize(640,480,Image.INTERPOLATE_LANCZOS)
	concept.convert(Image.FORMAT_RGBA8)
	var letterbox := Image.create(640,960,false,Image.FORMAT_RGBA8)
	letterbox.fill(Color(0.64,0.66,0.68))
	letterbox.blit_rect(concept,Rect2i(Vector2i.ZERO,concept.get_size()),Vector2i(0,240))
	_save(_join([letterbox,study],[640,640]),"01-concept-vs-modeled-profile")
	_save(await _view("healthy",Vector3(0.35,2.14,-0.12),BayCeiling.FAILED_SEAT_CENTER-Vector3(0,.006,0),Vector2i(1280,960),52),"02-healthy-installed-seat")
	var full := await _view("isolated",Vector3(-1.25,0.38,-0.63),Vector3(-0.6,0.012,-1.4),Vector2i(960,960),52)
	var end := Rail.floor_pose()*Vector3(-0.5,-0.009,0)
	var detail := await _view("isolated",end+Vector3(-0.19,0.045,0.06),end,Vector2i(320,960),42)
	_save(_join([full,detail],[960,320]),"03-detached-stick-and-torn-end")
	_save(await _view("fault",Vector3(-0.8,1.65,-0.25),Vector3(-0.6,0.012,-1.4),Vector2i(1280,960),65),"04-floor-pickup-standing")
	var assembled := await _view("healthy",Vector3(-0.25,2.55,-0.24),BayCeiling.FAILED_SEAT_CENTER-Vector3(0,.008,0),Vector2i(1280,320),64)
	var missing := await _view("missing",Vector3(-0.25,2.55,-0.24),BayCeiling.FAILED_SEAT_CENTER-Vector3(0,.008,0),Vector2i(1280,320),64)
	var fallen := await _view("isolated",Vector3(-1.25,0.38,-0.63),Vector3(-0.6,0.012,-1.4),Vector2i(1280,320),64)
	var diagram := Image.create(1280,960,false,Image.FORMAT_RGBA8)
	var diagram_views: Array[Image] = [assembled,missing,fallen]
	for index: int in range(3):
		diagram_views[index].convert(Image.FORMAT_RGBA8)
		diagram.blit_rect(diagram_views[index],Rect2i(0,0,1280,320),Vector2i(0,index*320))
	_save(diagram,"05-assembled-missing-fallen")
	var white := await _view("fault",Vector3(1.45,1.62,1.7),Vector3(-0.6,1.56,-1.06),Vector2i(640,960),64)
	var red := await _view("fault",Vector3(1.45,1.62,1.7),Vector3(-0.6,1.56,-1.06),Vector2i(640,960),64,true)
	_save(_join([white,red],[640,640]),"06-fault-white-red")
	assert(before==_hashes(),"source geometry and PBR unchanged across all captures")
	var outputs: Dictionary = {}
	for path: String in DirAccess.get_files_at(OUT):
		if path.ends_with(".png"): outputs[path]=FileAccess.get_sha256(OUT+path)
	var manifest := {"source_sha256":before,"outputs_sha256":outputs,"views":captures,"renderer":RenderingServer.get_video_adapter_name(),"display":DisplayServer.get_name(),"materials":"One shared imported image-derived gray steel PBR, source UV retained in healthy/stubs/fallen. Existing BayCeiling panels and context surface materials unchanged.","layout":"01 concept left/model right; 03 full piece left/torn end right; 05 assembled/missing/fallen top to bottom; 06 white left/red right.","review":"Pending parent image-comparer. Capture worker made no visual judgments."}
	FileAccess.open(OUT+"capture-manifest.json",FileAccess.WRITE).store_string(JSON.stringify(manifest,"\t")+"\n")
	print("SEAT_RAIL_CAPTURE_PASS six current-material sheets")
	quit(0)
