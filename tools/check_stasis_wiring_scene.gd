extends SceneTree
## Native-backend construction check, without launching main or changing gameplay.

func _initialize() -> void:
	_run.call_deferred()

func _run() -> void:
	assert(DisplayServer.get_name()!="headless", "native renderer required for production MultiMesh readback")
	var game := Game.new(0)
	var collider_count := game.colliders.size()
	var parent := Node3D.new()
	root.add_child(parent)
	var scene := ShipScene.build_into(parent,game)
	var installed := scene.bay_root.get_node("StasisWiringInstallation") as Node3D
	assert(installed!=null and installed.get_child_count()==2,"ShipScene installs the network exactly once")
	assert(scene.bay_root.find_children("StasisWiringInstallation","Node3D",true,false).size()==1,"one network under the bay frame")
	assert(scene.bay_root.transform==game.layout.bay_to_world(),"bay-local installation follows the ship transform")
	assert(game.colliders.size()==collider_count,"no player collision changes")
	assert(scene.pods_node.get_child_count()==7,"seven registry pods remain in place")
	assert(BayCeiling.EMPTY_CELLS==[Vector2i(4,4)],"no additional ceiling openings")
	assert((scene.rod.get_node("RodBar") as Node3D).transform==SeatRailComponent.floor_pose(),"passed 115 degree pickup pose is unchanged")
	var errors := StasisWiringRoutes.validate(StasisWiringRoutes.graph())
	assert(errors.is_empty(),"production route graph: "+str(errors))
	var meshes := installed.get_child(0).find_children("*","MeshInstance3D",true,false)
	var bounds := AABB()
	for i in range(meshes.size()):
		var mesh := meshes[i] as MeshInstance3D
		var box := installed.global_transform.affine_inverse()*mesh.global_transform*mesh.mesh.get_aabb()
		bounds = box if i==0 else bounds.merge(box)
		assert(mesh.layers==(1|Lighting.BAY_FILL_MASK),"installation uses normal bay lighting layers")
	assert(meshes.size()==8,"eight material groups include released-core insulation, no duplicate dressing")
	assert(scene.bay_root.find_children("HangingWires","Node3D",true,false).is_empty(),"obsolete loose-run dressing is absent")
	var fault: Dictionary = StasisWiringRoutes.graph().fault
	var sparks := scene.bay_root.find_children("SparkSpot*","Node3D",true,false)
	assert(sparks.size()==3,"exactly three production spark emitters")
	for index in range(3):
		assert((sparks[index] as Node3D).position.is_equal_approx(fault.power_tip_positions[index]),"spark emitter matches actual copper tip")
	assert(bounds.position.y>-.8 and bounds.end.y<3.10,"native GLB import has expected +Y-up bounds")
	assert(bounds.position.x>-5.88 and bounds.end.x<.40,"network uses measured production route bounds")
	var camera := Camera3D.new()
	parent.add_child(camera)
	camera.global_position = game.layout.bay_to_world()*Vector3(1.5,1.7,1.0)
	camera.look_at(game.layout.bay_to_world()*Vector3(-3.5,2.5,-3.0))
	camera.current = true
	for i in range(3): await process_frame
	RenderingServer.call_deferred("force_draw",false)
	await RenderingServer.frame_post_draw
	print("PRODUCTION_WIRING_SCENE_PASS meshes=%d pods=7 colliders=%d graph_errors=0 bounds=%s" % [meshes.size(),collider_count,str(bounds)])
	# Detach light/particle render work before the test scene is destroyed.
	for light: Light3D in parent.find_children("*","Light3D",true,false): light.hide()
	for particles: GPUParticles3D in parent.find_children("*","GPUParticles3D",true,false): particles.emitting = false
	for i in range(3): await process_frame
	RenderingServer.call_deferred("force_draw",false)
	await RenderingServer.frame_post_draw
	quit(0)
