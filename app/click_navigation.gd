class_name ClickNavigation
extends RefCounted
## Tick-side objective admission, facing and one-shot interaction scheduling.

var interaction_id: StringName

func prepare(plane: InputPlane, game: Game, motion: PlayerMotion, interactions: Interactions, look: Vector2) -> Vector2:
	interaction_id = &""
	var offered := plane.take_objective()
	var follower := motion.objectives
	if motion.state() != PlayerMotion.BodyState.WALK or game.phase.current() != Phase.Wake.STANDING:
		follower.cancel()
		return look
	if plane.movement_pressed():
		follower.cancel()
		return look
	if offered != null:
		_admit(offered, plane, game, motion, interactions)
	if follower.current == null:
		return look
	var objective := follower.current
	if motion.mounted():
		follower.cancel()
		return look
	if objective.kind != ClickObjective.Kind.ACT:
		return look
	var target := interactions.target_for(objective.target_id, objective.deck, motion.capsule().foot)
	var delta := target.center - motion.capsule().foot
	if Vector2(delta.x, delta.z).length() <= target.reach + 1.0:
		look.x = atan2(-delta.x, -delta.z)
	var facing := -Basis.from_euler(Vector3(look.y, look.x, 0)).z
	var ready := motion.mount_target(game.layout, facing) == target.id if target.kind == Interactions.Kind.LADDER else Interactions.hit_distance(target, Interactions.context_for(game, motion, facing), interactions.selection_solids(motion.deck())) >= 0
	if ready:
		plane.offer_press(InputPlane.Buttons.INTERACT)
		interaction_id = target.id
		follower.cancel()
	return look

func _admit(offered: ClickObjective, plane: InputPlane, game: Game, motion: PlayerMotion, interactions: Interactions) -> void:
	if offered.deck < 1 or offered.deck > 30:
		return
	if motion.mounted():
		var ladder := motion.locomotion.ladder_state()
		if offered.kind == ClickObjective.Kind.ACT and offered.target_id == ladder.well_id() and ladder.mode() == Ladder.Mode.CLIMBING and offered.deck == ladder.dismount_deck():
			motion.objectives.cancel()
			plane.offer_press(InputPlane.Buttons.INTERACT)
		return
	if offered.deck != motion.deck():
		return
	var objective := offered.copy()
	if objective.kind == ClickObjective.Kind.FLOOR:
		if not objective.point.is_finite() or absf(objective.point.y - game.layout.floor_y(objective.deck)) > 0.02:
			return
	else:
		var foot := motion.capsule().foot
		var target := interactions.target_for(objective.target_id, objective.deck, foot)
		if target == null or target.deck != objective.deck:
			return
		objective.target_id = target.id
		var toward := Vector3(target.center.x - foot.x, 0, target.center.z - foot.z)
		var stand_off := minf(toward.length(), target.reach - 0.15)
		objective.point = target.center - toward.normalized() * stand_off
		objective.point.y = game.layout.floor_y(objective.deck)
		if target.kind == Interactions.Kind.LADDER:
			objective.point = game.layout.well(target.id).landing(objective.deck).origin
		var displacement := objective.point - foot
		displacement.y = 0
		var supported := game.collision.supported_walk_on_deck(objective.deck, motion.capsule(), displacement)
		var swept := Resolve.resolve_constrained_motion(motion.capsule(), supported, game.collision.deck_set(objective.deck))
		if not swept.is_ok() or (swept.motion.displacement - displacement).length() > Controller.PENETRATION_TOLERANCE:
			return
	motion.objectives.set_objective(objective)
