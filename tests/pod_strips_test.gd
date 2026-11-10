extends SimTestCase
# New pod #88: pins follow the fitted asset, row centers and eight-piece topology.
## Pins for the PodStrips emissive flank belts: every pod group carries
## exactly one "PodStrips" child instancing the one shared merged mesh
## (one surface, one material, exactly 576 triangles), the build is
## deterministic across rebuilds and scene builds, the material follows
## the fixture lens emission convention, the belt waypoints sit against
## the measured shell skin at their belt heights, the strips clear every
## authored dressing solid by the measured margins, and nothing in the
## strip pass adds a light or a collider.

const BELT_DOME_Y: float = 0.28
const BELT_TRAY_Y: float = 0.28 # #88: both flanks share the mid-height belt.
const CONTACT_TOLERANCE: float = 0.011
const GAP_EPSILON: float = 1e-4

var _skin_triangles: Array[PackedVector3Array] = []

func test_both_flanks_have_the_same_world_height_in_both_rows() -> void:
	# #88: yaw preserves Y; the authored 120 mm tray table caused the low belt.
	for pod: Pods.Pod in Pods.PodRegistry.frozen().pods():
		var placement := pod.placement()
		var frame := Transform3D(Basis(Vector3.UP, placement.yaw_radians), Vector3(placement.center.x, 0, placement.center.y))
		for plus: Vector3 in PodStrips.FLANK_DOME:
			for minus: Vector3 in PodStrips.FLANK_TRAY:
				assert_true(absf((frame * plus).y - (frame * minus).y) < 1e-5,
					"pod %d has matching world-space flank heights" % pod.id().index())

func test_every_pod_carries_the_one_shared_strip_mesh() -> void:
	var pods := StasisPods.build(Pods.PodRegistry.frozen())
	var groups: Array[Node] = pods.get_children()
	assert_int_equal(groups.size(), Pods.POD_COUNT, "every registry pod gets a group")
	var total_strips := 0
	for group: Node in groups:
		var strips := 0
		for child: Node in group.get_children():
			if child.name != "PodStrips":
				continue
			var instance := child as MeshInstance3D
			assert_true(instance != null, "%s's PodStrips child is a MeshInstance3D" % group.name)
			assert_true(instance.get_parent() == group, "the strip's parent is the pod group, so the registry transform carries it")
			assert_true(instance.mesh == PodStrips.strips_mesh(), "%s's strip instances the one shared mesh" % group.name)
			strips += 1
		assert_int_equal(strips, 1, "%s carries exactly one PodStrips child" % group.name)
		total_strips += strips
	assert_int_equal(total_strips, Pods.POD_COUNT, "all seven pods carry the strip")
	var mesh: ArrayMesh = PodStrips.strips_mesh()
	assert_int_equal(mesh.get_surface_count(), 1, "both flank tubes merge into one surface")
	var arrays: Array = mesh.surface_get_arrays(0)
	var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
	assert_int_equal(indices.size() % 3, 0, "the strip surface index buffer is whole triangles")
	assert_int_equal(indices.size() / 3, 576, "the strip mesh is exactly 576 tris (304 dome + 272 tray)")

func test_strip_builds_are_deterministic() -> void:
	var instance := PodStrips.make()
	assert_true(instance.mesh == PodStrips.strips_mesh(), "fresh strip instances share the one mesh")
	var first := PodStrips._build_mesh()
	var second := PodStrips._build_mesh()
	var a := first.surface_get_arrays(0)
	var b := second.surface_get_arrays(0)
	var va: PackedVector3Array = a[Mesh.ARRAY_VERTEX]
	var vb: PackedVector3Array = b[Mesh.ARRAY_VERTEX]
	assert_int_equal(va.size(), vb.size(), "rebuilds produce the same vertex count")
	if va.size() == vb.size():
		assert_true(va == vb, "two independent builds produce identical vertices")
	var ia: PackedInt32Array = a[Mesh.ARRAY_INDEX]
	var ib: PackedInt32Array = b[Mesh.ARRAY_INDEX]
	assert_int_equal(ia.size(), ib.size(), "rebuilds produce the same index count")
	if ia.size() == ib.size():
		assert_true(ia == ib, "two independent builds produce identical indices")
	var pods_a := StasisPods.build(Pods.PodRegistry.frozen())
	var pods_b := StasisPods.build(Pods.PodRegistry.frozen())
	assert_int_equal(pods_b.get_child_count(), pods_a.get_child_count(), "both scene builds carry every pod group")
	for index: int in range(pods_a.get_child_count()):
		var from_a := _strips_of(pods_a.get_child(index))
		var from_b := _strips_of(pods_b.get_child(index))
		if from_a == null or from_b == null:
			assert_true(false, "pod %d carries its strips in both builds" % index)
			continue
		assert_true(from_a.transform == from_b.transform, "pod %d's strip transform is identical across scene rebuilds" % index)
		assert_true(from_a.transform == Transform3D.IDENTITY, "the strip rides its pod group at identity")
		assert_true(from_a.mesh == from_b.mesh and from_a.mesh == PodStrips.strips_mesh(), "pod %d's strip is the one shared mesh in both builds" % index)

