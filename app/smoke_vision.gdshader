shader_type canvas_item;

uniform float dose : hint_range(0.0, 1.0) = 0.0;
uniform float cough_pulse : hint_range(0.0, 1.0) = 0.0;
uniform float breath_pulse : hint_range(0.0, 1.0) = 0.0;
uniform vec2 viewport_size = vec2(2304.0, 1296.0);
uniform sampler2D screen_texture : hint_screen_texture, filter_linear_mipmap;

void fragment() {
	vec2 uv = SCREEN_UV;
	vec2 centered = (uv - vec2(0.5)) * vec2(viewport_size.x / viewport_size.y, 1.0);
	float radius = length(centered);
	float peripheral = smoothstep(0.52, 0.95, radius);
	float severity = clamp(dose, 0.0, 1.0);
	float radial = peripheral * severity;
	vec2 offset = normalize(centered + vec2(0.00001)) * radial * (2.0 / viewport_size);
	vec4 center = texture(screen_texture, uv);
	vec4 ghost = texture(screen_texture, uv - offset);
	vec3 color = mix(center.rgb, ghost.rgb, radial * 0.08);
	float blur_pixels = radial * 4.0;
	vec2 px = vec2(blur_pixels) / viewport_size;
	color = mix(color, texture(screen_texture, uv + vec2(px.x, 0.0)).rgb, radial * 0.18);
	float gray = dot(color, vec3(0.2126, 0.7152, 0.0722));
	color = mix(color, vec3(gray), radial * 0.72);
	color *= 1.0 - radial * 0.12;
	color += vec3(0.035) * radial;
	// Mixing, rather than multiplying, lets a bounded cue register on dark pixels.
	float haze = peripheral * (cough_pulse * 0.26 + breath_pulse * 0.14);
	color = mix(color, vec3(0.32, 0.38, 0.42), haze);
	COLOR = vec4(color, 1.0);
}
