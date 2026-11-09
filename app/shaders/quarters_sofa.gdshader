shader_type spatial;
render_mode cull_disabled;
#include "steel_sampling.gdshaderinc"

uniform sampler2D albedo_a : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D albedo_b : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D albedo_c : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform bool aged_finish = false;
uniform sampler2D baked_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_disable;
uniform sampler2D baked_nodust : source_color, filter_linear_mipmap_anisotropic, repeat_disable;
uniform sampler2D baked_normal : hint_normal, filter_linear_mipmap_anisotropic, repeat_disable;
uniform sampler2D baked_orm : filter_linear_mipmap_anisotropic, repeat_disable;
uniform sampler2D baked_masks : filter_linear_mipmap_anisotropic, repeat_disable;
uniform sampler2D weave : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform bool dust_enabled = true;
uniform int diagnostic = 0;
uniform bool diagnostic_door = false;
varying vec3 surface_position;
varying vec3 surface_normal;

void vertex() {
	surface_position = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	surface_normal = normalize(MODEL_NORMAL_MATRIX * NORMAL);
}

void fragment() {
	vec4 colour = texture(baked_albedo, UV);
	if (!dust_enabled) { colour = texture(baked_nodust, UV); }
	vec3 orm = texture(baked_orm, UV).rgb;
	vec4 masks = texture(baked_masks, UV);
	vec3 detail = texture(baked_normal, UV).rgb;
	if (masks.a < 0.4) {
		vec3 weights = pow(abs(normalize(surface_normal)), vec3(4.0));
		weights /= dot(weights, vec3(1.0));
		vec3 p = surface_position / 0.12;
		float yarn = dot(texture(weave, p.yz).rgb, vec3(0.3333)) * weights.x
			+ dot(texture(weave, p.xz).rgb, vec3(0.3333)) * weights.y
			+ dot(texture(weave, p.xy).rgb, vec3(0.3333)) * weights.z;
		colour.rgb *= 0.88 + 0.30 * yarn;
		detail.xy += vec2(dFdx(yarn), -dFdy(yarn)) * 0.80;
	}
	ALBEDO = colour.rgb;
	ALPHA = colour.a;
	ALPHA_SCISSOR_THRESHOLD = 0.5;
	NORMAL_MAP = detail;
	ROUGHNESS = orm.g;
	METALLIC = orm.b;
	AO = orm.r;
	AO_LIGHT_AFFECT = 0.65;
	if (masks.a > 0.6) {
		vec3 n = normalize(surface_normal);
		vec3 weights = pow(abs(n), vec3(4.0));
		weights /= dot(weights, vec3(1.0));
		vec3 signs = mix(vec3(-1.0), vec3(1.0), step(vec3(0.0), n));
		vec3 steel = scan_sample(albedo_a, surface_position, signs, weights, 0.20, vec2(0.0));
		vec3 paint = scan_sample(albedo_b, surface_position, signs, weights, 0.20, vec2(0.0));
		vec3 oxide = scan_sample(albedo_c, surface_position, signs, weights, 0.20, vec2(0.0));
		vec3 scan = aged_finish ? oxide : (masks.a > 0.8 ? steel : paint);
		float grain = clamp(dot(scan, vec3(0.2126, 0.7152, 0.0722)) * 3.0, 0.0, 1.0);
		ALBEDO *= 0.97 + grain * 0.06;
	}
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
