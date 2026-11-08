shader_type spatial;
render_mode cull_back;
#include "steel_sampling.gdshaderinc"
uniform sampler2D baked_albedo : source_color, repeat_disable, filter_linear_mipmap_anisotropic;
uniform sampler2D baked_normal : hint_normal, repeat_disable, filter_linear_mipmap_anisotropic;
uniform sampler2D baked_orm : repeat_disable, filter_linear_mipmap_anisotropic;
uniform sampler2D baked_dust : source_color, repeat_disable, filter_linear_mipmap_anisotropic;
uniform sampler2D aged_paint : source_color, repeat_disable, filter_linear_mipmap_anisotropic;
uniform sampler2D aged_oxide : source_color, repeat_disable, filter_linear_mipmap_anisotropic;
uniform sampler2D runoff_colour : source_color, repeat_disable, filter_linear_mipmap_anisotropic;
uniform sampler2D weather_masks : repeat_disable, filter_nearest;
uniform sampler2D albedo_a : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D albedo_b : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D albedo_c : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D normal_a : hint_normal, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D normal_b : hint_normal, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D normal_c : hint_normal, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D orm_a : repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D orm_b : repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D orm_c : repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D region_masks : repeat_disable, filter_nearest;
uniform sampler2D streak_sources : repeat_disable, filter_nearest;
uniform bool aged_finish = false;
uniform bool dust_enabled = true;
uniform bool diagnostic_door = false;
uniform int diagnostic = 0;
instance uniform vec4 prop_x = vec4(1, 0, 0, 0);
instance uniform vec4 prop_y = vec4(0, 1, 0, 0);
instance uniform vec4 prop_z = vec4(0, 0, 1, 0);
varying vec3 prop_position;
varying vec3 prop_normal;

void vertex() {
    vec4 p = vec4(VERTEX, 1);
    prop_position = vec3(dot(prop_x, p), dot(prop_y, p), dot(prop_z, p));
    prop_normal = normalize(vec3(dot(prop_x.xyz, NORMAL), dot(prop_y.xyz, NORMAL), dot(prop_z.xyz, NORMAL)));
}

float seeded_profile(float x) {
    float i = floor(x);
    float f = fract(x);
    f = f * f * (3.0 - 2.0 * f);
    return mix(fract(sin(i * 1.61803399) * 43.7585453), fract(sin((i + 1.0) * 1.61803399) * 43.7585453), f) * 2.0 - 1.0;
}

vec4 cubic_weights(float t) {
    float t2 = t * t;
    float t3 = t2 * t;
    return vec4(-t * 0.5 + t2 - t3 * 0.5,
                1.0 - t2 * 2.5 + t3 * 1.5,
                t * 0.5 + t2 * 2.0 - t3 * 1.5,
                -t2 * 0.5 + t3 * 0.5);
}

// Interpolating cubic reconstruction preserves small losses that a smoothing
// spline erodes, without introducing bilinear cell corners when sharpened.
float oxide_field(vec2 uv) {
    vec2 size = vec2(textureSize(baked_albedo, 0));
    vec2 p = uv * size - 0.5;
    vec4 wx = cubic_weights(fract(p.x));
    vec4 wy = cubic_weights(fract(p.y));
    vec2 start = floor(p) - 0.5;
    float field = 0.0;
    for (int y = 0; y < 4; y++) {
        for (int x = 0; x < 4; x++) {
            field += texture(baked_albedo, (start + vec2(float(x), float(y))) / size).a * wx[x] * wy[y];
        }
    }
    return clamp(field, 0.0, 1.0);
}


