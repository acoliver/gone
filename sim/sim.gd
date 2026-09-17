class_name Sim
extends RefCounted
## Facade over the ported gone_sim modules, mirroring lib.rs: every
## module's public surface reachable through one place. The sim owns and
## advances the authoritative game state with no display server, no GPU,
## and no render code involved.

## colliders
const Aabb := ColliderSet.Aabb
const ColliderError := ColliderSet.ColliderError

## intensity
const FixtureFade := Intensity.FixtureFade
const FixtureFadeError := Intensity.FixtureFadeError

## phase
const PhaseError := Phase.PhaseError
const PhaseTransition := Phase.Transition
const WakePhase := Phase.Wake

## pods
const POD_COUNT := Pods.POD_COUNT
const HatchPlacement := Pods.HatchPlacement
const Pod := Pods.Pod
const PodId := Pods.PodId
const PodPlacement := Pods.PodPlacement
const PodRegistry := Pods.PodRegistry
const PodRegistryError := Pods.PodRegistryError
const PodState := Pods.PodState

## power
const PowerGrid := Power.Grid
const PowerState := Power.State
const PowerTransition := Power.Transition

## resolve
const Capsule := Resolve.Capsule
const NonFiniteInput := Resolve.ResolveError.NonFiniteInput
const ResolveError := Resolve.ResolveError
const ResolvedMotion := Resolve.ResolvedMotion

static func resolve_motion(capsule: Resolve.Capsule, displacement: Vector3, colliders: ColliderSet) -> Resolve.Result:
	return Resolve.resolve_motion(capsule, displacement, colliders)

## wake
const AuthoredBoundaries := Wake.AuthoredBoundaries
const LOGICAL_TICK_SECS := Wake.LOGICAL_TICK_SECS
const LOGICAL_TICKS_PER_SECOND := Wake.LOGICAL_TICKS_PER_SECOND
const WakeSample := Wake.WakeSample
const WakeStart := Wake.WakeStart
const WakeState := Wake.WakeState
const WakeTimeline := Wake.WakeTimeline
const WakeTimelineError := Wake.WakeTimelineError

## walk
const IntentAxis := Walk.IntentAxis
const MoveIntent := Walk.MoveIntent
const WalkContact := Walk.WalkContact
const WalkError := Walk.WalkError
const WalkOutcome := Walk.WalkOutcome
const WalkState := Walk.WalkState

## Minimal stand-in for a full ship entity: enough state to prove the sim
## builds and its logic runs standalone until real ship systems arrive.
class ShipState:
	extends RefCounted

	var _hull: int = 0

	func _init(hull: int) -> void:
		_hull = hull

	## Remaining hull integrity, where 0 means destroyed.
	func hull() -> int:
		return _hull

	## Applies hull damage, clamped so a ship never falls below zero hull.
	func apply_damage(amount: int) -> void:
		_hull = maxi(_hull - amount, 0)

	## Whether any hull integrity remains.
	func is_intact() -> bool:
		return _hull > 0
