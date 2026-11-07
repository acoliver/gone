extends SceneTree
## #88: fixed production-scene captures and paired interior measurements.
var output := "res://tmp/pods/fix3/captures"
var stage: Node3D
var ship: ShipScene
var game: Game
var camera: Camera3D
var results: Dictionary = {}
var failures: Array[String] = []
var panes: Array[MeshInstance3D] = []
var meshes: Array[MeshInstance3D] = []
var sealed_red_linear: Image

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	for i: int in range(args.size()-1):
		if args[i] == "--out":
			output = args[i+1]
	_run.call_deferred()

func _run() -> void:
	root.size = Vector2i(1152,648)
	root.always_on_top = true
	DirAccess.make_dir_recursive_absolute(output)
	game = Game.new(0)
	stage = Node3D.new()
	root.add_child(stage)
	ship = ShipScene.build_into(stage,game)
	ship.hazards.auto_bursts = false
	ship.hazards.set_physics_process(false)
	ship.hazards._smoke_field.use_fixed_seed = true
	ship.hazards._smoke_field.seed = 88
	camera = Camera3D.new()
	camera.fov = 70
	stage.add_child(camera)
	for mesh: MeshInstance3D in stage.find_children("*","MeshInstance3D",true,false):
		meshes.append(mesh)
		if mesh.name == "WindowPane":
			panes.append(mesh)
	_pose(Vector3(5.2,2.2,3.2),Vector3(-2.8,.95,0))
	await _settle(30)
	ship.hazards._smoke_field.speed_scale = 0.0
	Engine.time_scale = 0.0 # Freeze shader TIME as well as the particle transforms for paired captures.
	for power: String in ["red","fade","white"]:
		if power == "fade":
			game.press_console()
			game.press_console()
		if power != "red":
			var elapsed := .25 if power == "fade" else 1.0
			ship.lighting.process_frame(elapsed)
			ship.hallway.process_frame(elapsed)
			ship.power_room.process_frame(elapsed)
			await _settle(30)
		_pose(Vector3(5.2,2.2,3.2),Vector3(-2.8,.95,0))
		await _capture("bay-wide-"+power)
		_pose(Vector3(-4.7,2.1,Pods.ROW_A_Z-.15),Vector3(-4.8,.30,Pods.ROW_A_Z-.25))
		var present := await _capture("sealed-close-"+power)
		_set_panes(false)
		var hidden := await _capture("sealed-close-"+power+"-pane-hidden")
		var couch: MeshInstance3D = ship.pods_node.get_node("Pod0/PodShell/PodBase/Couch")
		var pillow: MeshInstance3D = ship.pods_node.get_node("Pod0/PodShell/PodBase/Pillow")
		var couch_mask := await _mask(couch,"couch-mask-"+power)
		var pillow_mask := await _mask(pillow,"pillow-mask-"+power)
		_set_panes(true)
		var aperture := await _mask(panes[0],"pane-mask-"+power)
		_set_panes(false)
		for pair: Array in [["couch",couch_mask],["pillow",pillow_mask]]:
			if power == "red":
				var clipping := _red_clipping(sealed_red_linear,present,pair[1],aperture)
				results[pair[0]+"_red_clipping"] = clipping
				if pair[0] == "couch":
					_gate("couch_red_shape",clipping.pixels>=200 and clipping.clipped_fraction<=.20,clipping,.20)
			var stats := _interior(hidden,present,pair[1],power=="red")
			results[pair[0]+"_"+power] = stats
			_gate(pair[0]+"_"+power+"_coverage",stats.pixels>=200,stats.pixels,200)
			_gate(pair[0]+"_"+power+"_baseline",stats.reference_mean>.02,stats.reference_mean,.02)
			_gate(pair[0]+"_"+power+"_brightness",stats.median_ratio>=.85,stats.median_ratio,.85)
			_gate(pair[0]+"_"+power+"_black_fraction",stats.black_fraction<.01,stats.black_fraction,.01)
			var modulation := _boundary(hidden,present,pair[1],aperture,power=="red")
			_gate(pair[0]+"_"+power+"_boundary_baseline",modulation.pairs>0 and modulation.reference>.01,modulation,.01)
			_gate(pair[0]+"_"+power+"_boundary_transfer",modulation.reference>.01 and modulation.glass>=.8*modulation.reference,modulation,.8)
		_set_panes(true)
		# A checker substitution leaves the real opaque shell and lining intact.
		var material := ShaderMaterial.new()
		var shader := Shader.new()
		shader.code = "shader_type spatial; render_mode unshaded; varying vec3 p; void vertex(){p=VERTEX;} void fragment(){float c=mod(floor(p.x*18.0)+floor(p.z*18.0),2.0); ALBEDO=vec3(mix(0.025,0.175,c));}"
		material.shader = shader
		couch.material_override = material
		var witness := await _capture("checker-"+power)
		_set_panes(false)
		var witness_hidden := await _capture("checker-"+power+"-pane-hidden")
		results["checker_"+power] = _interior(witness_hidden,witness,couch_mask,power=="red")
		_gate("checker_"+power+"_brightness",results["checker_"+power].median_ratio>=.85,results["checker_"+power].median_ratio,.85)
		var transfer := _checker_transfer(witness_hidden,witness,couch_mask,aperture)
		_gate("checker_"+power+"_transfer",transfer.transfer>=.80,transfer,.80)
		var diffuse := StandardMaterial3D.new()
		diffuse.albedo_color = Color.WHITE
		diffuse.roughness = 1.0
		couch.material_override = diffuse
		pillow.material_override = diffuse
		await _capture("white-fabric-"+power+"-pane-hidden")
		var lid: MeshInstance3D = ship.pods_node.get_node("Pod0/PodShell/PodLid")
		lid.visible = false
		await _capture("white-fabric-"+power+"-lid-hidden")
		lid.visible = true
		couch.material_override = null
		pillow.material_override = null
		_set_panes(true)
	var a := Vector3(-3.4,0,Pods.ROW_A_Z)
	_pose(a+Vector3(.9,1.7,2.0),a+Vector3(0,1.0,-.4))
	await _capture("open-foot-three-quarter")
	_pose(a+Vector3(.55,.72,-1.30),a+PodGeometry.LID_PIVOT)
	await _capture("open-head-hinge-contact")
	for entry: Array in [["row-a",Vector3(-4.8,0,Pods.ROW_A_Z)],["row-b",Vector3(-2.0,0,Pods.ROW_B_Z)]]:
		for side: float in [-1.0,1.0]:
			_pose(entry[1]+Vector3(side*.7,.48,.05),entry[1]+Vector3(0,.28,0))
			await _capture("flank-%s-%s"%[entry[0],"left" if side<0 else "right"])
	preload("res://tools/pod_diagnostic_export.gd").save_scene(meshes,output.path_join("scene-geometry.json"))
	await _mirrored_flanks()
	results.metadata = {"engine":Engine.get_version_info(),"renderer":RenderingServer.get_current_rendering_method(),"device":RenderingServer.get_video_adapter_name(),"exposure":2.0,"size":[1152,648],"smoke_seed":88,"sparks":false,"shader_time_frozen":true,"asset_sha256":FileAccess.get_sha256(PodMesh.POD_PATH),"shader_sha256":FileAccess.get_sha256("res://app/pod_glass.gdshader"),"failures":failures}
	FileAccess.open(output.path_join("measurements.json"),FileAccess.WRITE).store_string(JSON.stringify(results,"\t"))
	print("PRODUCTION CAPTURES ",results)
	stage.free()
	quit(0 if failures.is_empty() else 1)

