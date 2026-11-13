uniform vec4 base_colour : source_color = vec4(1.0);
uniform sampler2D albedo_texture : source_color, filter_linear_mipmap, repeat_enable;
uniform sampler2D normal_texture : hint_normal, filter_linear_mipmap, repeat_enable;
uniform bool has_albedo = false;
uniform bool has_normal = false;
uniform bool vertex_colour = false;
uniform float normal_scale = 1.0;
uniform float metallic = 0.0;
uniform float roughness = 0.97;
uniform float specular = 0.12;
uniform float alpha_cutoff = 0.5;
uniform vec3 pigment_gain = vec3(1.0);

vec4 tunic_base(vec2 uv, vec4 vertex) {
	vec4 base = base_colour;
	if (has_albedo) base *= texture(albedo_texture, uv);
	if (vertex_colour) base *= vertex;
	return base;
}

uniform bool contact_enabled = false;
uniform sampler2D contact_texture : filter_linear_mipmap, repeat_disable;
uniform vec4 contact_x;
uniform vec4 contact_height;
uniform vec4 contact_depth;
uniform float contact_light_affect = 0.35;
varying vec3 contact_position;
varying float contact_facing;

void vertex() {
	contact_position = vec3(dot(vec4(VERTEX, 1.0), contact_x), dot(vec4(VERTEX, 1.0), contact_height), dot(vec4(VERTEX, 1.0), contact_depth));
	contact_facing = dot(NORMAL, -contact_depth.xyz);
}

float tunic_contact_ao() {
	if (!contact_enabled || contact_facing < 0.2) return 1.0;
	vec2 uv = (contact_position.xy + vec2(0.024)) / vec2(0.048, 0.056);
	if (any(lessThan(uv, vec2(0.0))) || any(greaterThan(uv, vec2(1.0)))) return 1.0;
	// The Blender patch starts at its bottom row; standalone PNG sampling starts at the top.
	uv.y = 1.0 - uv.y;
	vec3 mask = texture(contact_texture, uv).rgb;
	float depth = (mask.g - 0.5) * 0.02;
	if (mask.b < 0.99 || abs(contact_position.z - depth) > 0.00035) return 1.0;
	return mask.r;
}
