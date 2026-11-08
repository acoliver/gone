extends "res://tools/quarters_pilot_preview.gd"
## Keep the matched pilot views, adding an isolated physical-runoff control.

func _capture(name: String) -> void:
	await super._capture(name)
	if name == "aged-albedo-front.png":
		_diagnostic(6)
		await super._capture("aged-streakmask-front.png")
		_diagnostic(1)
