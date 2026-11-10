extends SceneTree
## Isolated native-material inspection captures, never normal game startup.

const Presenter = preload("res://app/stasis_wiring.gd")
const Rail = preload("res://app/seat_rail_component.gd")
const OUT := "res://tmp/verify-stasis-wiring/seat-rail/readability/"
var views: Array[Dictionary] = []

func _init() -> void:
	_run.call_deferred()

func _v(p: Vector3) -> Array:
	return [p.x,p.y,p.z]

func _meshes(node: Node, result: Array[MeshInstance3D]) -> void:
	if node is MeshInstance3D: result.append(node)
	for child: Node in node.get_children(): _meshes(child,result)

func _part(world: Node3D, part: StringName, label: String, pose := Transform3D.IDENTITY) -> Node3D:
	var source := Rail.build(part)
	source.name = label
	source.transform = pose
	world.add_child(source)
	return source

func _world(mode: String) -> Node3D:
	var world := Node3D.new()
	world.name = "Inspection"
	root.add_child(world)
	if mode.begins_with("native"):
		world.add_child(Presenter.build(&"fault-frame-pair"))
	elif mode == "full":
		_part(world,&"full","Full")
	elif mode == "gap":
		_part(world,&"left","Left")
		_part(world,&"right","Right")
	elif mode == "fallen":
		var pose := Rail.floor_pose()
		pose.origin.x = 0
		pose.origin.z = 0
		_part(world,&"middle","Middle",pose)
	elif mode == "left_mate":
		_part(world,&"left","Left")
		_part(world,&"middle","Middle",Transform3D(Basis.IDENTITY,Vector3(0.012,0,0)))
	elif mode == "right_mate":
		_part(world,&"right","Right")
		_part(world,&"middle","Middle",Transform3D(Basis.IDENTITY,Vector3(-0.012,0,0)))
	else:
		assert(mode == "profile")
		_part(world,&"middle","Middle")
	return world

func _lighting(world: Node3D, native: bool) -> Dictionary:
	var environment := WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.16,0.18,0.20)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.8,0.8,0.8)
	env.ambient_light_energy = 0.65
	env.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
	env.sky = Sky.new()
	var sky := ProceduralSkyMaterial.new()
	sky.sky_top_color = Color(0.55,0.58,0.62)
	sky.sky_horizon_color = Color(0.75,0.75,0.75)
	sky.ground_horizon_color = Color(0.75,0.75,0.75)
	sky.ground_bottom_color = Color(0.3,0.32,0.35)
	env.sky.sky_material = sky
	environment.environment = env
	world.add_child(environment)
	var center := Vector3(-0.6,1.6,-0.9) if native else Vector3.ZERO
	var offsets: Array = [Vector3(0.4,0.6,-1.8),Vector3(-1.8,-0.1,0.5),Vector3(0.8,1.9,0.4)] if native else [Vector3(-0.3,0.8,-0.9),Vector3(0.2,-0.6,0.7),Vector3(0.9,0.3,0.2)]
	var lights: Array[Dictionary] = []
	for i: int in range(3):
		var light := OmniLight3D.new()
		light.position = center+offsets[i]
		light.omni_range = 7.0 if native else 4.0
		light.light_energy = [4.0,3.0,3.0][i] if native else [2.0,1.8,1.0][i]
		light.light_color = Color.WHITE
		light.shadow_enabled = true
		world.add_child(light)
		lights.append({"position":_v(light.position),"energy":light.light_energy,"range_m":light.omni_range,"color":[1,1,1]})
	return {"ambient_energy":0.65,"neutral_sky_reflection":true,"lights":lights,"fixed_exposure":1.0,"native_materials":true}

func _colliders(world: Node3D, meshes: Array[MeshInstance3D]) -> void:
	for mesh: MeshInstance3D in meshes:
		if not mesh.is_visible_in_tree(): continue
		var body := StaticBody3D.new()
		body.set_meta("render_mesh",mesh)
		world.add_child(body)
		body.global_transform = mesh.global_transform
		var shape := CollisionShape3D.new()
		shape.shape = mesh.mesh.create_trimesh_shape()
		body.add_child(shape)

