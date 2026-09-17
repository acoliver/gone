class_name Power
extends RefCounted
## Ship power state for the emergency-lit stasis bay, ported from gone_sim
## power.rs. The bay runs on emergency cells or nothing: Emergency (red
## emergency fixtures lit) and Dead (dark). The grid starts on emergency
## power, the story layer is the only authority that changes it, and the
## single transition cut_emergency_power is idempotent. There is
## deliberately no normal-lighting state. Pure data: no clocks, no RNG,
## no render types.

enum State { EMERGENCY, DEAD }

## Whether the red emergency fixtures are lit in this state: true only in
## Emergency. The single lighting-meaningful query the sim ships.
static func emergency_fixtures_lit(state: int) -> bool:
	return state == State.EMERGENCY

class Transition:
	extends RefCounted

	enum Kind { ADVANCED, UNCHANGED }

	var kind: int = Kind.UNCHANGED
	var from: int = Power.State.EMERGENCY
	var to: int = Power.State.EMERGENCY
	var current: int = Power.State.EMERGENCY

	static func advanced(from_state: int, to_state: int) -> Power.Transition:
		var transition: Power.Transition = Power.Transition.new()
		transition.kind = Kind.ADVANCED
		transition.from = from_state
		transition.to = to_state
		return transition

	static func unchanged(present: int) -> Power.Transition:
		var transition: Power.Transition = Power.Transition.new()
		transition.kind = Kind.UNCHANGED
		transition.current = present
		return transition

	func equals(other: Power.Transition) -> bool:
		if other == null or kind != other.kind:
			return false
		match kind:
			Kind.ADVANCED:
				return from == other.from and to == other.to
			_:
				return current == other.current

class Grid:
	extends RefCounted
	## The authoritative power machine. Constructed only on the opening
	## beat's emergency-powered bay; the state changes only through
	## cut_emergency_power.

	var _state: int = Power.State.EMERGENCY

	func state() -> int:
		return _state

	## Consume one cut-the-emergency-cells story event. In Emergency this
	## advances to Dead; in Dead the event is already delivered and the
	## outcome is the no-op Unchanged.
	func cut_emergency_power() -> Power.Transition:
		match _state:
			Power.State.EMERGENCY:
				_state = Power.State.DEAD
				return Power.Transition.advanced(Power.State.EMERGENCY, Power.State.DEAD)
			_:
				return Power.Transition.unchanged(Power.State.DEAD)

	## Rust grids are Copy; the reachability walk copies one before
	## applying an event to it.
	func copy() -> Power.Grid:
		var duplicate: Power.Grid = Power.Grid.new()
		duplicate._state = _state
		return duplicate

	func equals(other: Power.Grid) -> bool:
		return other != null and _state == other._state
