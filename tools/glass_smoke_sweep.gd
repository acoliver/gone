extends "res://tools/glass_validation.gd"
## Reproject the same broad-face centroids through a fixed-time production field.
func _run() -> void:
	var region_path:=""
	var arguments:=OS.get_cmdline_user_args()
	for i: int in range(arguments.size()-1):
		if arguments[i]=="--regions":
			region_path=arguments[i+1]
	assert(not region_path.is_empty(),"--regions must name verified pane triangle regions")
	var regions: Array=JSON.parse_string(FileAccess.get_file_as_string(region_path))
	root.size=Vector2i(1152,648)
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	var game:=Game.new(0)
	stage=Node3D.new()
	root.add_child(stage)
	var ship:=ShipScene.build_into(stage,game)
	ship.hazards.auto_bursts=false
	ship.hazards.set_physics_process(false)
	ship.hazards._smoke_field.use_fixed_seed=true
	ship.hazards._smoke_field.seed=88
	camera=Camera3D.new()
	camera.fov=70
	camera.near=.02
	stage.add_child(camera)
	var bay_frame:=game.layout.bay_to_world()
	camera.position=bay_frame*Vector3(5.2,2.2,3.2)
	camera.look_at(bay_frame*Vector3(-2.8,.95,0))
	ship.hazards._smoke_field.restart()
	for i: int in range(30):
		await process_frame
		await RenderingServer.frame_post_draw
	ship.hazards._smoke_field.speed_scale=0
	var smoke_enabled:=OS.get_environment("GONE_SMOKE_CONTROL")!="off"
	ship.hazards._smoke_field.visible=smoke_enabled
	Engine.time_scale=0
	var meshes: Array[MeshInstance3D]=[]
	for node: MeshInstance3D in stage.find_children("*","MeshInstance3D",true,false):
		meshes.append(node)
	var black:=StandardMaterial3D.new()
	black.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
	black.albedo_color=Color.BLACK
	var white:=StandardMaterial3D.new()
	white.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
	white.albedo_color=Color.WHITE
	white.cull_mode=BaseMaterial3D.CULL_DISABLED
	var selected: Dictionary[int,bool]={}
	for pod: Pods.Pod in game.registry.pods():
		if selected.has(pod.state()):
			continue
		selected[pod.state()]=true
		pane=ship.pods_node.get_node("Pod%d/PodShell/PodLid/WindowPane"%pod.id().index())
		var arrays:=pane.mesh.surface_get_arrays(0)
		var vertices: PackedVector3Array=arrays[Mesh.ARRAY_VERTEX]
		var normals: PackedVector3Array=arrays[Mesh.ARRAY_NORMAL]
		var indices: PackedInt32Array=arrays[Mesh.ARRAY_INDEX]
		assert(regions.size()==indices.size()/3,"source regions must match the prepared pane")
		var points: Array[Vector3]=[]
		var ns: Array[Vector3]=[]
		for i: int in range(0,indices.size(),3):
			if int(regions[i/3])!=0:
				continue
			points.append(pane.global_transform*((vertices[indices[i]]+vertices[indices[i+1]]+vertices[indices[i+2]])/3))
			ns.append((pane.global_basis*(normals[indices[i]]+normals[indices[i+1]]+normals[indices[i+2]])).normalized())
		var center:=pane.global_transform*Vector3(0,.8959952-.437,1.17250931263)
		var frame:=game.layout.bay_to_world()
		var previous: Dictionary={}
		var valid:=0
		var jumps:=0
		var worst:=0.0
		var smoke_pixels:=0
		var steps: Array=[]
		for angle: int in range(0,92,2):
			var radians:=deg_to_rad(angle)
			# A continuous low-inside to high-outside arc, relative to this lid.
			camera.position=center+frame.basis*Vector3(.8*sin(radians),-.55*cos(radians)+.8*sin(radians),.35*cos(radians))
			camera.look_at(center,frame.basis*Vector3.FORWARD)
			var label:="state%d-%02d"%[pod.state(),angle]
			pane.visible=true
			var candidate:=await _capture(label+"-glass")
			pane.visible=false
			var hidden:=await _capture(label+"-hidden")
			ship.hazards._smoke_field.visible=false
			var clear_hidden:=await _capture(label+"-clear-hidden")
			pane.visible=true
			var clear_glass:=await _capture(label+"-clear-glass")
			var saved: Array[Material]=[]
			for mesh: MeshInstance3D in meshes:
				saved.append(mesh.material_override)
				mesh.material_override=white if mesh==pane else black
			ship.hazards._smoke_field.visible=false
			var mask:=await _capture(label+"-mask")
			ship.hazards._smoke_field.visible=smoke_enabled
			for i: int in range(meshes.size()):
				meshes[i].material_override=saved[i]
			var current: Dictionary={}
			var step_valid:=0
			var step_jumps:=0
			for i: int in range(points.size()):
				if camera.is_position_behind(points[i]):
					continue
				var pixel:=Vector2i(camera.unproject_position(points[i]))
				if pixel.x<5 or pixel.x>=1147 or pixel.y<5 or pixel.y>=643:
					continue
				if not _inside(mask,pixel):
					continue
				var ndv:=absf(ns[i].dot((camera.position-points[i]).normalized()))
				if ndv<.174:
					continue
				smoke_pixels+=int(absf(_linear(hidden,pixel.x,pixel.y)-_linear(clear_hidden,pixel.x,pixel.y))>.003)
				var transfer:=.98*(1-(.04+.96*pow(1-ndv,5)))
				# Remove the same view's smoke-free reflection and lighting change.
				# A pane-hidden sequence alone still contains moving fixture highlights.
				var delta:=(candidate.get_pixelv(pixel).srgb_to_linear()-clear_glass.get_pixelv(pixel).srgb_to_linear())-(hidden.get_pixelv(pixel).srgb_to_linear()-clear_hidden.get_pixelv(pixel).srgb_to_linear())*transfer
				current[i]=Vector3(delta.r,delta.g,delta.b)
				if previous.has(i):
					var change: Vector3=(current[i]-previous[i]).abs()
					var error:=maxf(change.x,maxf(change.y,change.z))
					worst=maxf(worst,error)
					step_valid+=1
					step_jumps+=int(error>.08)
			valid+=step_valid
			jumps+=step_jumps
			steps.append({"angle":angle,"valid":step_valid,"jumps":step_jumps})
			previous=current
		var fraction:=float(jumps)/maxf(valid,1)
		results["state%d_steps"%pod.state()]=steps
		_gate("state%d_smoke_coverage"%pod.state(),smoke_pixels>=1000,smoke_pixels,1000)
		var peak_fraction:=0.0
		for step: Dictionary in steps:
			if int(step.valid)>0:
				peak_fraction=maxf(peak_fraction,float(step.jumps)/float(step.valid))
		_gate("state%d_jumps"%pod.state(),valid>1000 and peak_fraction<.01,{"valid":valid,"jumps":jumps,"fraction":fraction,"peak_step_fraction":peak_fraction,"max":worst},.01)
	results.metadata={"particles":ship.hazards._smoke_field.amount,"seed":88,"fixed_time":true,"failures":failures}
	FileAccess.open(output.path_join("measurements.json"),FileAccess.WRITE).store_string(JSON.stringify(results,"\t"))
	print("SMOKE SWEEP ",failures)
	quit(0 if failures.is_empty() else 1)

func _inside(mask: Image,pixel: Vector2i) -> bool:
	for d: Vector2i in [Vector2i.ZERO,Vector2i(5,0),Vector2i(-5,0),Vector2i(0,5),Vector2i(0,-5)]:
		if mask.get_pixelv(pixel+d).r<.95:
			return false
	return true
