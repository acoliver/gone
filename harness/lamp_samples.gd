extends RefCounted
## Lens pixels come from fixture records, not frame colour segmentation.
## Rays use the rendered meshes (including moving leaves and batched steel).

const Protocol := preload("res://harness/protocol.gd")
const WHITE_MIN_LUMA := 0.5
# Unlit brown lenses still reflect the white circuit at exposure 2.
const EMERGENCY_MAX_LUMA := 0.45
const RED_ADVANCE := 0.02
const EMERGENCY_MAX_RED := 0.6

var _triangles: Dictionary = {}

static func validate(lamps: Variant) -> String:
	if not lamps is Array: return "lamps must be an array"
	for lamp: Variant in lamps:
		if not lamp is Dictionary: return "lamp must be an object"
		if not lamp.get("id") is String: return "lamp needs a fixture id"
		if lamp.get("circuit") not in ["white", "emergency"]: return "lamp needs a white/emergency circuit"
		if not lamp.get("pixels") is Array or lamp.pixels.is_empty(): return "lamp needs a nonempty pixel patch"
		for point: Variant in lamp.pixels:
			if not point is Array or point.size() != 2: return "lamp pixel must be [x, y]"
			for value: Variant in point:
				if not (value is int or value is float) or not is_finite(float(value)) or float(value) != floor(float(value)) or float(value) < 0:
					return "lamp pixel coordinates must be nonnegative integers"
	return ""

func record(scene: Node3D, camera: Camera3D, size: Vector2i) -> Array:
	var geometry: Array = []
	var lenses: Array[MeshInstance3D] = []
	_collect(scene, camera.cull_mask, geometry, lenses)
	var result: Array = []
	for lens: MeshInstance3D in lenses:
		var center := lens.global_transform * lens.mesh.get_aabb().get_center()
		if camera.is_position_behind(center): continue
		var bounds := lens.mesh.get_aabb()
		var projected := Rect2(camera.unproject_position(lens.global_transform * bounds.get_endpoint(0)), Vector2.ZERO)
		for corner: int in range(1, 8):
			projected = projected.expand(camera.unproject_position(lens.global_transform * bounds.get_endpoint(corner)))
		var visible_pixels: Array = []
		for y: int in range(maxi(0, int(floor(projected.position.y))), mini(size.y, int(ceil(projected.end.y)))):
			for x: int in range(maxi(Protocol.chip_size().x, int(floor(projected.position.x))), mini(size.x, int(ceil(projected.end.x)))):
				var point := Vector2(x + 0.5, y + 0.5)
				var origin := camera.project_ray_origin(point)
				var direction := camera.project_ray_normal(point)
				var hit := _hit(lens.mesh, lens.global_transform, origin, origin + direction * camera.far)
				if hit.is_empty(): continue
				var end: Vector3 = hit.position - direction * 0.001
				var occluded := false
				for item: Dictionary in geometry:
					if item.node == lens: continue
					if item.bounds.intersects_segment(origin, end) == null: continue
					if not _hit(item.mesh, item.transform, origin, end).is_empty():
						occluded = true
						break
				if not occluded: visible_pixels.append(Vector2i(x, y))
		var pixels: Array = []
		if not visible_pixels.is_empty():
			# Sample a small patch around an actually visible pixel, including
			# partially occluded lenses whose projected centre is hidden.
			var anchor: Vector2i = visible_pixels[visible_pixels.size() / 2]
			for point: Vector2i in visible_pixels:
				if absi(point.x - anchor.x) <= 2 and absi(point.y - anchor.y) <= 2:
					pixels.append([point.x, point.y])
		if not pixels.is_empty():
			result.append({"id": String(scene.get_path_to(lens)), "circuit": String(lens.get_meta(&"lamp_circuit")), "pixels": pixels})
	return result

