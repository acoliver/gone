extends "res://tools/glass_validation.gd"
## Independent alpha witnesses use the actual puff shader and fixed phase/time.
var puff: MultiMeshInstance3D
var puff_material: ShaderMaterial
var background_material: StandardMaterial3D

func _run() -> void:
	root.size=Vector2i(1152,648)
	RenderingServer.set_default_clear_color(Color.BLACK)
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	stage=Node3D.new()
	root.add_child(stage)
	world=Lighting._world_environment()
	stage.add_child(world)
	camera=Camera3D.new()
	camera.projection=Camera3D.PROJECTION_ORTHOGONAL
	camera.size=2
	stage.add_child(camera)
	pane=MeshInstance3D.new()
	pane.mesh=_coupon()
	pane.material_override=PodMesh.canopy_material()
	pane.sorting_use_aabb_center=true
	stage.add_child(pane)
	checker=MeshInstance3D.new()
	var q:=QuadMesh.new()
	q.size=Vector2(20,20)
	checker.mesh=q
	background_material=StandardMaterial3D.new()
	background_material.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
	background_material.cull_mode=BaseMaterial3D.CULL_DISABLED
	checker.material_override=background_material
	stage.add_child(checker)
	puff=MultiMeshInstance3D.new()
	var multi:=MultiMesh.new()
	multi.transform_format=MultiMesh.TRANSFORM_3D
	multi.use_custom_data=true
	var quad:=QuadMesh.new()
	quad.size=Vector2(1.6,1.6)
	multi.mesh=quad
	multi.instance_count=1
	multi.set_instance_transform(0,Transform3D.IDENTITY)
	multi.set_instance_custom_data(0,Color(0,.5,0,0))
	puff.multimesh=multi
	puff_material=ShaderMaterial.new()
	puff_material.shader=load("res://app/smoke_puff.gdshader")
	puff_material.set_shader_parameter("tint",Color.BLACK)
	puff_material.set_shader_parameter("emission_tint",Color(.75,.75,.75))
	puff_material.set_shader_parameter("opacity",.48)
	puff.material_override=puff_material
	stage.add_child(puff)
	Engine.time_scale=0
	for lid: float in [0.0,absf(rad_to_deg(PodGeometry.lid_angle(Pods.PodState.EMPTY_OPEN))),70.0,78.0]:
		var rotation:=Basis(Vector3.RIGHT,-deg_to_rad(lid))
		pane.basis=rotation
		for side: float in [1.0,-1.0]:
			var direction:=rotation*Vector3(sin(deg_to_rad(80)),0,side*cos(deg_to_rad(80)))
			camera.position=direction*10
			camera.look_at(Vector3.ZERO,rotation*Vector3.UP)
			checker.position=-direction*10
			checker.look_at(camera.position,rotation*Vector3.UP)
			for kind: String in ["behind","front","frame","crossing"]:
				var label:="%d-%s-%s"%[lid,"outside" if side>0 else "inside",kind]
				var behind:=kind!="front"
				# At 80 degrees a nearby billboard crosses the sheet, even when
				# its center is in front. This separation clears its entire 1.6 m quad.
				puff.position=direction*(-6.0 if behind else 6.0)
				if kind=="crossing":
					puff.position+=camera.basis.x*.33
				var frame: MeshInstance3D
				if kind=="frame":
					frame=MeshInstance3D.new()
					var box:=BoxMesh.new()
					box.size=Vector3(.12,.7,.05)
					frame.mesh=box
					frame.global_transform=Transform3D(camera.basis,direction*.1+camera.basis.x*.08)
					var black:=StandardMaterial3D.new()
					black.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
					black.albedo_color=Color.BLACK
					frame.material_override=black
					stage.add_child(frame)
				pane.visible=false
				puff.visible=false
				background_material.albedo_color=Color(.6,.6,.6)
				var b:=await _capture(label+"-background")
				pane.visible=true
				var g:=await _capture(label+"-glass-white")
				pane.visible=false
				puff.visible=true
				var sw:=await _capture(label+"-smoke-white")
				background_material.albedo_color=Color.BLACK
				var s:=await _capture(label+"-smoke-black")
				pane.visible=true
				var actual:=await _capture(label+"-composite")
				var stats:=_composition(b,g,s,sw,actual,behind)
				results[label]=stats
				_gate(label+"_mean",stats.mean<=.02,stats.mean,.02)
				_gate(label+"_p99",stats.p99<=.06,stats.p99,.06)
				_gate(label+"_bad",stats.bad_fraction<.01,stats.bad_fraction,.01)
				_gate(label+"_coverage",stats.pixels>=1000,stats.pixels,1000)
				puff_material.render_priority=127 if behind else -127
				var reversed:=_composition(b,g,s,sw,await _capture(label+"-reversed"),behind)
				if behind:
					_gate(label+"_reversal_detected",reversed.mean>.02 or reversed.p99>.06 or reversed.bad_fraction>=.01,reversed,"must fail E")
				puff_material.render_priority=0
				if frame!=null:
					frame.free()
	results.metadata={"shader":"res://app/smoke_puff.gdshader","fixed_phase":.5,"time_frozen":true,"incidence":80,"failures":failures}
	FileAccess.open(output.path_join("measurements.json"),FileAccess.WRITE).store_string(JSON.stringify(results,"\t"))
	print("SMOKE ",failures)
	quit(0 if failures.is_empty() else 1)

func _composition(b: Image,g: Image,s: Image,sw: Image,actual: Image,behind: bool) -> Dictionary:
	var errors: Array[float]=[]
	var bad:=0
	var sum:=0.0
	for y: int in range(200,448):
		for x: int in range(540,612):
			var bg:=_linear(b,x,y)
			if bg<.1:
				continue
			# Ignore opaque-frame boundaries by checking the independent white pass.
			if _linear(b,x-5,y)<.1 or _linear(b,x+5,y)<.1 or _linear(b,x,y-5)<.1 or _linear(b,x,y+5)<.1:
				continue
			var smoke:=_linear(s,x,y)
			var alpha:=1-(_linear(sw,x,y)-smoke)/bg
			if alpha<.05:
				continue
			var transfer:=_linear(g,x,y)/bg
			var expected:=smoke*transfer if behind else smoke
			var error:=absf(_linear(actual,x,y)-expected)
			errors.append(error)
			sum+=error
			bad+=int(error>.08)
	errors.sort()
	return {"pixels":errors.size(),"mean":sum/maxf(errors.size(),1),"p99":errors[mini(errors.size()-1,int(errors.size()*.99))] if not errors.is_empty() else 1,"bad_fraction":float(bad)/maxf(errors.size(),1)}
