class_name ClickPicker
extends RefCounted
## Presentation rays use the same layout targets and solids as the fixed tick.

const RAY_LENGTH: float = 80.0

static func pick(origin: Vector3, direction: Vector3, game: Game, motion: PlayerMotion, interactions: Interactions) -> ClickObjective:
	if motion.state() != PlayerMotion.BodyState.WALK:
		return null
	if motion.mounted():
		return _landing(origin, direction, game, motion)
	var deck := motion.deck()
	var end := origin + direction * RAY_LENGTH
	var wall_distance := RAY_LENGTH
	var floor_hit := Vector3.ZERO
	var has_floor := false
	var solid_id: StringName
	var boxes := game.collision.deck_set(deck).boxes()
	var ids := game.collision.solid_ids(deck)
	for index: int in range(boxes.size()):
		var box := boxes[index]
		var bounds := AABB(box.min_corner(), box.max_corner() - box.min_corner())
		var fraction := Interactions.segment_hit(origin, end, bounds)
		if fraction < 0 or fraction * RAY_LENGTH >= wall_distance:
			continue
		wall_distance = fraction * RAY_LENGTH
		solid_id = ids[index]
		floor_hit = origin + direction * wall_distance
		has_floor = direction.y < 0 and absf(floor_hit.y - game.layout.floor_y(deck)) < 0.02
	var closest := RAY_LENGTH
	var selected: Interactions.Target
	for target: Interactions.Target in interactions.targets_on_deck(deck):
		if target.kind == Interactions.Kind.PICKUP and motion.rod_carried:
			continue
		if target.kind == Interactions.Kind.DOOR and game.doors.snapshot(target.door_id).state == Doors.State.OPEN:
			continue
		var distance := _target_distance(origin, direction, target, game.layout)
		# The bay's ajar leaf stands proud of its portal, but is still that target.
		if distance >= 0 and target.kind == Interactions.Kind.DOOR and String(solid_id).begins_with(String(target.door_id) + "/"):
			distance = minf(distance, wall_distance)
		if distance >= 0 and distance < closest and distance <= wall_distance + 0.0001:
			closest = distance
			selected = target
	if selected != null:
		return ClickObjective.act(selected.id, deck)
	if has_floor:
		return ClickObjective.floor_point(floor_hit, deck)
	return null

static func _target_distance(origin: Vector3, direction: Vector3, target: Interactions.Target, layout: ShipLayout) -> float:
	if target.policy == Interactions.Selection.FACE_RAY:
		var distance := _face_distance(origin, direction, target.frame, target.size)
		if distance >= 0 and target.kind == Interactions.Kind.DOOR and layout.door(target.door_id).kind() == ShipLayout.DoorKind.SIDE:
			var fraction := Interactions.segment_hit(origin, origin + direction * RAY_LENGTH, target.bounds)
			if fraction >= 0:
				distance = minf(distance, fraction * RAY_LENGTH)
		return distance
	if target.kind == Interactions.Kind.DOOR:
		var door := layout.door(target.door_id)
		var best := INF
		for id: StringName in door.face_ids():
			var distance := _face_distance(origin, direction, door.frame() * layout.face(id).surface_frame(), door.aperture())
			if distance >= 0:
				best = minf(best, distance)
		return -1.0 if best == INF else best
	var center := target.center
	var size := Vector3(0.4, 0.3, 0.3)
	match target.kind:
		Interactions.Kind.PICKUP:
			center.y += 0.05
			size = Vector3(0.22, 0.10, 1.15)
		Interactions.Kind.CONSOLE:
			var fraction := Interactions.segment_hit(origin, origin + direction * RAY_LENGTH, target.bounds)
			return fraction * RAY_LENGTH if fraction >= 0 else -1.0
	var fraction := Interactions.segment_hit(origin, origin + direction * RAY_LENGTH, AABB(center - size * 0.5, size))
	return fraction * RAY_LENGTH if fraction >= 0 else -1.0

static func _face_distance(origin: Vector3, direction: Vector3, frame: Transform3D, size: Vector2) -> float:
	var eye := frame.affine_inverse() * origin
	var ray := frame.basis.inverse() * direction
	if eye.z <= 0 or ray.z >= 0:
		return -1.0
	var distance := -eye.z / ray.z
	var hit := eye + ray * distance
	return distance if absf(hit.x) <= size.x / 2.0 and hit.y >= 0 and hit.y <= size.y else -1.0

static func _landing(origin: Vector3, direction: Vector3, game: Game, motion: PlayerMotion) -> ClickObjective:
	var ladder := motion.locomotion.ladder_state()
	if ladder.mode() != Ladder.Mode.CLIMBING:
		return null
	var deck := ladder.dismount_deck()
	if deck == 0:
		return null
	var target := Interactions.ladder_target(game.layout, ladder.well_id(), deck, true)
	if _face_distance(origin, direction, target.frame, target.size) < 0:
		return null
	return ClickObjective.act(target.id, deck)