func test_strip_material_follows_the_lens_convention() -> void:
	var material: Material = PodStrips.strips_mesh().surface_get_material(0)
	assert_true(material is StandardMaterial3D, "the strip surface carries a StandardMaterial3D")
	var strip: StandardMaterial3D = material
	assert_true(strip.emission_enabled, "the strip material emits")
	assert_true(strip.emission == Color(2.6, 0.0, 0.0), "the strip emission is full-power linear red")
	assert_true(PodStrips.STRIP_EMISSION == Color(Lighting.FIXTURE_EMISSIVE, 0.0, 0.0), "the emission constant is the fixture lens convention")
	assert_true(strip == PodStrips._strip_material(), "the one material in play is the cached shared strip material")

func test_strip_geometry_stays_within_the_pinned_bounds() -> void:
	# New pod #88: outward-offset base belts, measured from the mesh.
	var bounds: AABB = PodStrips.strips_mesh().get_aabb()
	assert_true(bounds.position.x >= -0.4856 - 1e-4 and bounds.end.x <= 0.4853 + 1e-4,
		"strip x within [-0.4856, 0.4853], got %s" % str(bounds))
	assert_true(bounds.position.y >= 0.268 - 1e-4 and bounds.end.y <= 0.292 + 1e-4,
		"strip y within [0.268, 0.292], got %s" % str(bounds))
	assert_true(bounds.position.z >= -0.8534 - 1e-4 and bounds.end.z <= 0.9037 + 1e-4,
		"strip z within [-0.8534, 0.9037], got %s" % str(bounds))
	assert_true(bounds.end.y <= 0.692, "the strip top stays under the 0.692 m pin")
	assert_true(bounds.end.y < Placement.OVERHEAD_CLEARANCE,
		"the strips stay far under the overhead clearance floor")
	assert_true(PodStrips.STRIP_RADIUS > CONTACT_TOLERANCE,
		"the tube radius covers the contact tolerance, so skin contact is guaranteed")

func test_every_waypoint_sits_against_the_shell_skin() -> void:
	_ensure_skin_triangles()
	_assert_skin_contact(PodStrips.FLANK_DOME, true)
	_assert_skin_contact(PodStrips.FLANK_TRAY, false)

## Triangle intersections replace the scan's coarse vertex windows and
## sampling-hole exceptions. The same 0.011 m contact tolerance now also
## holds between stations, not just at the authored waypoints.
func _assert_skin_contact(points: Array[Vector3], positive_x: bool) -> void:
	for index: int in range(points.size()):
		_assert_point_contact(points[index], positive_x)
		if index + 1 < points.size():
			for fraction: float in [0.25, 0.5, 0.75]:
				_assert_point_contact(points[index].lerp(points[index + 1], fraction), positive_x)

func _assert_point_contact(point: Vector3, positive_x: bool) -> void:
	var skin := _skin_x(point, positive_x)
	# New pod #88: tubes sit outside, rather than embedded in, the tub.
	var deviation := absf(point.x) - 0.024 - skin
	assert_true(absf(point.x) - skin >= 0.012, "the tube radius stays outside the shell")
	assert_true(absf(deviation) <= CONTACT_TOLERANCE,
		"belt at %s sits within %.3f of the skin, got %.4f (skin %.4f)" % [
			str(point), CONTACT_TOLERANCE, deviation, skin])

func test_strips_clear_the_authored_dressing() -> void:
	_assert_clearance("sealed lid", _solid_bounds(PodBody.sealed_lid()), 0.208, 0.478)
	_assert_clearance("open lid", _solid_bounds(PodBody.open_lid()), 0.193, 0.463)
	_assert_clearance("hanging blanket", _solid_bounds(PodBody.hanging_blanket()), 0.050, -1.0)
	_assert_clearance("indicator plate", _plate_bounds(), 0.188, 0.288)

func test_strips_add_no_lights_and_no_colliders() -> void:
	var pods := StasisPods.build(Pods.PodRegistry.frozen())
	assert_int_equal(_count_type(pods, "Light3D"), 0, "the pod tree adds no Light3D")
	assert_int_equal(_count_type(pods, "CollisionShape3D"), 0, "the pod tree adds no CollisionShape3D")
	var colliders := Placement.scene_collider_set(Pods.PodRegistry.frozen())
	assert_int_equal(colliders.size(), 67,
		"the scene collider set stays the 67 authored boxes: strips add no solids")

