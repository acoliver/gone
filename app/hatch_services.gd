class_name HatchServices
extends RefCounted
## Local mesh details for layout-owned hatch service assemblies. No new lights.

static func _piece(parent: Node3D, mesh: Mesh, pose: Transform3D, mask: int, role: StringName, frame: Surfaces.SurfaceFrame) -> MeshInstance3D:
	var piece := HatchModel.mesh_piece(mesh, pose, mask, Surfaces.material(role))
	Surfaces.bind(piece, role, frame)
	parent.add_child(piece)
	return piece

static func _box(parent: Node3D, size: Vector3, center: Vector3, mask: int, frame: Surfaces.SurfaceFrame) -> MeshInstance3D:
	return _piece(parent, HatchModel.box_mesh(size), Transform3D(Basis(), center), mask, &"hardware", frame)

static func _rounded(parent: Node3D, size: Vector3, radius: float, center: Vector3, mask: int, role: StringName, frame: Surfaces.SurfaceFrame) -> MeshInstance3D:
	var part := HatchParts.Part.new(&"prop", &"rounded", size, Transform3D.IDENTITY, radius)
	var key := [size, radius, &"service"]
	if not HatchModel._meshes.has(key): HatchModel._meshes[key] = HatchModel._part_mesh(part)
	return _piece(parent, HatchModel._meshes[key], Transform3D(Basis(), center), mask, role, frame)

static func _pin(parent: Node3D, radius: float, length: float, center: Vector3, axis: Vector3, mask: int, frame: Surfaces.SurfaceFrame) -> MeshInstance3D:
	return _piece(parent, HatchModel.cylinder(radius, length), Transform3D(Basis(Quaternion(Vector3.UP, axis.normalized())), center), mask, &"hardware", frame)

static func _rod(parent: Node3D, a: Vector3, b: Vector3, radius: float, mask: int, frame: Surfaces.SurfaceFrame) -> void:
	_pin(parent, radius, a.distance_to(b), (a + b) / 2, b - a, mask, frame)

static func build(spec: ShipLayout.DoorSpec, side: int, mask: int) -> Node3D:
	var root := Node3D.new()
	root.name = "ForeServices" if side == 0 else "AftServices"
	var frame := Surfaces.door_frame(spec, &"FRAME")
	for service: ShipLayout.HatchServiceSpec in spec.hatch_services(side):
		var group := Node3D.new()
		group.name = service.kind
		group.transform = service.frame
		root.add_child(group)
		match service.kind:
			&"Control": _control(group, mask, frame)
			&"Lamp": _lamp(group, service, mask, frame)
			&"Conduit": _conduit(group, service, mask, frame)
		if service.kind != &"Control": _batch_metal(group, mask, frame)
	return root

static func _batch_metal(root: Node3D, mask: int, frame: Surfaces.SurfaceFrame) -> void:
	var pieces: Array[MeshInstance3D] = []
	var key: Array = [&"service_batch"]
	for child: Node in root.get_children():
		if child is MeshInstance3D and child.material_override == Surfaces.material(&"hardware"):
			pieces.append(child)
			key.append([child.mesh, child.transform])
	if not HatchModel._meshes.has(key):
		var mesh := ArrayMesh.new()
		var bounds: Array[AABB] = []
		for piece: MeshInstance3D in pieces:
			var tool := SurfaceTool.new()
			tool.begin(Mesh.PRIMITIVE_TRIANGLES)
			HatchModel._append(tool, piece.mesh, piece.transform)
			tool.index()
			tool.commit(mesh)
			bounds.append(piece.transform * piece.mesh.get_aabb())
		mesh.set_meta(&"service_bounds", bounds)
		HatchModel._meshes[key] = mesh
	for piece: MeshInstance3D in pieces: piece.free()
	var batch := _piece(root, HatchModel._meshes[key], Transform3D.IDENTITY, mask, &"hardware", frame)
	batch.name = "Steel"