float gravity_trails(vec3 p, vec3 n) {
    // Derivatives inside the per-source drop branches are undefined at outlets.
    vec3 pixel_span = abs(dFdx(p)) + abs(dFdy(p));
    float coverage = 0.0;
    int count = textureSize(streak_sources, 0).x;
    for (int i = 0; i < count; i++) {
        vec4 source = texelFetch(streak_sources, ivec2(i, 0), 0);
        vec4 shape = texelFetch(streak_sources, ivec2(i, 1), 0);
        float drop = source.y - p.y;
        if (drop < 0.0 || drop > shape.x) { continue; }
        float lateral = 1.0;
        float aa = 0.0002;
        if (abs(n.z) > 0.6 && abs(p.z - source.z) < 0.035) {
            lateral = p.x - source.x;
            aa = max(pixel_span.x, 0.0002);
        } else if (abs(n.x) > 0.6 && abs(p.x - source.x) < 0.035) {
            lateral = p.z - source.z;
            aa = max(pixel_span.z, 0.0002);
        }
        float ragged = seeded_profile(drop * 147.0 + shape.w) * 0.8 + seeded_profile(drop * 337.0 + shape.w + 83.0) * 0.4 + seeded_profile(drop * 499.0 + shape.w + 97.0) * 0.9;
        float taper = pow(1.0 - drop / shape.x, 0.40);
        float radius = (source.w * 0.5 + shape.z * ragged / 2.1) * taper;
        float drift = shape.z * (seeded_profile(drop * 71.0 + shape.w + 31.0) + seeded_profile(drop * 193.0 + shape.w + 7.0) * 0.4 + seeded_profile(drop * 409.0 + shape.w + 53.0) * 0.7);
        lateral = abs(lateral + drift);
        float trail = max(0.0, min(lateral + aa * 0.5, radius) - max(lateral - aa * 0.5, -radius)) / aa;
        trail *= 1.0 - smoothstep(0.35, 1.0, drop / shape.x);
        coverage = max(coverage, trail * shape.y);
    }
    return coverage;
}

