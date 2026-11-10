shader_type spatial;
render_mode cull_disabled;

uniform sampler2D baked_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_disable;
uniform sampler2D baked_nodust : source_color, filter_linear_mipmap_anisotropic, repeat_disable;
uniform sampler2D baked_normal : hint_normal, filter_linear_mipmap_anisotropic, repeat_disable;
uniform sampler2D baked_orm : filter_linear_mipmap_anisotropic, repeat_disable;
uniform sampler2D baked_masks : filter_linear_mipmap_anisotropic, repeat_disable;
uniform bool dust_enabled = true;
uniform int diagnostic = 0;
uniform bool diagnostic_door = false;

void fragment() {
	vec4 colour = texture(baked_albedo, UV);
	if (!dust_enabled) { colour = texture(baked_nodust, UV); }
	vec3 orm = texture(baked_orm, UV).rgb;
	vec4 masks = texture(baked_masks, UV);
	ALBEDO = colour.rgb;
	ALPHA = colour.a;
	NORMAL_MAP = texture(baked_normal, UV).rgb;
	ROUGHNESS = orm.g;
	METALLIC = 0.0;
	AO = orm.r;
	AO_LIGHT_AFFECT = 0.65;
	if (diagnostic != 0) {
		vec3 value = colour.rgb;
		if (diagnostic == 2) { value = vec3(1.0, masks.b, 1.0); }
		if (diagnostic == 3) { value = masks.rgb; }
		if (diagnostic == 4) { value = orm; }
		if (diagnostic == 5) { value = vec3(masks.a); }
		ALBEDO = vec3(0.0);
		EMISSION = value;
	}
}
