// Soft ceiling-smoke puffs for the particle draw pass, the visual
// half of issue #33: each particle is a square quad, and the fragment
// shader composes two seed-placed radial lobes so each puff reads as
// an individual billow instead of averaging into a veil. Both
// falloffs reach exactly zero at UV radius PUFF_RADIUS from their lobe
// center; the lobe offsets at most LOBE_MAX per component, so the
// nearest a lobe center can sit to the quad boundary is
// 0.5 - sqrt(2) * LOBE_MAX = 0.316 > PUFF_RADIUS — no square
// silhouette can survive, even corner-on. Per-particle variety comes
// from INSTANCE_ID hashes (flip, lobe placement, rotation direction,
// wobble phase) layered on the emitter's own scale spread; lifetime
// bloom/dissolve reads the process material's phase. Godot 4.7
// dropped the billboard render modes, so the vertex stage builds the
// camera-facing quad by hand (view-plane layout at the particle
// origin, keeping the instance transform's scale, discarding its
// rotation). Alpha blended, no depth write, lit (not unshaded) so the
// red emergency fixtures shade the haze; churn stays cheap: two
// lengths, a rotation, and a couple of smoothsteps per fragment.
shader_type spatial;
render_mode blend_mix, depth_draw_never, cull_disabled, diffuse_lambert, specular_disabled, skip_vertex_transform;

// Lit translucent grey with a red emission glint: reads under the
// emergency fixtures without becoming a light source. Authored values
// live in app/hazards.gd.
uniform vec4 tint : source_color = vec4(0.22, 0.21, 0.21, 1.0);
uniform vec4 emission_tint : source_color = vec4(0.05, 0.0, 0.0, 1.0);
uniform float opacity : hint_range(0.0, 1.0) = 0.48;

// Each lobe's falloff reaches zero at this UV radius from the lobe
// center. The quad half-edge is 0.5; see the header for the
// boundary-safety margin.
const float PUFF_RADIUS = 0.30;
// Lobe center offsets per component; 0.13 keeps |lobe| <= 0.184.
const float LOBE_MAX = 0.13;
// Slow churn: UV rotation in rad/s and alpha wobble in Hz.
const float CHURN_RATE = 0.22;
const float WOBBLE_RATE = 0.13;

varying float seed;
varying float phase;

// Integer hash to [0, 1): stable per particle slot.
float hash1(int id) {
	return fract(sin(float(id) * 78.233) * 43758.5453);
}

void vertex() {
	seed = hash1(INSTANCE_ID);
	phase = clamp(INSTANCE_CUSTOM.y, 0.0, 1.0);
	// Manual particle billboard: the quad's own XY size rides the
	// instance scale, laid out flat in the view plane at the particle's
	// translated origin; the normal faces the camera down view -Z.
	vec3 origin = (MODELVIEW_MATRIX * vec4(vec3(0.0), 1.0)).xyz;
	float sx = length(MODELVIEW_MATRIX[0].xyz);
	float sy = length(MODELVIEW_MATRIX[1].xyz);
	VERTEX = origin + vec3(VERTEX.x * sx, VERTEX.y * sy, 0.0);
	NORMAL = vec3(0.0, 0.0, -1.0);
}

void fragment() {
	vec2 p = UV - 0.5;
	// Half the puffs mirror; the lobes are asymmetric, so flips read.
	if (seed > 0.5) {
		p.x = -p.x;
	}
	float angle = seed * TAU + TIME * CHURN_RATE * sign(seed - 0.25);
	float cs = cos(angle);
	float sn = sin(angle);
	p = vec2(cs * p.x - sn * p.y, sn * p.x + cs * p.y);
	// Two seed-placed lobe centers, one either side of the quad center:
	// every component offsets at most LOBE_MAX, so the boundary-safety
	// margin in the header holds for both.
	vec2 lobe_a = -mix(vec2(0.05), vec2(LOBE_MAX), fract(seed * 7.31));
	vec2 lobe_b = mix(vec2(0.05), vec2(LOBE_MAX), fract(seed * 3.97));
	float puff = max(
		1.0 - smoothstep(0.0, PUFF_RADIUS, length(p - lobe_a)),
		1.0 - smoothstep(0.0, PUFF_RADIUS, length(p - lobe_b))
	);
	// Bloom in, dissolve out over the lifetime, floored so a degenerate
	// phase can never blank the haze.
	float bloom = mix(0.25, smoothstep(0.0, 0.22, phase) * (1.0 - smoothstep(0.72, 1.0, phase)), 0.75);
	float wobble = 0.8 + 0.2 * sin(TAU * WOBBLE_RATE * TIME + seed * TAU);
	ALPHA = puff * bloom * wobble * opacity;
	ALBEDO = tint.rgb;
	EMISSION = emission_tint.rgb;
	ROUGHNESS = 1.0;
}