func _surface_point(point: Vector3, a: Vector3, b: Vector3, c: Vector3) -> Vector3:
	var ab := b-a
	var ac := c-a
	var normal := ab.cross(ac).normalized()
	var projected := point-normal*normal.dot(point-a)
	var relative := projected-a
	var d00 := ab.dot(ab)
	var d01 := ab.dot(ac)
	var d11 := ac.dot(ac)
	var denominator := d00*d11-d01*d01
	var v := (d11*relative.dot(ab)-d01*relative.dot(ac))/denominator
	var w := (d00*relative.dot(ac)-d01*relative.dot(ab))/denominator
	if v>=0 and w>=0 and v+w<=1: return projected
	var best := Geometry3D.get_closest_point_to_segment(point,a,b)
	for candidate: Vector3 in [Geometry3D.get_closest_point_to_segment(point,b,c),Geometry3D.get_closest_point_to_segment(point,c,a)]:
		if candidate.distance_squared_to(point)<best.distance_squared_to(point): best = candidate
	return best

func _anchor(camera: Camera3D, meshes: Array[MeshInstance3D], spec: Dictionary) -> Dictionary:
	var desired: Vector3 = spec.point
	var candidates: Array[Dictionary] = []
	for mesh: MeshInstance3D in meshes:
		if not String(mesh.get_path()).contains(spec.node): continue
		var faces := mesh.mesh.get_faces()
		for i: int in range(0,faces.size(),3):
			var a := mesh.global_transform*faces[i]
			var b := mesh.global_transform*faces[i+1]
			var c := mesh.global_transform*faces[i+2]
			var point := _surface_point(desired,a,b,c).lerp((a+b+c)/3.0,0.0001)
			var distance := point.distance_to(desired)
			if distance > spec.get("radius",0.12): continue
			candidates.append({"point":point,"distance":distance,"mesh":mesh,"triangle_index":i/3})
	candidates.sort_custom(func(a: Dictionary,b: Dictionary) -> bool: return a.distance < b.distance)
	for candidate: Dictionary in candidates:
		var point: Vector3 = candidate.point
		var pixel := camera.unproject_position(point)
		if camera.is_position_behind(point) or not Rect2(Vector2.ZERO,Vector2(root.size)).has_point(pixel): continue
		var query := PhysicsRayQueryParameters3D.create(camera.project_ray_origin(pixel),point+camera.project_ray_normal(pixel)*0.01)
		var hit := camera.get_world_3d().direct_space_state.intersect_ray(query)
		if hit.is_empty(): continue
		var hit_mesh: MeshInstance3D = hit.collider.get_meta("render_mesh")
		if hit_mesh != candidate.mesh or (hit.position as Vector3).distance_to(point)>0.001: continue
		return {"id":spec.id,"pixel":[pixel.x,pixel.y],"world_m":_v(point),"node_path":String(hit_mesh.get_path()),"object_instance_id":hit_mesh.get_instance_id(),"mesh_resource":hit_mesh.mesh.resource_path,"source":spec.source,"triangle_index":candidate.triangle_index,"ray_hit_node":String(hit_mesh.get_path()),"ray_hit_world_m":_v(hit.position),"visible":true}
	printerr("No visible source-triangle anchor: "+spec.id+" candidates="+str(candidates.size()))
	if not candidates.is_empty():
		printerr("closest candidate: ",candidates[0].point," pixel=",camera.unproject_position(candidates[0].point)," node=",candidates[0].mesh.get_path())
	quit(1)
	return {}

