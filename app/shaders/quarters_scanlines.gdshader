shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_never, shadows_disabled;

void fragment() {
	ALBEDO = vec3(0.0);
	ALPHA = step(0.7, fract(UV.y * 72.0)) * 0.14;
}
