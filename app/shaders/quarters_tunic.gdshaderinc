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
