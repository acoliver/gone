extends RefCounted
## Opt-in GI experiment. No source, exposure, material or ambient-energy changes.

const ENVIRONMENT_VARIABLE := "GONE_REAL_BOUNCE"

static func configure(environment: Environment, mode: String) -> void:
	assert(mode in ["", "sdfgi", "ssil"], "GONE_REAL_BOUNCE must be empty, sdfgi or ssil")
	if mode == "sdfgi":
		environment.sdfgi_enabled = true
		environment.sdfgi_read_sky_light = false
		environment.sdfgi_cascades = 4
		environment.sdfgi_min_cell_size = 0.1
		environment.sdfgi_use_occlusion = true
		environment.sdfgi_energy = 1.0
	elif mode == "ssil":
		environment.ssil_enabled = true
		environment.ssil_intensity = 1.0
		environment.ssil_radius = 5.0

static func prepare_geometry(root: Node, mode: String) -> void:
	if mode != "sdfgi": return
	for mesh: MeshInstance3D in root.find_children("*", "MeshInstance3D", true, false):
		for surface: int in range(mesh.mesh.get_surface_count()):
			var material := mesh.get_active_material(surface) as BaseMaterial3D
			# Fixtures already have a real Light3D. Do not inject their lens emission again.
			if material != null and material.emission_enabled:
				mesh.gi_mode = GeometryInstance3D.GI_MODE_DISABLED
	# Refresh live instance registration after off-tree procedural assembly.
	for light: Light3D in root.find_children("*", "Light3D", true, false):
		if light.visible:
			light.call_deferred("hide")
			light.call_deferred("show")