func _hit(mesh: Mesh, frame: Transform3D, start: Vector3, end: Vector3) -> Dictionary:
	var inverse := frame.affine_inverse()
	var local_start := inverse * start
	var local_end := inverse * end
	if mesh.get_aabb().intersects_segment(local_start, local_end) == null: return {}
	if not _triangles.has(mesh): _triangles[mesh] = mesh.generate_triangle_mesh()
	var hit: Dictionary = _triangles[mesh].intersect_segment(local_start, local_end)
	if not hit.is_empty(): hit.position = frame * hit.position
	return hit

func _collect(node: Node, mask: int, geometry: Array, lenses: Array[MeshInstance3D]) -> void:
	if node is Node3D and not node.is_visible_in_tree(): return
	if node is MeshInstance3D and node.mesh != null and (node.layers & mask) != 0:
		if node.has_meta(&"lamp_circuit"): lenses.append(node)
		if _opaque(node): geometry.append(_geometry(node, node.mesh, node.global_transform))
	if node is MultiMeshInstance3D and node.multimesh != null and (node.layers & mask) != 0:
		var count: int = node.multimesh.instance_count
		if node.multimesh.visible_instance_count >= 0: count = node.multimesh.visible_instance_count
		for index: int in range(count):
			geometry.append(_geometry(node, node.multimesh.mesh, node.global_transform * node.multimesh.get_instance_transform(index)))
	for child: Node in node.get_children(): _collect(child, mask, geometry, lenses)

func _geometry(node: Node3D, mesh: Mesh, frame: Transform3D) -> Dictionary:
	return {"node": node, "mesh": mesh, "transform": frame, "bounds": frame * mesh.get_aabb()}

func _opaque(node: MeshInstance3D) -> bool:
	var material := node.get_active_material(0)
	if material is BaseMaterial3D: return material.transparency == BaseMaterial3D.TRANSPARENCY_DISABLED
	if material is ShaderMaterial: return not material.shader.code.contains("ALPHA")
	return true

static func evaluate(image: Image, lamps: Array) -> Dictionary:
	var failures: Array[String] = []
	var lines: Array[String] = []
	var white_lit := 0
	var white_visible := 0
	for lamp: Dictionary in lamps:
		var sum := Vector3.ZERO
		var pixels: Array = lamp.pixels
		if pixels.is_empty():
			failures.append("lamp `%s` has an empty sample" % lamp.id)
			continue
		var outside := pixels.any(func(point: Array) -> bool: return point[0] < Protocol.chip_size().x or point[0] >= image.get_width() or point[1] < 0 or point[1] >= image.get_height())
		if outside:
			failures.append("lamp `%s` sample outside the measured frame" % lamp.id)
			continue
		for point: Array in pixels:
			var color := image.get_pixel(int(point[0]), int(point[1]))
			sum += Vector3(color.r, color.g, color.b)
		var rgb := sum / float(pixels.size())
		var luma := Color(rgb.x, rgb.y, rgb.z).get_luminance()
		var red := rgb.x >= rgb.y + RED_ADVANCE and rgb.x >= rgb.z + RED_ADVANCE
		var passed: bool
		if lamp.circuit == "white":
			white_visible += 1
			passed = luma >= WHITE_MIN_LUMA and not red
			if passed: white_lit += 1
		else:
			passed = luma <= EMERGENCY_MAX_LUMA and rgb.x <= EMERGENCY_MAX_RED
			if not passed: failures.append("emergency lens `%s` not dark: luma %.4f red %.4f" % [lamp.id, luma, rgb.x])
		lines.append("lamp `%s` %s pixels=%s luma=%.4f rgb=%.4f/%.4f/%.4f %s" % [lamp.id, lamp.circuit, str(pixels), luma, rgb.x, rgb.y, rgb.z, "PASS" if passed else "FAIL"])
	if white_visible == 0:
		failures.append("scenario authoring error: no regular-white lens visible outside the chip; frame a regular strip")
	elif white_lit == 0:
		failures.append("no visible regular-white lens is lit white")
	return {"failures": failures, "lines": lines}
