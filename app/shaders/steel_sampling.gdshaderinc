// Signed projection bases keep OpenGL normal-map Y and reverse faces consistent.
vec2 plane_uv(vec3 p, vec3 signs, int axis) {
    if (axis == 0) { return vec2(-p.z * signs.x, p.y); }
    if (axis == 1) { return vec2(p.x, -p.z * signs.y); }
    return vec2(p.x * signs.z, p.y);
}
vec3 scan_sample(sampler2D map, vec3 p, vec3 signs, vec3 weights, float pitch, vec2 offset) {
    vec3 value = vec3(0.0);
    if (weights.x > 0.0) { value += texture(map, plane_uv(p, signs, 0) / pitch + offset).rgb * weights.x; }
    if (weights.y > 0.0) { value += texture(map, plane_uv(p, signs, 1) / pitch + offset).rgb * weights.y; }
    if (weights.z > 0.0) { value += texture(map, plane_uv(p, signs, 2) / pitch + offset).rgb * weights.z; }
    return value;
}
vec3 bc5_normal(vec2 xy) {
    xy = xy * 2.0 - 1.0;
    return vec3(xy, sqrt(max(0.0, 1.0 - dot(xy, xy))));
}
vec3 scan_normal(sampler2D map, vec3 p, vec3 signs, vec3 weights, float pitch, vec2 offset) {
    vec3 value = vec3(0.0);
    if (weights.x > 0.0) {
        vec3 v = bc5_normal(texture(map, plane_uv(p, signs, 0) / pitch + offset).rg);
        value += vec3(0.0, v.y, -v.x * signs.x) * weights.x;
    }
    if (weights.y > 0.0) {
        vec3 v = bc5_normal(texture(map, plane_uv(p, signs, 1) / pitch + offset).rg);
        value += vec3(v.x, 0.0, -v.y * signs.y) * weights.y;
    }
    if (weights.z > 0.0) {
        vec3 v = bc5_normal(texture(map, plane_uv(p, signs, 2) / pitch + offset).rg);
        value += vec3(v.x * signs.z, v.y, 0.0) * weights.z;
    }
    return value;
}