func _material_rows(meshes: Array[MeshInstance3D]) -> Array[Dictionary]:
	var result: Array[Dictionary] = []
	for mesh: MeshInstance3D in meshes:
		var mat := mesh.get_active_material(0)
		var row := {"node":String(mesh.get_path()),"material_class":mat.get_class(),"resource_name":mat.resource_name,"mesh":mesh.mesh.resource_path,"normal_count":(mesh.mesh.surface_get_arrays(0)[Mesh.ARRAY_NORMAL] as PackedVector3Array).size(),"vertex_count":(mesh.mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX] as PackedVector3Array).size()}
		if mat is StandardMaterial3D:
			var pbr := mat as StandardMaterial3D
			row.merge({"metallic":pbr.metallic,"roughness":pbr.roughness,"albedo_texture":pbr.albedo_texture.resource_path if pbr.albedo_texture else "","roughness_texture":pbr.roughness_texture.resource_path if pbr.roughness_texture else "","normal_enabled":pbr.normal_enabled,"normal_texture":pbr.normal_texture.resource_path if pbr.normal_texture else "","master_hardware_resource":mat==Presenter._hardware_material(),"shared_seat_resource":mat==Rail.material()})
		result.append(row)
	return result

func _capture(name: String, mode: String, eye: Vector3, target: Vector3, size: Vector2i, specs: Array[Dictionary], ortho: float = 0.0, fov: float = 65.0) -> void:
	root.size = size
	root.content_scale_mode = Window.CONTENT_SCALE_MODE_VIEWPORT
	root.content_scale_size = size
	DisplayServer.window_set_size(size)
	var world := _world(mode)
	var lighting := _lighting(world,mode.begins_with("native"))
	var camera := Camera3D.new()
	camera.near = 0.002
	camera.far = 20
	camera.keep_aspect = Camera3D.KEEP_WIDTH
	camera.fov = fov
	if ortho>0:
		camera.projection = Camera3D.PROJECTION_ORTHOGONAL
		camera.size = ortho
	world.add_child(camera)
	camera.position = eye
	camera.look_at(target)
	camera.current = true
	var meshes: Array[MeshInstance3D] = []
	_meshes(world,meshes)
	_colliders(world,meshes)
	await physics_frame
	await physics_frame
	for i: int in range(10): await process_frame
	RenderingServer.force_draw(false)
	await RenderingServer.frame_post_draw
	await process_frame
	RenderingServer.force_draw(false)
	await RenderingServer.frame_post_draw
	var image := root.get_texture().get_image()
	assert(image != null and image.get_size()==size)
	var anchors: Array[Dictionary] = []
	for spec: Dictionary in specs: anchors.append(_anchor(camera,meshes,spec))
	var row := {"name":name,"mode":mode,"eye_m":_v(eye),"target_m":_v(target),"size":[size.x,size.y],"fov_horizontal_degrees":fov,"orthographic_width_m":ortho,"pixels_per_metre":size.x/ortho if ortho>0 else null,"lighting":lighting,"anchors":anchors,"materials":_material_rows(meshes)}
	if mode=="gap":
		var original := Rail.build(&"middle")
		var source_meshes: Array[MeshInstance3D] = []
		_meshes(original,source_meshes)
		var projected := PackedVector2Array()
		for mesh: MeshInstance3D in source_meshes:
			for vertex: Vector3 in mesh.mesh.get_faces(): projected.append(camera.unproject_position(vertex))
		var hull := Geometry2D.convex_hull(projected)
		var outline: Array = []
		for pixel: Vector2 in hull: outline.append([pixel.x,pixel.y])
		row["removed_component_outline_pixels"] = outline
		row["outline_source"] = "Actual middle.glb projected in original installed source frame, not rendered replacement geometry."
		original.free()
	if mode=="native_standing":
		row["eye_height_m"] = eye.y
		row["pickup_center_bay_xz_m"] = [-0.6,-1.4]
		row["pickup_plan_distance_m"] = Vector2(eye.x+0.6,eye.z+1.4).length()
		row["interaction_reach_m"] = 1.3
	assert(image.save_png(OUT+name+".png")==OK)
	views.append(row)
	world.free()
	await process_frame

func _spec(id: String, point: Vector3, node: String, source: String, radius: float = 0.12) -> Dictionary:
	return {"id":id,"point":point,"node":node,"source":source,"radius":radius}

