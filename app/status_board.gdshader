shader_type spatial;
render_mode unshaded, cull_disabled;

uniform sampler2D native_board : source_color, filter_linear;
uniform sampler2D perceived_board : source_color, filter_linear;
uniform float perceive : hint_range(0.0, 1.0) = 0.0;

void fragment() {
	vec4 native_ink = texture(native_board, UV);
	vec4 perceived_ink = texture(perceived_board, UV);
	ALBEDO = mix(native_ink.rgb, perceived_ink.rgb, perceive);
	EMISSION = ALBEDO;
	ALPHA = mix(native_ink.a, perceived_ink.a, perceive);
}