## The pod group's strip instance, or null when the group lacks one.
func _strips_of(group: Node) -> MeshInstance3D:
	for child: Node in group.get_children():
		if child.name == "PodStrips":
			return child as MeshInstance3D
	return null

## All rendered surfaces participate, including the raised glass shoulder.
func _ensure_skin_triangles() -> void:
	if not _skin_triangles.is_empty():
		return
	var mesh := PodMesh.shell_mesh(Pods.PodState.SEALED)
	for surface: int in range(mesh.get_surface_count()):
		var arrays := mesh.surface_get_arrays(surface)
		var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
		for index: int in range(0, indices.size(), 3):
			_skin_triangles.append(PackedVector3Array([
				vertices[indices[index]], vertices[indices[index + 1]], vertices[indices[index + 2]]]))

func _skin_x(point: Vector3, positive_x: bool) -> float:
	var origin := Vector3(2 if positive_x else -2, point.y, point.z)
	var direction := Vector3.LEFT if positive_x else Vector3.RIGHT
	var best := -INF
	for triangle: PackedVector3Array in _skin_triangles:
		var hit: Variant = Geometry3D.ray_intersects_triangle(origin, direction, triangle[0], triangle[1], triangle[2])
		if hit != null:
			best = maxf(best, hit.x if positive_x else -hit.x)
	assert_true(is_finite(best), "shell skin intersects the belt station %s" % str(point))
	return best

## The conservative pod-local AABB [lo, hi] of one authored solid, hull
## of its roll-rotated corners (exact for the flat lid and blanket).
func _solid_bounds(solid: PodBody.PodSolid) -> Array[Vector3]:
	var half := solid.size * 0.5
	var roll := Quaternion(Vector3.RIGHT, solid.roll_radians)
	var lo := Vector3(INF, INF, INF)
	var hi := Vector3(-INF, -INF, -INF)
	for x: float in [-1.0, 1.0]:
		for y: float in [-1.0, 1.0]:
			for z: float in [-1.0, 1.0]:
				var corner: Vector3 = solid.center + roll * (Vector3(x, y, z) * half)
				lo = lo.min(corner)
				hi = hi.max(corner)
	return [lo, hi]

func _plate_bounds() -> Array[Vector3]:
	var plate: Placement.SolidPlacement = Placement.indicator_plate()
	var half := plate.size * 0.5
	return [plate.center - half, plate.center + half]

## No strip waypoint enters the dressing box grown by the tube radius,
## and the minimum waypoint-to-box separation (less the radius) holds
## the spec's measured margin. A negative flank gap skips that flank.
func _assert_clearance(what: String, bounds: Array[Vector3], dome_gap: float, tray_gap: float) -> void:
	var lo: Vector3 = bounds[0]
	var hi: Vector3 = bounds[1]
	for waypoint: Vector3 in PodStrips.FLANK_DOME:
		assert_false(_grown_contains(waypoint, lo, hi, PodStrips.STRIP_RADIUS),
			"the %s box grown by the radius holds no +X waypoint" % what)
	assert_true(_min_gap(PodStrips.FLANK_DOME, lo, hi) >= dome_gap - GAP_EPSILON,
		"the %s clears the +X strip by >= %.3f m" % [what, dome_gap])
	if tray_gap < 0.0:
		return
	for waypoint: Vector3 in PodStrips.FLANK_TRAY:
		assert_false(_grown_contains(waypoint, lo, hi, PodStrips.STRIP_RADIUS),
			"the %s box grown by the radius holds no -X waypoint" % what)
	assert_true(_min_gap(PodStrips.FLANK_TRAY, lo, hi) >= tray_gap - GAP_EPSILON,
		"the %s clears the -X strip by >= %.3f m" % [what, tray_gap])

func _grown_contains(point: Vector3, lo: Vector3, hi: Vector3, radius: float) -> bool:
	return point.x >= lo.x - radius and point.x <= hi.x + radius \
		and point.y >= lo.y - radius and point.y <= hi.y + radius \
		and point.z >= lo.z - radius and point.z <= hi.z + radius

func _min_gap(points: Array[Vector3], lo: Vector3, hi: Vector3) -> float:
	var best := INF
	for waypoint: Vector3 in points:
		var dx := maxf(maxf(lo.x - waypoint.x, waypoint.x - hi.x), 0.0)
		var dy := maxf(maxf(lo.y - waypoint.y, waypoint.y - hi.y), 0.0)
		var dz := maxf(maxf(lo.z - waypoint.z, waypoint.z - hi.z), 0.0)
		best = minf(best, sqrt(dx * dx + dy * dy + dz * dz))
	return best - PodStrips.STRIP_RADIUS

func _count_type(node: Node, type_name: String) -> int:
	var count := 1 if node.is_class(type_name) else 0
	for child: Node in node.get_children():
		count += _count_type(child, type_name)
	return count
