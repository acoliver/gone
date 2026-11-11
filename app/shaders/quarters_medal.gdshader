shader_type spatial;
render_mode diffuse_burley, specular_schlick_ggx;

uniform vec4 base_colour : source_color = vec4(1.0);
uniform sampler2D albedo_texture : source_color, filter_linear_mipmap, repeat_disable;
uniform sampler2D normal_texture : hint_normal, filter_linear_mipmap, repeat_disable;
uniform sampler2D orm_texture : filter_linear_mipmap, repeat_disable;
uniform bool has_albedo = true;
uniform bool has_normal = true;
uniform float normal_scale = 1.0;
uniform float roughness = 1.0;
uniform float metallic = 1.0;
uniform float specular = 0.5;
uniform float coat = 0.0;
uniform float coat_roughness = 0.13;
uniform float ao_light_affect = 0.2;
uniform bool vertex_colour = false;
uniform bool flat_normal = false;
uniform bool rough_enamel = false;
uniform int diagnostic = 0;

void fragment() {
	vec4 base = base_colour * (has_albedo ? texture(albedo_texture, UV) : vec4(1.0));
	vec3 orm = texture(orm_texture, UV).rgb;
	vec2 xy = texture(normal_texture, UV).rg * 2.0 - 1.0;
	// Imported normal maps may use BC5. Reconstruct +Z rather than reading its absent B.
	vec3 normal_sample = vec3(xy, sqrt(max(0.0, 1.0 - dot(xy, xy))));
	if (flat_normal || !has_normal) normal_sample = vec3(0.0, 0.0, 1.0);
	ALBEDO = base.rgb;
	NORMAL_MAP = normal_sample * 0.5 + 0.5;
	NORMAL_MAP_DEPTH = normal_scale;
	ROUGHNESS = rough_enamel ? 1.0 : orm.g * roughness;
	METALLIC = orm.b * metallic;
	SPECULAR = specular;
	AO = orm.r;
	AO_LIGHT_AFFECT = ao_light_affect;
	CLEARCOAT = rough_enamel ? 0.0 : coat;
	CLEARCOAT_ROUGHNESS = rough_enamel ? 1.0 : coat_roughness;
	if (diagnostic == 3) {
		ALBEDO = vec3(1.0); METALLIC = 1.0; ROUGHNESS = 0.0; AO = 1.0; CLEARCOAT = 0.0;
	}
	if (diagnostic == 1 || diagnostic == 2) {
		ALBEDO = vec3(0.0);
		METALLIC = 0.0;
		SPECULAR = 0.0;
		CLEARCOAT = 0.0;
		EMISSION = diagnostic == 1 ? (normal_sample * 0.5 + 0.5) : vec3(1.0);
	}
}
