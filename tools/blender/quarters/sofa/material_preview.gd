extends "res://tools/quarters_pilot_preview.gd"

func _camera(angle: String) -> void:
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = 2.8
	match angle:
		"hero": camera.position = Vector3(3.1, 2.2, 3.5)
		"front": camera.position = Vector3(0, .55, 4.0)
		"top":
			camera.position = Vector3(-.4, 2.4, 1.4)
			camera.size = 2.55
		"detail", "streaks":
			camera.projection = Camera3D.PROJECTION_PERSPECTIVE
			camera.fov = 43.6028
			camera.position = _target(angle) + Vector3(-.18, .28, .50).normalized() * .6
	camera.look_at(_target(angle), Vector3.UP)

func _target(angle: String) -> Vector3:
	match angle:
		"detail": return Vector3(-.18, .46, .29)
		"streaks": return Vector3(1.05, .50, .18)
		_: return Vector3(0, .43, 0)
