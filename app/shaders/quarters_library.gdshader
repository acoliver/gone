shader_type spatial;
render_mode cull_back;
#include "res://app/shaders/steel_sampling.gdshaderinc"

uniform sampler2D paint_grain : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
varying vec3 part_position;
varying vec3 part_normal;

void vertex() {
    part_position = VERTEX;
    part_normal = NORMAL;
}

uniform sampler2D baked_albedo : source_color, repeat_disable, filter_linear_mipmap_anisotropic;
uniform sampler2D baked_normal : hint_normal, repeat_disable, filter_linear_mipmap_anisotropic;
uniform sampler2D baked_orm : repeat_disable, filter_linear_mipmap_anisotropic;
uniform sampler2D regions : repeat_disable, filter_nearest;
uniform bool aged_finish = false;
uniform bool relief_enabled = true;
uniform int diagnostic = 0;

void fragment() {
    ALBEDO = texture(baked_albedo, UV).rgb;
    vec3 orm = texture(baked_orm, UV).rgb;
    ROUGHNESS = orm.g;
    vec3 region = texture(regions, UV).rgb;
    if (!aged_finish && max(region.r, region.g) > .5) {
        vec3 n = normalize(part_normal);
        vec3 signs = mix(vec3(-1), vec3(1), step(vec3(0), n));
        vec3 weights = pow(abs(n), vec3(4));
        weights /= dot(weights, vec3(1));
        vec3 scan = scan_sample(paint_grain, part_position, signs, weights, .20, vec2(0));
        float grain = clamp(dot(scan, vec3(.2126, .7152, .0722))*3.0, 0.0, 1.0);
        ALBEDO *= .88+grain*.24;
        ROUGHNESS = .40+grain*.10;
    }
    if (aged_finish && region.b > .5) ROUGHNESS = max(ROUGHNESS, .94);
    METALLIC = orm.b;
    SPECULAR = .32;
    if (relief_enabled) NORMAL_MAP = texture(baked_normal, UV).rgb;
    if (diagnostic > 0) {
        EMISSION = diagnostic == 2 ? texture(regions, UV).rgb : ALBEDO;
        ALBEDO = vec3(0.0);
        METALLIC = 0.0;
        SPECULAR = 0.0;
    }
}
