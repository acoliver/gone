extends "res://tools/glass_validation.gd"
## --regions is the source-region map written by verify_runtime.py.
var regions: Array
var source_mesh: ArrayMesh
var flat_mesh: ArrayMesh
var mask_mesh: ArrayMesh
var opaque_meshes: Array[MeshInstance3D] = []

func _run() -> void:
	var args:=OS.get_cmdline_user_args()
	var region_path:=""
	for i: int in range(args.size()-1):
		if args[i]=="--regions":
			region_path=args[i+1]
	assert(not region_path.is_empty(),"source face regions required")
	regions=JSON.parse_string(FileAccess.get_file_as_string(region_path))
	root.size=Vector2i(1152,648)
	RenderingServer.set_default_clear_color(Color.BLACK)
	stage=Node3D.new()
	root.add_child(stage)
	world=Lighting._world_environment()
	stage.add_child(world)
	var shell:=PodMesh.make_shell(Pods.PodState.SEALED)
	stage.add_child(shell)
	pane=shell.get_node("PodLid/WindowPane")
	for node: MeshInstance3D in shell.find_children("*","MeshInstance3D",true,false):
		if node!=pane:
			opaque_meshes.append(node)
	camera=Camera3D.new()
	camera.fov=70
	camera.near=.01
	stage.add_child(camera)
	source_mesh=pane.mesh
	flat_mesh=_variant(true,false)
	mask_mesh=_variant(false,true)
	var arrays:=source_mesh.surface_get_arrays(0)
	var vertices: PackedVector3Array=arrays[Mesh.ARRAY_VERTEX]
	var normals: PackedVector3Array=arrays[Mesh.ARRAY_NORMAL]
	var indices: PackedInt32Array=arrays[Mesh.ARRAY_INDEX]
	var mask_material:=ShaderMaterial.new()
	var mask_shader:=Shader.new()
	# A transparent broad face must not become an opaque ID-pass occluder.
	mask_shader.code="""shader_type spatial;
render_mode unshaded,cull_disabled;
uniform vec3 patch_center;
uniform vec3 card_center;
uniform vec3 card_normal;
uniform vec3 card_right;
uniform vec3 card_up;
varying vec3 local_point;
varying vec3 world_point;
void vertex(){local_point=VERTEX;world_point=(MODEL_MATRIX*vec4(VERTEX,1.0)).xyz;}
void fragment(){
    if(COLOR.r<0.5 || distance(local_point,patch_center)>0.3)discard;
    vec3 ray=normalize((INV_VIEW_MATRIX*vec4(reflect(-normalize(VIEW),normalize(NORMAL)),0.0)).xyz);
    float denominator=dot(ray,card_normal);
    if(abs(denominator)<0.00001)discard;
    float t=dot(card_center-world_point,card_normal)/denominator;
    vec3 hit=world_point+ray*t-card_center;
    if(t<=0.0 || abs(dot(hit,card_right))>1.0 || abs(dot(hit,card_up))>2.0)discard;
    ALBEDO=vec3(1.0);
}"""
	mask_material.shader=mask_shader
	for patch: String in ["flank","end"]:
		var selected:=-1
		var distance:=INF
		var target:=Vector3(.413, .535-.437,1.17250931263) if patch=="flank" else Vector3(0,.535-.437,2.29)
		for triangle: int in range(regions.size()):
			if int(regions[triangle])!=3:
				continue
			var center:=(vertices[indices[triangle*3]]+vertices[indices[triangle*3+1]]+vertices[indices[triangle*3+2]])/3
			if center.distance_to(target)<distance:
				distance=center.distance_to(target)
				selected=triangle
		var point:=Vector3.ZERO
		var normal:=Vector3.ZERO
		for j: int in range(3):
			point+=vertices[indices[selected*3+j]]/3
			normal+=normals[indices[selected*3+j]]
		mask_material.set_shader_parameter("patch_center",point)
		point=pane.global_transform*point
		normal=(pane.global_basis*normal).normalized()
		var view:=Vector3(-.5,.8660254,0) if patch=="flank" else Vector3(0,.8660254,-.5)
		camera.position=point+view*.5
		camera.look_at(point,Vector3.FORWARD if patch=="flank" else Vector3.RIGHT)
		card=MeshInstance3D.new()
		var quad:=QuadMesh.new()
		quad.size=Vector2(2,4)
		card.mesh=quad
		card.layers=2
		var emitter:=StandardMaterial3D.new()
		emitter.albedo_color=Color.BLACK
		emitter.emission_enabled=true
		emitter.emission=Color(.55,.55,.55)
		emitter.cull_mode=BaseMaterial3D.CULL_DISABLED
		card.material_override=emitter
		stage.add_child(card)
		card.position=point+(2*normal.dot(view)*normal-view)*2
		card.look_at(point,camera.basis.y)
		mask_material.set_shader_parameter("card_center",card.global_position)
		mask_material.set_shader_parameter("card_normal",card.global_basis.z)
		mask_material.set_shader_parameter("card_right",card.global_basis.x)
		mask_material.set_shader_parameter("card_up",card.global_basis.y)
		camera.cull_mask=1
		card.visible=false
		await _edge_probe(point)
		var off:=await _capture(patch+"-off")
		card.visible=true
		await _edge_probe(point)
		var on:=await _capture(patch+"-on")
		pane.mesh=flat_mesh
		var flat:=await _capture(patch+"-flattened")
		pane.mesh=mask_mesh
		pane.material_override=mask_material
		var mask:=await _capture(patch+"-bevel-mask")
		pane.mesh=source_mesh
		pane.material_override=null
		var signals: Array[float]=[]
		var flat_signals: Array[float]=[]
		var positive:=0
		var visible_rows: Dictionary={}
		var lit_rows: Dictionary={}
		var coverage:=0.0
		for y: int in range(3,645):
			for x: int in range(3,1149):
				var weight:=mask.get_pixel(x,y).srgb_to_linear().r
				coverage+=weight
				if weight<.05:
					continue
				var response:=_linear(on,x,y)-_linear(off,x,y)
				signals.append(response)
				flat_signals.append(_linear(flat,x,y)-_linear(off,x,y))
				visible_rows[y]=true
				if response>=.005:
					positive+=1
					lit_rows[y]=true
		var longest:=0
		var current:=0
		for y: int in range(3,645):
			current=current+1 if visible_rows.has(y) and lit_rows.has(y) else 0
			longest=maxi(longest,current)
		var span:=float(longest)/maxi(visible_rows.size(),1)
		signals.sort()
		var median: float=signals[signals.size()/2] if not signals.is_empty() else 0.0
		var loss:=1-_mean(flat_signals)/maxf(_mean(signals),1e-9)
		_gate(patch+"_coverage",coverage>=100,{"pixel_area":coverage,"samples":signals.size()},100)
		_gate(patch+"_signal",median>=.005,median,.005)
		_gate(patch+"_span",span>=.75,{"projected_contiguous_fraction":span,"rows":visible_rows.size(),"longest":longest,"responding_pixels":float(positive)/maxi(signals.size(),1)},.75)
		_gate(patch+"_flattened_loss",loss>=.5,loss,.5)
		card.free()
		probe.free()
		probe=null
	results.metadata={"failures":failures,"distance":.5,"fov":70,"regions":region_path}
	FileAccess.open(output.path_join("measurements.json"),FileAccess.WRITE).store_string(JSON.stringify(results,"\t"))
	print("EDGE ",failures)
	quit(0 if failures.is_empty() else 1)

