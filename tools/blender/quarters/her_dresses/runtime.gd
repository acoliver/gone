extends SceneTree
## Check the imported dress surfaces without changing demo materials.

func _initialize() -> void:
	for state: String in ["remembered", "aged"]:
		var path := "res://assets/props/quarters/her_dresses" + ("_aged" if state == "aged" else "") + ".glb"
		var garment := (load(path) as PackedScene).instantiate() as Node3D
		assert(garment.transform == Transform3D.IDENTITY)
		var triangles := 0
		var masked := 0
		for node: MeshInstance3D in garment.find_children("*", "MeshInstance3D", true, false):
			for surface: int in range(node.mesh.get_surface_count()):
				var material := node.get_active_material(surface) as StandardMaterial3D
				assert(material != null and material.cull_mode == BaseMaterial3D.CULL_BACK, "explicit-sided dress surfaces")
				if material.transparency == BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR: masked += 1
				triangles += int(node.mesh.surface_get_array_index_len(surface) / 3)
		assert(triangles <= 10000)
		if state == "aged": assert(masked >= 4, "fringe and powder import as alpha-scissor surfaces")
		print("DRESS_RUNTIME state=%s triangles=%d masked_surfaces=%d cull_back=true identity_root=true" % [state, triangles, masked])
		garment.free()
	quit()
