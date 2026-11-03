class_name BayVentilation
extends RefCounted
## Fixed-tick air clearing on the secondary bus. GameStep is the only clock.

const CLEAR_TICKS: int = 8 * 60
var _elapsed: int = 0

func tick(secondary_active: bool) -> void:
	if secondary_active:
		_elapsed = mini(_elapsed + 1, CLEAR_TICKS)

func density() -> float:
	return 1.0 - float(_elapsed) / float(CLEAR_TICKS)

func clearing() -> bool:
	return _elapsed > 0 and _elapsed < CLEAR_TICKS

func started() -> bool:
	return _elapsed > 0

func elapsed_secs() -> float:
	return float(_elapsed) * Sim.LOGICAL_TICK_SECS
