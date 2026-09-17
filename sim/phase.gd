class_name Phase
extends RefCounted
## Wake phase machine, ported from gone_sim phase.rs.
## One forward-only progression governs the opening beat: Waking ->
## AwakeInPod -> ExitingPod -> Standing. Exit-pod intent is consumed only
## in AwakeInPod and only on a fresh press edge; boundary signals are
## idempotent; the only illegal call shape is get-up-complete before
## ExitingPod, which is rejected loudly and leaves the phase unchanged.
## Pure simulation logic: no Node, scene, rendering, or input types.

enum Wake { WAKING, AWAKE_IN_POD, EXITING_POD, STANDING }

enum InputEdge { RISING, HELD }

static func phase_name(phase: int) -> String:
	match phase:
		Wake.WAKING:
			return "Waking"
		Wake.AWAKE_IN_POD:
			return "AwakeInPod"
		Wake.EXITING_POD:
			return "ExitingPod"
		_:
			return "Standing"

static func in_phase(phase: int, candidate: int) -> bool:
	return phase == candidate

## Look is allowed from AwakeInPod onward and from nothing before it.
static func look_allowed(phase: int) -> bool:
	return phase != Wake.WAKING

## The single locomotion predicate: true only in Standing.
static func locomotion_allowed(phase: int) -> bool:
	return phase == Wake.STANDING

class Transition:
	extends RefCounted

	enum Kind { ADVANCED, ALREADY_DELIVERED, IGNORED }

	var kind: int = Kind.IGNORED
	var from: int = Phase.Wake.WAKING
	var to: int = Phase.Wake.WAKING

	static func advanced(from_phase: int, to_phase: int) -> Phase.Transition:
		var transition: Phase.Transition = Phase.Transition.new()
		transition.kind = Kind.ADVANCED
		transition.from = from_phase
		transition.to = to_phase
		return transition

	static func already_delivered() -> Phase.Transition:
		var transition: Phase.Transition = Phase.Transition.new()
		transition.kind = Kind.ALREADY_DELIVERED
		return transition

	static func ignored() -> Phase.Transition:
		var transition: Phase.Transition = Phase.Transition.new()
		transition.kind = Kind.IGNORED
		return transition

	func equals(other: Phase.Transition) -> bool:
		return other != null and kind == other.kind and from == other.from and to == other.to

class PhaseError:
	extends RefCounted

	var current: int = Phase.Wake.WAKING

	static func get_up_before_exiting_pod(phase: int) -> Phase.PhaseError:
		var error: Phase.PhaseError = Phase.PhaseError.new()
		error.current = phase
		return error

	func equals(other: Phase.PhaseError) -> bool:
		return other != null and current == other.current

	func _to_string() -> String:
		return "get-up-complete signaled in phase %s: the get-up has not started, the skip is rejected, and the phase is unchanged" % Phase.phase_name(current)

class Result:
	extends RefCounted

	var transition: Phase.Transition = null
	var error: Phase.PhaseError = null

	static func with_transition(outcome: Phase.Transition) -> Phase.Result:
		var result: Phase.Result = Phase.Result.new()
		result.transition = outcome
		return result

	static func with_error(failure: Phase.PhaseError) -> Phase.Result:
		var result: Phase.Result = Phase.Result.new()
		result.error = failure
		return result

	func is_ok() -> bool:
		return error == null

class Machine:
	extends RefCounted
	## The enum value plus its transition methods. Spawns in Waking; the
	## initial-phase constructor argument stands in for Rust's direct enum
	## value construction.

	var _phase: int = Phase.Wake.WAKING

	func _init(initial: int = Phase.Wake.WAKING) -> void:
		_phase = initial

	func current() -> int:
		return _phase

	func in_phase(candidate: int) -> bool:
		return Phase.in_phase(_phase, candidate)

	func look_allowed() -> bool:
		return Phase.look_allowed(_phase)

	func locomotion_allowed() -> bool:
		return Phase.locomotion_allowed(_phase)

	func wake_complete() -> Phase.Transition:
		if _phase == Phase.Wake.WAKING:
			return _advance_to(Phase.Wake.AWAKE_IN_POD)
		return Phase.Transition.already_delivered()

	func request_pod_exit(edge: int) -> Phase.Transition:
		if _phase == Phase.Wake.AWAKE_IN_POD and edge == Phase.InputEdge.RISING:
			return _advance_to(Phase.Wake.EXITING_POD)
		return Phase.Transition.ignored()

	func get_up_complete() -> Phase.Result:
		match _phase:
			Phase.Wake.EXITING_POD:
				return Phase.Result.with_transition(_advance_to(Phase.Wake.STANDING))
			Phase.Wake.STANDING:
				return Phase.Result.with_transition(Phase.Transition.already_delivered())
			_:
				return Phase.Result.with_error(Phase.PhaseError.get_up_before_exiting_pod(_phase))

	func _advance_to(next: int) -> Phase.Transition:
		var transition: Phase.Transition = Phase.Transition.advanced(_phase, next)
		_phase = next
		return transition