func _pose(eye: Vector3, target: Vector3) -> void:
	var frame := game.layout.bay_to_world()
	camera.position = frame*eye
	camera.look_at(frame*target)
	camera.force_update_transform()

func _mirrored_flanks() -> void:
	results.mirror_setup = {"pod":0,"camera_distance":.9,"camera_height":.6,"target_height":.28,"lights_x":[-1.4,1.4],"lights_height":1.4,"light_energy":Lighting.regular_energy()*.08,"light_range":3.0,"room_and_status_lights":false,"smoke":false}
	var pod: Node3D = ship.pods_node.get_node("Pod0")
	for mesh: MeshInstance3D in meshes:
		mesh.visible = pod.is_ancestor_of(mesh)
	ship.hazards._smoke_field.visible = false
	for light: Node in stage.find_children("*","Light3D",true,false):
		light.visible = false
	for side: float in [-1.0,1.0]:
		var light := OmniLight3D.new()
		light.light_color = Lighting.REGULAR_WHITE
		light.light_energy = Lighting.regular_energy() * .08
		light.omni_range = 3.0
		pod.add_child(light)
		light.position = Vector3(side*1.4,1.4,0)
	for side: float in [-1.0,1.0]:
		camera.global_position = pod.global_transform * Vector3(side*.9,.6,0)
		camera.look_at(pod.global_transform * Vector3(0,.28,0))
		camera.force_update_transform()
		await _capture("flank-mirror-"+("left" if side<0 else "right"))
	preload("res://tools/pod_diagnostic_export.gd").save_scene(meshes,output.path_join("mirror-geometry.json"))

