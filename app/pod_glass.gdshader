shader_type spatial;
render_mode blend_premul_alpha, depth_draw_never, cull_disabled,
            specular_schlick_ggx, fog_disabled, specular_occlusion_disabled;

void fragment() {
    vec3 n = normalize(NORMAL);
    vec3 v = normalize(VIEW);
    if (dot(n, v) < 0.0) {
        n = -n;
    }
    NORMAL = n;
    float ndv = clamp(dot(n, v), 0.0, 1.0);
    float fresnel = 0.04 + 0.96 * pow(1.0 - ndv, 5.0);
    float edge_mask = COLOR.r;
    ALBEDO = edge_mask * vec3(0.006, 0.012, 0.010);
    METALLIC = 0.0;
    SPECULAR = 0.5;
    ROUGHNESS = 0.07;
    ALPHA = mix(1.0 - 0.98 * (1.0 - fresnel), 1.0, edge_mask);
    PREMUL_ALPHA_FACTOR = 1.0;
}
