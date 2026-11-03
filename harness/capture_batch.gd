class_name CaptureBatch
extends RefCounted
## Yield presentation at capture, residency, raster and terminal boundaries.

static func advance(limit: int, step: Callable, boundary: Callable) -> int:
	var count := 0
	while count < limit and not boundary.call():
		step.call()
		count += 1
	return count