func _edge_probe(origin: Vector3) -> void:
	probe=Lighting.bay_reflection_probe()
	probe.position=origin
	probe.size=Vector3(8,8,8)
	probe.cull_mask=2
	probe.box_projection=false
	stage.add_child(probe)
	for i: int in range(20):
		await process_frame
		RenderingServer.call_deferred("force_draw",false)
		await RenderingServer.frame_post_draw

func _variant(flatten: bool,mask: bool) -> ArrayMesh:
	var arrays:=source_mesh.surface_get_arrays(0)
	var vertices: PackedVector3Array=arrays[Mesh.ARRAY_VERTEX]
	var normals: PackedVector3Array=arrays[Mesh.ARRAY_NORMAL]
	var colors: PackedColorArray=arrays[Mesh.ARRAY_COLOR]
	var indices: PackedInt32Array=arrays[Mesh.ARRAY_INDEX]
	assert(regions.size()==indices.size()/3)
	var broad: Dictionary[int,bool]={}
	for t: int in range(regions.size()):
		if int(regions[t])==0:
			for j: int in range(3):
				broad[indices[t*3+j]]=true
	var tool:=SurfaceTool.new()
	tool.begin(Mesh.PRIMITIVE_TRIANGLES)
	tool.set_material(PodMesh.canopy_material())
	for t: int in range(regions.size()):
		for j: int in range(3):
			var i:=indices[t*3+j]
			var n:=normals[i]
			if flatten and int(regions[t])==3:
				var nearest:=-1
				var distance:=INF
				for k: int in broad:
					var d:=vertices[k].distance_squared_to(vertices[i])
					if d<distance:
						distance=d
						nearest=k
				n=normals[nearest]
			tool.set_normal(n)
			tool.set_color((Color.WHITE if int(regions[t])==3 else Color.BLACK) if mask else colors[i])
			tool.add_vertex(vertices[i])
	return tool.commit()
