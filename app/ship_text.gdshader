shader_type spatial;
render_mode unshaded, cull_back, shadows_disabled;

uniform sampler2D native_ink : filter_linear, repeat_disable;
uniform sampler2D perceived_ink : filter_linear, repeat_disable;
uniform float perceive : hint_range(0.0, 1.0) = 0.0;

float blurred_alpha(sampler2D ink, vec2 uv, float radius) {
	vec2 step_uv = vec2(radius) / vec2(textureSize(ink, 0));
	float alpha = texture(ink, uv).a * 0.25;
	alpha += texture(ink, uv + vec2(step_uv.x, 0.0)).a * 0.125;
	alpha += texture(ink, uv - vec2(step_uv.x, 0.0)).a * 0.125;
	alpha += texture(ink, uv + vec2(0.0, step_uv.y)).a * 0.125;
	alpha += texture(ink, uv - vec2(0.0, step_uv.y)).a * 0.125;
	alpha += texture(ink, uv + step_uv).a * 0.0625;
	alpha += texture(ink, uv - step_uv).a * 0.0625;
	alpha += texture(ink, uv + vec2(step_uv.x, -step_uv.y)).a * 0.0625;
	alpha += texture(ink, uv + vec2(-step_uv.x, step_uv.y)).a * 0.0625;
	return alpha;
}

void fragment() {
	float native_alpha = blurred_alpha(native_ink, UV, perceive * 12.0);
	float spanish_alpha = blurred_alpha(perceived_ink, UV, (1.0 - perceive) * 12.0);
	ALBEDO = vec3(0.0);
	EMISSION = vec3(0.85, 0.95, 1.0) * 1.3;
	ALPHA = mix(native_alpha, spanish_alpha, perceive);
}
