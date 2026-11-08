extends "res://tools/quarters_pilot_preview.gd"
## Keep the matched pilot views, adding an isolated physical-runoff control.

func _capture(name: String) -> void:
	await super._capture(name)
	if name in ["aged-albedo-front.png", "aged-albedo-streaks.png"]:
		_diagnostic(6)
		await super._capture(name.replace("albedo", "streakmask"))
		_diagnostic(1)
	if name == "aged-neutral-streaks.png":
		var pose := camera.transform
		var size := camera.size
		camera.position = Vector3(-0.015, 1.075, 0.600)
		camera.look_at(Vector3(-0.015, 1.075, 0.300), Vector3.UP)
		camera.size = 0.64
		await super._capture("closeup-hinge.png")
		camera.transform = pose
		camera.size = size