func _settle(frames: int) -> void:
	for i: int in range(frames):
		await process_frame
		RenderingServer.call_deferred("force_draw", false)
		await RenderingServer.frame_post_draw

func _capture(label: String) -> Image:
	await _settle(4)
	var image := root.get_texture().get_image()
	image.save_png(output.path_join(label+".png"))
	if label == "sealed-close-red":
		await _capture_red_linear()
	if not results.has("views"):
		results.views = {}
	var frame := camera.global_transform
	results.views[label] = {"eye":[frame.origin.x,frame.origin.y,frame.origin.z],"basis":[frame.basis.x.x,frame.basis.x.y,frame.basis.x.z,frame.basis.y.x,frame.basis.y.y,frame.basis.y.z,frame.basis.z.x,frame.basis.z.y,frame.basis.z.z],"fov":camera.fov,"near":camera.near,"far":camera.far}
	return image

func _capture_red_linear() -> void:
	# Eight-bit PNG rounds near-white highlights to 255. Measure linear half-floats too.
	root.use_hdr_2d = true
	await _settle(8)
	sealed_red_linear = root.get_texture().get_image()
	assert(sealed_red_linear.get_format() == Image.FORMAT_RGBH, "clipping requires a linear half-float target")
	sealed_red_linear.save_exr(output.path_join("sealed-close-red.exr"))
	root.use_hdr_2d = false
	await _settle(8)

static func _red_clipping(linear: Image,present: Image,mask: Image,aperture: Image) -> Dictionary:
	var count := 0
	var clipped := 0
	var png_saturated := 0
	for y: int in range(2,linear.get_height()-2):
		for x: int in range(2,linear.get_width()-2):
			if mask.get_pixel(x,y).r<.95 or not _inside_aperture(aperture,x,y):
				continue
			count += 1
			clipped += int(linear.get_pixel(x,y).r>=1.0)
			png_saturated += int(present.get_pixel(x,y).r>=1.0)
	return {"pixels":count,"clipped_pixels":clipped,"clipped_fraction":float(clipped)/maxi(count,1),"png_saturated_pixels":png_saturated,"png_saturated_fraction":float(png_saturated)/maxi(count,1)}

func _set_panes(visible: bool) -> void:
	for pane: MeshInstance3D in panes:
		pane.visible = visible

func _mask(selected: MeshInstance3D,label: String) -> Image:
	var old: Array[Material] = []
	var black := StandardMaterial3D.new()
	black.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	black.albedo_color = Color.BLACK
	var white := StandardMaterial3D.new()
	white.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	white.albedo_color = Color.WHITE
	for mesh: MeshInstance3D in meshes:
		old.append(mesh.material_override)
		mesh.material_override = white if mesh==selected else black
	# Keep the settled probe, lights and smoke state unchanged. ID materials
	# are diagnostic only and never mutate the shared production resources.
	# ID passes omit alpha smoke only to identify geometry, not to measure appearance.
	var smoke_visible := ship.hazards._smoke_field.visible
	ship.hazards._smoke_field.visible = false
	var image := await _capture(label)
	ship.hazards._smoke_field.visible = smoke_visible
	for i: int in range(meshes.size()):
		meshes[i].material_override = old[i]
	return image

