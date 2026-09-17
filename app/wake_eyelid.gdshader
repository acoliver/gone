// The wake eyelid full-screen pass, ported from gone_app's
// wake_eyelid.wgsl: opaque upper and lower lids closing over the frame
// from the center outward (a lens-shaped slit, not a straight band), a
// blur whose radius follows the authored smear, and the dark-to-neutral
// exposure ramp shaping the light through the slit. Drawn as a full-screen
// ColorRect in a top CanvasLayer reading the finished frame through
// hint_screen_texture, so it composites over the 3D view's presented
// image. Authored lid and floor colors are display-space values.
shader_type canvas_item;

uniform sampler2D screen_texture : hint_screen_texture, repeat_disable, filter_linear;

// 0 fully shut, 1 fully open (the sim's lid openness).
uniform float lid_openness : hint_range(0.0, 1.0) = 1.0;
// 0 sharp, 1 fully smeared (the sim's blur).
uniform float blur : hint_range(0.0, 1.0) = 0.0;
// 0 the authored dark floor, 1 neutral (the sim's exposure ramp).
uniform float exposure_ramp : hint_range(0.0, 1.0) = 1.0;

// The closed-eye presentation: a dark warm gray, deliberately not black,
// so the closed screen still carries signal.
const vec3 LID_COLOR = vec3(0.020, 0.012, 0.010);

// The light through the slit at exposure ramp zero: the authored dark
// floor the ramp rises from, a touch deeper than the lid color.
const vec3 RAMP_FLOOR = vec3(0.008, 0.005, 0.004);

// Half-width of the soft lid edge in screen-v units; the aperture math
// retracts the lids one band beyond the screen so full openness leaves
// no residue.
const float LID_SOFT = 0.045;

// How far the lid corners droop into the aperture at the screen's left
// and right edges: a lens-shaped slit.
const float LID_ARC = 0.030;

const float GOLDEN_ANGLE = 2.399963229728653;

// The blurred frame color: a golden-angle spiral of taps whose radius
// grows with the authored blur. Zero blur is the single tap.
vec3 blurred_color(vec2 uv) {
	vec3 sum = textureLod(screen_texture, uv, 0.0).rgb;
	if (blur < 1e-4) {
		return sum;
	}
	vec2 dims = vec2(textureSize(screen_texture, 0));
	float radius = blur * 0.02 * min(dims.x, dims.y);
	for (int tap = 1; tap < 9; tap++) {
		float angle = GOLDEN_ANGLE * float(tap);
		vec2 offset = vec2(cos(angle), sin(angle)) * (radius * sqrt(float(tap)) / sqrt(9.0));
		sum += textureLod(screen_texture, uv + offset / dims, 0.0).rgb;
	}
	return sum / 9.0;
}

// Coverage of the two eyelids at this pixel: 0 fully revealed, 1 fully
// covered. The slit's half-height retracts from -LID_SOFT (lids overlapped
// past center, fully shut) to 0.5 + LID_SOFT + LID_ARC (retracted past the
// screen edges, no residue at full openness).
float lid_coverage(vec2 uv) {
	float x = uv.x - 0.5;
	float y = uv.y - 0.5;
	float droop = LID_ARC * (4.0 * x * x);
	float h = mix(-LID_SOFT, 0.5 + LID_SOFT + LID_ARC, lid_openness);
	float edge_top = -h + droop;
	float edge_bottom = h - droop;
	float cover_top = 1.0 - smoothstep(edge_top, edge_top + LID_SOFT, y);
	float cover_bottom = smoothstep(edge_bottom - LID_SOFT, edge_bottom, y);
	return max(cover_top, cover_bottom);
}

void fragment() {
	vec2 uv = SCREEN_UV;
	vec3 scene = mix(RAMP_FLOOR, blurred_color(uv), exposure_ramp);
	vec3 color = mix(scene, LID_COLOR, lid_coverage(uv));
	COLOR = vec4(color, 1.0);
}