func _run() -> void:
	assert(DisplayServer.get_name()!="headless","native GPU inspection capture required")
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	root.msaa_3d = Viewport.MSAA_4X
	DirAccess.make_dir_recursive_absolute(OUT)
	var eye := Vector3(0.05,0.15,-0.8)
	var target := Vector3(0,-0.003,0)
	await _capture("raw-sheet-full","full",eye,target,Vector2i(1280,230),[_spec("ceiling seat rail",Vector3(0,-0.006,-0.021),"Full/","full.glb/seat_rail_full")],1.45)
	await _capture("raw-sheet-gap","gap",eye,target,Vector2i(1280,230),[_spec("left retained end",Vector3(-0.55,-0.006,-0.021),"Left/","left.glb/seat_rail_left"),_spec("right retained end",Vector3(0.55,-0.006,-0.021),"Right/","right.glb/seat_rail_right")],1.45)
	await _capture("raw-sheet-fallen","fallen",eye,target,Vector2i(1280,230),[_spec("same part detached",Vector3(0,0.02,0),"Middle/","middle.glb/seat_rail_middle")],1.45)
	await _capture("raw-installed-overview","native_overview",Vector3(1.9,1.65,1.7),Vector3(-0.6,1.6,-0.9),Vector2i(1280,480),[],0,100)
	await _capture("raw-installed-detail","native_detail",Vector3(-0.6,2.25,-0.5),Vector3(-0.6,3.02,-0.9),Vector2i(1280,570),[_spec("ceiling seat rail (intact)",Vector3(-0.6,2.979,-1.22),"seat_healthy","full.glb/seat_rail_full at (-0.6,2.988,-1.2)"),_spec("same source: left torn end",Vector3(-1.15,2.979,-.58),"SeatRail_left/","left.glb/seat_rail_left"),_spec("same source: right torn end",Vector3(-0.05,2.979,-.58),"SeatRail_right/","right.glb/seat_rail_right"),_spec("upper support (intact)",Vector3(-0.6,3.12,-.58),"steel_frame","BayCeiling carrier at y=3.12; separate from lower seat",0.07)],0,100)
	await _capture("raw-standing","native_standing",Vector3(-0.8,1.6,-2.65),Vector3(-0.6,0.02,-1.4),Vector2i(1280,900),[_spec("same part detached",Vector3(-0.6,0.025,-1.4),"fallen_fragment","middle.glb/seat_rail_middle; measured floor pose")],0,65)
	await _capture("raw-left-mate","left_mate",Vector3(-0.494,-0.065,-0.16),Vector3(-0.494,-0.008,0),Vector2i(420,420),[_spec("left retained",Vector3(-0.505,-0.008,-0.02),"Left/","left.glb/seat_rail_left"),_spec("middle left cut",Vector3(-0.483,-0.008,-0.02),"Middle/","middle.glb/seat_rail_middle; +12mm X inspection separation")],0.16)
	await _capture("raw-right-mate","right_mate",Vector3(0.494,-0.065,-0.16),Vector3(0.494,-0.008,0),Vector2i(420,420),[_spec("right retained",Vector3(0.505,-0.008,-0.02),"Right/","right.glb/seat_rail_right"),_spec("middle right cut",Vector3(0.483,-0.008,-0.02),"Middle/","middle.glb/seat_rail_middle; -12mm X inspection separation")],0.16)
	await _capture("raw-profile","profile",Vector3(-0.62,-0.045,-0.055),Vector3(-0.5,-0.009,0),Vector2i(420,420),[_spec("actual C profile / torn end",Vector3(-0.5,-0.009,0),"Middle/","middle.glb/seat_rail_middle")],0.085)
	var manifest := {"views":views,"renderer":RenderingServer.get_video_adapter_name(),"display":DisplayServer.get_name(),"source_profile":"36mm bearing / 42mm overall / 18mm deep / 2.5mm gauge; unmodified source meshes and PBR","floor_roll_degrees":115,"anchor_method":"Projected actual triangle surface points, camera ray first-hit checked against exact source mesh. Pixel coordinates are raw viewport coordinates.","review":"Parent image-comparer review pending; capture worker made no image judgments."}
	FileAccess.open(OUT+"capture-manifest.json",FileAccess.WRITE).store_string(JSON.stringify(manifest,"\t")+"\n")
	print("SEAT_RAIL_READABILITY_CAPTURE_PASS native materials, source-triangle anchors")
	quit(0)