func _checker_transfer(reference: Image,candidate: Image,mask: Image,aperture: Image) -> Dictionary:
	var low := Vector2.ZERO
	var high := Vector2.ZERO
	var nl := 0
	var nh := 0
	var samples: Array[Vector2] = []
	var minimum := INF
	var maximum := -INF
	for y: int in range(5,643):
		for x: int in range(5,1147):
			if mask.get_pixel(x,y).r<.95 or not _inside_aperture(aperture,x,y):
				continue
			var r := _channel(reference,x,y,false)
			if absf(r-_channel(reference,x+2,y,false))>.005 or absf(r-_channel(reference,x,y+2,false))>.005:
				continue
			samples.append(Vector2(r,_channel(candidate,x,y,false)))
			minimum=minf(minimum,r)
			maximum=maxf(maximum,r)
	assert(not samples.is_empty() and maximum-minimum>.01,"checker reference must resolve two levels")
	# Classify the reference's two measured levels, not an assumed exposure.
	var split := (minimum+maximum)*.5
	for pair: Vector2 in samples:
		if pair.x>split:
			high+=pair
			nh+=1
		else:
			low+=pair
			nl+=1
	assert(nh>0 and nl>0,"checker reference requires both cell classes")
	var modulation := high/nh-low/nl
	assert(modulation.x>.01,"checker reference modulation must be measurable")
	return {"transfer":modulation.y/modulation.x,"reference":modulation.x,"glass":modulation.y,"pixels":nh+nl,"split":split,"bright_pixels":nh,"dark_pixels":nl}

func _channel(image: Image,x: int,y: int,red: bool) -> float:
	var color := image.get_pixel(x,y).srgb_to_linear()
	return color.r if red else color.r*.2126+color.g*.7152+color.b*.0722

func _interior(reference: Image,candidate: Image,mask: Image,red: bool) -> Dictionary:
	var ratios: Array[float] = []
	var count := 0
	var sum_reference := 0.0
	var sum_candidate := 0.0
	var black := 0
	for y: int in range(5,643):
		for x: int in range(5,1147):
			if mask.get_pixel(x,y).r<.95 or mask.get_pixel(x-5,y).r<.95 or mask.get_pixel(x+5,y).r<.95 or mask.get_pixel(x,y-5).r<.95 or mask.get_pixel(x,y+5).r<.95:
				continue
			var before := _channel(reference,x,y,red)
			var after := _channel(candidate,x,y,red)
			count += 1
			sum_reference += before
			sum_candidate += after
			if before>.02:
				ratios.append(after/before)
				if after<.02:
					black += 1
	ratios.sort()
	return {"pixels":count,"reference_mean":sum_reference/maxf(count,1),"glass_mean":sum_candidate/maxf(count,1),"median_ratio":ratios[ratios.size()/2] if not ratios.is_empty() else 0.0,"black_fraction":float(black)/maxf(ratios.size(),1)}

func _boundary(reference: Image,candidate: Image,mask: Image,aperture: Image,red: bool) -> Dictionary:
	var count := 0
	var before := 0.0
	var after := 0.0
	for y: int in range(7,641):
		for x: int in range(7,1145):
			if mask.get_pixel(x,y).r<.95 or not _inside_aperture(aperture,x,y):
				continue
			for delta: Vector2i in [Vector2i(5,0),Vector2i(-5,0),Vector2i(0,5),Vector2i(0,-5)]:
				var next := Vector2i(x,y)+delta
				if mask.get_pixelv(next).r>.05 or not _inside_aperture(aperture,next.x,next.y):
					continue
				before += absf(_channel(reference,x,y,red)-_channel(reference,next.x,next.y,red))
				after += absf(_channel(candidate,x,y,red)-_channel(candidate,next.x,next.y,red))
				count += 1
	return {"pairs":count,"reference":before/maxf(count,1),"glass":after/maxf(count,1)}

static func _inside_aperture(mask: Image,x: int,y: int) -> bool:
	for delta: Vector2i in [Vector2i.ZERO,Vector2i(2,0),Vector2i(-2,0),Vector2i(0,2),Vector2i(0,-2)]:
		if mask.get_pixel(x+delta.x,y+delta.y).r<.95:
			return false
	return true

func _gate(label: String,passed: bool,value: Variant,threshold: Variant) -> void:
	results[label] = {"pass":passed,"measured":value,"threshold":threshold}
	if not passed:
		failures.append(label)
