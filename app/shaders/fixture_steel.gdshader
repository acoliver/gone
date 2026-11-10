shader_type spatial;
render_mode cull_back;
uniform bool weathering_enabled = true;
uniform sampler3D grime_noise : repeat_enable, filter_linear;
varying vec3 fixture_position;
varying vec3 fixture_normal;
float noise(vec3 p) { return texture(grime_noise, p / 64.0).r; }
void vertex() {
	fixture_position = VERTEX;
	fixture_normal = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}
void fragment() {
	vec3 p = fixture_position;
	vec3 steel = vec3(0.105, 0.095, 0.078);
	float rough = 0.65;
	float oxide = 0.0;
	if (weathering_enabled) {
		float grain = noise(p * 290.0);
		float patch = noise(p * 47.0) * 0.65 + noise(p * 113.0) * 0.35;
		// Front rods and their welded ends collect more oxide than broad housing faces.
		float rods = smoothstep(0.20, 0.25, -p.z);
		float rim = smoothstep(0.10, 0.145, abs(p.x)) + smoothstep(0.075, 0.12, abs(p.y));
		oxide = smoothstep(0.38, 0.69, patch + min(1.0, rods + rim) * 0.26);
		vec3 rust = mix(vec3(0.065, 0.023, 0.008), vec3(0.30, 0.115, 0.035), grain);
		steel = mix(steel * mix(0.38, 1.05, patch), rust, oxide * 0.92);
		float grime = smoothstep(0.46, 0.73, noise(p * vec3(83.0, 14.0, 61.0)));
		steel *= mix(1.0, 0.28, grime);
		float dust = smoothstep(0.18, 0.7, fixture_normal.y) * (0.32 + 0.55 * noise(p * 67.0));
		steel = mix(steel, vec3(0.26, 0.225, 0.17), dust);
		rough = mix(0.86, 1.0, max(dust, oxide));
	}
	ALBEDO = steel;
	METALLIC = weathering_enabled ? 0.12 * (1.0 - oxide) : 0.55;
	ROUGHNESS = rough;
	SPECULAR = 0.2;
}
