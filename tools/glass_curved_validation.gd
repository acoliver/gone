extends "res://tools/glass_validation.gd"
## Render the prepared production sheet, including its frame, from both sides.
var shells: Array[Node3D] = []

func _run() -> void:
	root.size = Vector2i(1152,648)
	RenderingServer.set_default_clear_color(Color.BLACK)
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	stage = Node3D.new()
	root.add_child(stage)
	world = Lighting._world_environment()
	stage.add_child(world)
	camera = Camera3D.new()
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = .65
	camera.near = .01
	stage.add_child(camera)
	for i: int in range(7):
		var shell := PodMesh.make_shell(Pods.PodState.SEALED)
		shell.position.x = (i-3)*2.0
		stage.add_child(shell)
		shells.append(shell)
	pane = shells[3].get_node("PodLid/WindowPane")
	checker = MeshInstance3D.new()
	var quad := QuadMesh.new()
	quad.size = Vector2(1.0,1.0)
	checker.mesh = quad
	var witness := ShaderMaterial.new()
	var shader := Shader.new()
	shader.code = "shader_type spatial; render_mode unshaded,cull_disabled; void fragment(){float c=mod(floor(UV.x*24.0)+floor(UV.y*24.0),2.0); ALBEDO=vec3(mix(.025,.175,c));}"
	witness.shader = shader
	checker.material_override = witness
	stage.add_child(checker)
	for entry: Array in [["sealed",0.0],["empty_open",PodGeometry.lid_angle(Pods.PodState.EMPTY_OPEN)],["player",PodGeometry.lid_angle(Pods.PodState.PLAYER)],["diagnostic70",-deg_to_rad(70)],["diagnostic78",-deg_to_rad(78)]]:
		for shell: Node3D in shells:
			shell.get_node("PodLid").rotation.x = entry[1]
		await _frames(3)
		var center := pane.global_transform*Vector3(0,.8959952-.437,1.17250931263)
		var normal := pane.global_basis*Vector3.UP
		var tangent := pane.global_basis*Vector3.FORWARD
		for side: float in [1.0,-1.0]:
			var label := "%s-%s"%[entry[0],"outside" if side>0 else "inside"]
			camera.position = center+normal*side*.5
			camera.look_at(center,tangent)
			checker.global_transform = Transform3D(Basis(pane.global_basis.x,tangent,normal),center-normal*side*.15)
			pane.visible = false
			var reference := await _capture(label+"-hidden")
			pane.visible = true
			var candidate := await _capture(label+"-glass")
			var stats := _checker_stats(reference,candidate)
			results[label] = stats
			_gate(label+"_transfer",stats.transfer>=.88 and stats.transfer<=1.03,stats.transfer,[.88,1.03])
			_gate(label+"_tenth",stats.p10>=.82,stats.p10,.82)
			_gate(label+"_correlation",stats.correlation>=.98,stats.correlation,.98)
			_gate(label+"_pixels",stats.pixels>=1000,stats.pixels,1000)
	results.metadata = {"engine":Engine.get_version_info(),"seven_instances":shells.size(),"production_open_degrees":rad_to_deg(PodGeometry.LID_OPEN_TILT),"failures":failures}
	FileAccess.open(output.path_join("measurements.json"),FileAccess.WRITE).store_string(JSON.stringify(results,"\t"))
	print("CURVED ",failures)
	quit(0 if failures.is_empty() else 1)

func _frames(count: int) -> void:
	for i: int in range(count):
		await process_frame
		await RenderingServer.frame_post_draw

func _checker_stats(reference: Image,candidate: Image) -> Dictionary:
	var ratios: Array[float] = []
	var high: Array[float] = []
	var low: Array[float] = []
	var rh: Array[float] = []
	var rl: Array[float] = []
	var pairs: Array[Vector2] = []
	for y: int in range(224,424):
		for x: int in range(476,676):
			var r := _linear(reference,x,y)
			if r<.02 or absf(r-_linear(reference,x+2,y))>.003 or absf(r-_linear(reference,x-2,y))>.003 or absf(r-_linear(reference,x,y+2))>.003 or absf(r-_linear(reference,x,y-2))>.003:
				continue
			var c := _linear(candidate,x,y)
			ratios.append(c/r)
			pairs.append(Vector2(r,c))
			if r>.15:
				high.append(c)
				rh.append(r)
			else:
				low.append(c)
				rl.append(r)
	ratios.sort()
	var mx := 0.0
	var my := 0.0
	for p: Vector2 in pairs:
		mx+=p.x/maxf(pairs.size(),1)
		my+=p.y/maxf(pairs.size(),1)
	var cov := 0.0
	var vx := 0.0
	var vy := 0.0
	for p: Vector2 in pairs:
		cov+=(p.x-mx)*(p.y-my)
		vx+=pow(p.x-mx,2)
		vy+=pow(p.y-my,2)
	return {"transfer":(_mean(high)-_mean(low))/maxf(_mean(rh)-_mean(rl),1e-9),"p10":ratios[ratios.size()/10] if not ratios.is_empty() else 0,"median":ratios[ratios.size()/2] if not ratios.is_empty() else 0,"correlation":cov/maxf(sqrt(vx*vy),1e-9),"pixels":ratios.size()}