void fragment() {
    vec4 colour = texture(baked_albedo, UV);
    vec4 orm = texture(baked_orm, UV);
    float paint = 1.0 - step(0.08, abs(texture(weather_masks, UV).a - 0.25));
    vec3 n = normalize(prop_normal);
    float trail = aged_finish ? gravity_trails(prop_position, n) : 0.0;
    float oxide = max(colour.a, trail);
    vec2 runoff_uv = (prop_position.xy * 300.0 + vec2(180.0, 12.0)) / vec2(textureSize(runoff_colour, 0));
    vec3 runoff = texture(runoff_colour, runoff_uv).rgb;
    vec3 signs = mix(vec3(-1), vec3(1), step(vec3(0), n));
    vec3 weights = pow(abs(n), vec3(4));
    weights /= dot(weights, vec3(1));
    vec3 steel = scan_sample(albedo_a, prop_position, signs, weights, 0.20, vec2(0));
    vec3 painted = scan_sample(albedo_b, prop_position, signs, weights, 0.20, vec2(0));
    vec3 rust = scan_sample(albedo_c, prop_position, signs, weights, 0.20, vec2(0));
    if (aged_finish) {
        // Interpolated coverage locates the boundary. Scan relief breaks its
        // atlas-grid alignment before derivative-width antialiasing.
        float coverage = oxide_field(UV);
        if (paint < 0.5) { coverage = mix(coverage, 0.62, 0.70); }
        float breakup = clamp((dot(rust, vec3(0.2126, 0.7152, 0.0722)) - 0.061) * 12.0, -0.38, 0.38);
        float field = coverage + breakup * 4.0 * coverage * (1.0 - coverage);
        float aa = max(fwidth(field), 0.001);
        oxide = smoothstep(0.50 - aa, 0.50 + aa, field);
        vec3 pigment = mix(texture(aged_paint, UV).rgb, texture(aged_oxide, UV).rgb, oxide);
        vec3 paint_srgb = mix(pigment * 12.92, 1.055 * pow(pigment, vec3(1.0 / 2.4)) - 0.055, step(vec3(0.0031308), pigment));
        vec3 rust_srgb = mix(runoff * 12.92, 1.055 * pow(runoff, vec3(1.0 / 2.4)) - 0.055, step(vec3(0.0031308), runoff));
        vec3 stain = mix(paint_srgb, rust_srgb, trail * (1.0 - oxide));
        colour.rgb = mix(stain / 12.92, pow((stain + 0.055) / 1.055, vec3(2.4)), step(vec3(0.04045), stain));
        oxide = max(oxide, trail);
    }
    vec3 detail = mix(mix(steel, painted, paint), rust, oxide);
    // Scan luminance adds grain without importing the scan's green pigments.
    float grain = clamp(dot(detail, vec3(0.2126, 0.7152, 0.0722)) * 3.0, 0.0, 1.0);
    float dust = dust_enabled ? orm.a : 0.0;
    vec3 powder = texture(baked_dust, UV).rgb;
    float energy = dot(detail, vec3(0.2126, 0.7152, 0.0722));
    float scan_mean = mix(mix(0.079, 0.066, paint), 0.061, oxide);
    float aged_grain = clamp(pow(energy / scan_mean, 0.55), 0.55, 1.5);
    vec3 reflectance = colour.rgb * (aged_finish ? aged_grain : (0.88 + grain * 0.24));
    ALBEDO = mix(reflectance, powder, dust);
    vec3 scan_n = mix(scan_normal(normal_a, prop_position, signs, weights, 0.20, vec2(0)), scan_normal(normal_b, prop_position, signs, weights, 0.20, vec2(0)), paint);
    scan_n = mix(scan_n, scan_normal(normal_c, prop_position, signs, weights, 0.20, vec2(0)), oxide);
    mat3 prop_from_mesh = transpose(mat3(prop_x.xyz, prop_y.xyz, prop_z.xyz));
    vec3 grain_view = (VIEW_MATRIX * MODEL_MATRIX * vec4(transpose(prop_from_mesh) * scan_n, 0)).xyz;
    vec3 tangent_n = bc5_normal(texture(baked_normal, UV).rg);
    if (aged_finish) { tangent_n = normalize(mix(vec3(0, 0, 1), tangent_n, 0.08)); }
    float relief = aged_finish ? mix(0.18, 0.42, oxide) : mix(0.07, 0.22, oxide);
    NORMAL = normalize(TANGENT * tangent_n.x * (1.0 - dust * 0.8) + BINORMAL * tangent_n.y * (1.0 - dust * 0.8) + NORMAL * tangent_n.z + grain_view * relief * (1.0 - dust));
    vec3 detail_orm = mix(scan_sample(orm_a, prop_position, signs, weights, 0.20, vec2(0)), scan_sample(orm_b, prop_position, signs, weights, 0.20, vec2(0)), paint);
    detail_orm = mix(detail_orm, scan_sample(orm_c, prop_position, signs, weights, 0.20, vec2(0)), oxide);
    ROUGHNESS = mix(mix(clamp(orm.g + (detail_orm.g - 0.5) * 0.06, 0.15, 1.0), 0.94, trail), 0.98, dust);
    METALLIC = orm.b * (1.0 - dust) * (1.0 - trail);
    AO = orm.r;
    AO_LIGHT_AFFECT = 0.0;
    SPECULAR = 0.32;
    if (diagnostic == 1) {
        EMISSION = ALBEDO;
        ALBEDO = vec3(0);
        METALLIC = 0.0;
        SPECULAR = 0.0;
    } else if (diagnostic == 2) {
        EMISSION = vec3(paint, step(0.7, n.y), 1);
        ALBEDO = vec3(0);
        METALLIC = 0.0;
        SPECULAR = 0.0;
    } else if (diagnostic >= 3) {
        EMISSION = diagnostic == 3 ? texture(region_masks, UV).rgb : (diagnostic == 4 ? vec3(orm.g, orm.b, colour.a) : (diagnostic == 6 ? vec3(trail) : vec3(diagnostic_door && n.z > 0.999 ? 1.0 : 0.0)));
        ALBEDO = vec3(0);
        METALLIC = 0.0;
        SPECULAR = 0.0;
    }
}
