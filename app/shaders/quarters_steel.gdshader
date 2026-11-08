shader_type spatial;
render_mode cull_back;
#include "steel_sampling.gdshaderinc"
uniform sampler2D baked_albedo : source_color, repeat_disable, filter_linear_mipmap_anisotropic;
uniform sampler2D baked_normal : hint_normal, repeat_disable, filter_linear_mipmap_anisotropic;
uniform sampler2D baked_orm : repeat_disable, filter_linear_mipmap_anisotropic;
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

void fragment() {
    vec4 colour = texture(baked_albedo, UV);
    vec4 orm = texture(baked_orm, UV);
    float paint = 1.0 - step(0.08, abs(texture(weather_masks, UV).a - 0.25));
    float oxide = colour.a;
    vec3 n = normalize(prop_normal);
    vec3 signs = mix(vec3(-1), vec3(1), step(vec3(0), n));
    vec3 weights = pow(abs(n), vec3(4));
    weights /= dot(weights, vec3(1));
    vec3 steel = scan_sample(albedo_a, prop_position, signs, weights, 0.20, vec2(0));
    vec3 painted = scan_sample(albedo_b, prop_position, signs, weights, 0.20, vec2(0));
    vec3 rust = scan_sample(albedo_c, prop_position, signs, weights, 0.20, vec2(0));
    vec3 detail = mix(mix(steel, painted, paint), rust, oxide);
    // Scan luminance adds grain without importing the scan's green pigments.
    float grain = clamp(dot(detail, vec3(0.2126, 0.7152, 0.0722)) * 3.0, 0.0, 1.0);
    ALBEDO = colour.rgb * mix(0.88 + grain * 0.24, 1.0, orm.a);
    vec3 scan_n = mix(scan_normal(normal_a, prop_position, signs, weights, 0.20, vec2(0)), scan_normal(normal_b, prop_position, signs, weights, 0.20, vec2(0)), paint);
    scan_n = mix(scan_n, scan_normal(normal_c, prop_position, signs, weights, 0.20, vec2(0)), oxide);
    mat3 prop_from_mesh = transpose(mat3(prop_x.xyz, prop_y.xyz, prop_z.xyz));
    vec3 grain_view = (VIEW_MATRIX * MODEL_MATRIX * vec4(transpose(prop_from_mesh) * scan_n, 0)).xyz;
    vec3 tangent_n = bc5_normal(texture(baked_normal, UV).rg);
    NORMAL = normalize(TANGENT * tangent_n.x + BINORMAL * tangent_n.y + NORMAL * tangent_n.z + grain_view * mix(0.07, 0.22, oxide) * (1.0 - orm.a));
    vec3 detail_orm = mix(scan_sample(orm_a, prop_position, signs, weights, 0.20, vec2(0)), scan_sample(orm_b, prop_position, signs, weights, 0.20, vec2(0)), paint);
    detail_orm = mix(detail_orm, scan_sample(orm_c, prop_position, signs, weights, 0.20, vec2(0)), oxide);
    ROUGHNESS = clamp(orm.g + (detail_orm.g - 0.5) * 0.06 * (1.0 - orm.a), 0.15, 1.0);
    METALLIC = orm.b;
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
    }
}
