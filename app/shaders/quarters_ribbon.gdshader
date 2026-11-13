shader_type spatial;
render_mode cull_disabled, diffuse_burley, specular_schlick_ggx;

uniform sampler2D albedo_texture : source_color, filter_linear_mipmap, repeat_enable;
uniform vec4 base_colour : source_color = vec4(1.0);
uniform sampler2D weave_normal : hint_normal, filter_linear_mipmap, repeat_enable;
uniform sampler2D weave_roughness : filter_linear_mipmap, repeat_enable;
uniform vec2 weave_scale = vec2(1.0);
uniform vec2 weave_offset = vec2(0.0);
uniform bool aged = false;
uniform bool weave_enabled = true;

void fragment() {
	vec2 weave_uv = UV * weave_scale + weave_offset;
	vec3 fibre = weave_enabled ? mix(vec3(0.97), texture(albedo_texture, weave_uv).rgb, 0.75) : vec3(0.97);
	vec3 pigment = base_colour.rgb * COLOR.rgb * fibre;
	float grey = dot(pigment, vec3(0.2126, 0.7152, 0.0722));
	ALBEDO = aged ? mix(pigment, vec3(grey), 0.16) * 0.82 : pigment * 0.92;
	vec2 xy = weave_enabled ? texture(weave_normal, weave_uv).rg * 2.0 - 1.0 : vec2(0.0);
	xy *= 0.8;
	NORMAL_MAP = vec3(xy, sqrt(max(0.0, 1.0 - dot(xy, xy)))) * 0.5 + 0.5;
	float fibre_roughness = mix(texture(weave_roughness, weave_uv).g,
		texture(weave_roughness, weave_uv * vec2(0.11, 0.071) + vec2(0.0, 0.8)).g, 0.8);
	ROUGHNESS = (weave_enabled ? fibre_roughness : 0.52) + (aged ? 0.07 : 0.0);
	float fibre_visibility = mix(0.35, 0.65, 1.0 - fibre_roughness);
	METALLIC = 0.0;
	SPECULAR = 0.4;
	ANISOTROPY = weave_enabled ? 0.38 : 0.0;
	ANISOTROPY_FLOW = vec2(1.0, 0.0);
	RIM = 0.08;
	RIM_TINT = 0.6;
	SPECULAR *= fibre_visibility;
	ANISOTROPY *= fibre_visibility;
	RIM *= fibre_visibility;
}
