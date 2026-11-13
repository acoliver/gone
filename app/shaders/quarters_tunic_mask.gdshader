shader_type spatial;
render_mode cull_disabled, diffuse_burley, specular_schlick_ggx;
#include "quarters_tunic.gdshaderinc"

void fragment() {
	vec4 base = tunic_base(UV, COLOR);
	ALBEDO = base.rgb * pigment_gain;
	METALLIC = metallic;
	ROUGHNESS = roughness;
	SPECULAR = specular;
	AO = tunic_contact_ao();
	AO_LIGHT_AFFECT = contact_enabled ? contact_light_affect : 0.0;
	if (has_normal) {
		NORMAL_MAP = texture(normal_texture, UV).rgb;
		NORMAL_MAP_DEPTH = normal_scale;
	}

	ALPHA = base.a;
	ALPHA_SCISSOR_THRESHOLD = alpha_cutoff;
}