static func _control(root: Node3D, mask: int, frame: Surfaces.SurfaceFrame) -> void:
	_box(root, Vector3(0.38, 0.56, 0.05), Vector3(0, 0, 0.075), mask, frame).name = "MountingBox"
	_rounded(root, Vector3(0.34, 0.52, 0.13), 0.035, Vector3.ZERO, mask, &"frame", frame).name = "Housing"
	var face := _box(root, Vector3(0.285, 0.445, 0.016), Vector3(0, 0, -0.070), mask, frame)
	face.name = "FacePlate"
	face.material_override = Surfaces.control_material(&"face")
	for dx: float in [-0.12, 0.12]:
		for dy: float in [-0.19, 0.19]:
			_pin(root, 0.013, 0.016, Vector3(dx, dy, -0.080), Vector3.BACK, mask, frame).name = "Fastener%d%d" % [int(dx > 0), int(dy > 0)]
	var bezel := _pin(root, 0.059, 0.030, Vector3(0, 0.080, -0.092), Vector3.BACK, mask, frame)
	bezel.name = "ButtonBezel"
	bezel.material_override = Surfaces.control_material(&"dark")
	var button := _pin(root, 0.043, 0.030, Vector3(0, 0.080, -0.116), Vector3.BACK, mask, frame)
	button.name = "Button"
	button.material_override = Surfaces.control_material(&"button")
	var slot := _box(root, Vector3(0.19, 0.027, 0.018), Vector3(0, -0.110, -0.083), mask, frame)
	slot.name = "CardReader"
	slot.material_override = Surfaces.control_material(&"dark")
	var indicator := _pin(root, 0.015, 0.022, Vector3(-0.090, 0.160, -0.088), Vector3.BACK, mask, frame)
	indicator.name = "Indicator"
	indicator.material_override = Surfaces.control_material(&"indicator")
	var toggle := _box(root, Vector3(0.018, 0.060, 0.025), Vector3(0.085, -0.040, -0.083), mask, frame)
	toggle.name = "Toggle"
	toggle.rotation.x = -0.3

static func _lamp(root: Node3D, service: ShipLayout.HatchServiceSpec, mask: int, frame: Surfaces.SurfaceFrame) -> void:
	var mount_depth := 0.10 + service.stand_off
	_box(root, Vector3(0.31, 0.24, mount_depth), Vector3(0, 0, 0.02 + mount_depth / 2), mask, frame)
	_rounded(root, Vector3(0.37, 0.31, 0.055), 0.045, Vector3.ZERO, mask, &"hardware", frame)
	var lens := _rounded(root, Vector3(0.26, 0.16, 0.07), 0.065, Vector3(0, 0, -0.060), mask, &"hardware", frame)
	lens.name = "Lens"
	lens.set_meta(&"lamp_circuit", "emergency")
	lens.material_override = Lighting.emergency_lens_material(1.0)
	lens.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	for dy: float in [-0.115, 0.115]:
		_rod(root, Vector3(-0.16, dy, -0.12), Vector3(0.16, dy, -0.12), 0.012, mask, frame)
		for dx: float in [-0.16, 0.16]:
			_rod(root, Vector3(dx, dy, -0.015), Vector3(dx, dy, -0.12), 0.011, mask, frame)
	for dx: float in [-0.14, -0.07, 0, 0.07, 0.14]:
		_rod(root, Vector3(dx, -0.115, -0.12), Vector3(dx, 0.115, -0.12), 0.009, mask, frame)

static func _conduit(root: Node3D, service: ShipLayout.HatchServiceSpec, mask: int, frame: Surfaces.SurfaceFrame) -> void:
	for index: int in range(service.route.size() - 1):
		var a := service.route[index]
		var b := service.route[index + 1]
		_rod(root, a, b, service.radius, mask, frame)
		var count := maxi(1, int(ceil(a.distance_to(b) / 0.70)))
		for step: int in range(count):
			var point := a.lerp(b, (step + 0.5) / count)
			_pin(root, service.radius * 1.3, 0.045, point, b - a, mask, frame)
			_box(root, Vector3(0.065, 0.035, 0.10), Vector3(point.x, point.y, -0.03), mask, frame)
	for endpoint: Vector3 in [service.route[0], service.route[-1]]:
		_pin(root, service.radius * 1.5, 0.045, endpoint, Vector3.UP, mask, frame)

static func bind_lens(view: DoorView, side: int, material: Material) -> void:
	var lens: MeshInstance3D = view.get_node("%sServices/Lamp/Lens" % ("Fore" if side == 0 else "Aft"))
	lens.material_override = material

static func seat_fixture(view: DoorView, side: int, fixture: Node3D) -> void:
	var lamp: Node3D = view.get_node("%sServices/Lamp" % ("Fore" if side == 0 else "Aft"))
	var world := Surfaces.world_frame(lamp)
	world.origin += world.basis.z * -0.20
	fixture.transform = Surfaces.world_frame(fixture.get_parent()).affine_inverse() * world
	fixture.get_node("Lens").visible = false
	fixture.set_meta(&"hatch_lamp", true)

static func seat_nearest(view: DoorView, side: int, lights: Array[OmniLight3D]) -> void:
	var lamp: Node3D = view.get_node("%sServices/Lamp" % ("Fore" if side == 0 else "Aft"))
	var target := Surfaces.world_frame(lamp).origin
	var nearest: Node3D
	var distance := INF
	for light: OmniLight3D in lights:
		var fixture := light.get_parent() as Node3D
		if fixture.has_meta(&"hatch_lamp"): continue
		var candidate := target.distance_squared_to(Surfaces.world_frame(fixture).origin)
		if candidate < distance:
			distance = candidate
			nearest = fixture
	assert(nearest != null, "a switched-room fixture is available for its hatch lamp")
	seat_fixture(view, side, nearest)
