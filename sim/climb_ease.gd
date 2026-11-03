class_name ClimbEase
extends RefCounted
## Pure scalar response shared by ladder motion and input route compilation.

static func _alpha() -> float:
	return 1.0 - exp(-Controller.INTENT_EASE_EXPONENT * Sim.LOGICAL_TICK_SECS / Controller.CLIMB_EASE_SECONDS)

static func step(velocity: float, intent: float, speed: float) -> float:
	return velocity + (intent * speed - velocity) * _alpha()

static func intent_for_velocity(velocity: float, desired: float, speed: float) -> float:
	var alpha := _alpha()
	return clampf((desired - velocity * (1 - alpha)) / (speed * alpha), -1, 1)
