shader_type spatial;
render_mode cull_back;
#include "steel_sampling.gdshaderinc"
uniform sampler2D baked_albedo : source_color, repeat_disable, filter_linear_mipmap_anisotropic;
uniform sampler2D baked_normal : hint_normal, repeat_disable, filter_linear_mipmap_anisotropic;
uniform sampler2D baked_orm : repeat_disable, filter_linear_mipmap_anisotropic;
uniform sampler2D baked_dust : source_color, repeat_disable, filter_linear_mipmap_anisotropic;
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
uniform sampler2D face_albedo : source_color, repeat_disable, filter_linear_mipmap_anisotropic;
uniform sampler2D top_nodust : source_color, filter_linear_mipmap, repeat_disable;
uniform sampler2D face_orm : repeat_disable, filter_linear_mipmap_anisotropic;
instance uniform vec4 face_rectangle = vec4(0, 0, 1, 1);
instance uniform vec4 face_projection = vec4(0, 1, 0, 0);
instance uniform vec4 face_size = vec4(1, 1, 0, 0);
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

vec2 face_uv() {
    vec2 projected = vec2(prop_position[int(face_projection.x)], prop_position[int(face_projection.y)]);
    vec2 local = (projected - face_projection.zw) / face_size.xy;
    if (face_size.z > 0.5) {
        float angle = atan(prop_position.z - 0.301, prop_position.x + 0.260);
        float centre = floor((prop_position.y - 0.350) / 0.9 + 0.5) * 0.9 + 0.350;
        local = vec2(angle * 0.010 / 0.20 + 0.5, (prop_position.y - centre) / 0.20 + 0.5);
    } else if (face_size.w > 0.5) {
        local = fract(local);
    }
    local = clamp(vec2(local.x, 1.0 - local.y), vec2(0), vec2(1));
    vec2 texel = 0.5 / vec2(textureSize(face_albedo, 0));
    return mix(face_rectangle.xy + texel, face_rectangle.zw - texel, local);
}

void fragment() {
    vec3 geometry_normal = NORMAL;
    vec4 colour = texture(baked_albedo, UV);
    vec4 orm = texture(baked_orm, UV);
    float paint = 1.0 - step(0.08, abs(texture(weather_masks, UV).a - 0.25));
    vec3 n = normalize(prop_normal);
    float oxide = colour.a;
    vec3 signs = mix(vec3(-1), vec3(1), step(vec3(0), n));
    vec3 weights = pow(abs(n), vec3(4));
    weights /= dot(weights, vec3(1));
    vec3 steel = scan_sample(albedo_a, prop_position, signs, weights, 0.20, vec2(0));
    vec3 painted = scan_sample(albedo_b, prop_position, signs, weights, 0.20, vec2(0));
    vec3 rust = scan_sample(albedo_c, prop_position, signs, weights, 0.20, vec2(0));
    vec3 detail = mix(mix(steel, painted, paint), rust, oxide);
    // Scan luminance adds grain without importing the scan's green pigments.
    float grain = clamp(dot(detail, vec3(0.2126, 0.7152, 0.0722)) * 3.0, 0.0, 1.0);
    float dust = dust_enabled ? orm.a : 0.0;
    vec3 powder = texture(baked_dust, UV).rgb;
    vec3 reflectance = colour.rgb * (0.88 + grain * 0.24);
    ALBEDO = mix(reflectance, powder, dust);
    vec3 scan_n = mix(scan_normal(normal_a, prop_position, signs, weights, 0.20, vec2(0)), scan_normal(normal_b, prop_position, signs, weights, 0.20, vec2(0)), paint);
    scan_n = mix(scan_n, scan_normal(normal_c, prop_position, signs, weights, 0.20, vec2(0)), oxide);
    mat3 prop_from_mesh = transpose(mat3(prop_x.xyz, prop_y.xyz, prop_z.xyz));
    vec3 grain_view = (VIEW_MATRIX * MODEL_MATRIX * vec4(transpose(prop_from_mesh) * scan_n, 0)).xyz;
    vec3 tangent_n = bc5_normal(texture(baked_normal, UV).rg);
    float relief = mix(0.07, 0.22, oxide);
    NORMAL = normalize(TANGENT * tangent_n.x * (1.0 - dust * 0.8) + BINORMAL * tangent_n.y * (1.0 - dust * 0.8) + NORMAL * tangent_n.z + grain_view * relief * (1.0 - dust));
    vec3 detail_orm = mix(scan_sample(orm_a, prop_position, signs, weights, 0.20, vec2(0)), scan_sample(orm_b, prop_position, signs, weights, 0.20, vec2(0)), paint);
    detail_orm = mix(detail_orm, scan_sample(orm_c, prop_position, signs, weights, 0.20, vec2(0)), oxide);
    ROUGHNESS = mix(clamp(orm.g + (detail_orm.g - 0.5) * 0.06, 0.15, 1.0), 0.98, dust);
    METALLIC = orm.b * (1.0 - dust);
    if (aged_finish) {
        vec2 atlas_uv = face_uv();
        colour = texture(face_albedo, atlas_uv);
        vec4 face_material = texture(face_orm, atlas_uv);
        oxide = colour.a;
        if (!dust_enabled && face_size.w < -0.5) {
            vec2 local_uv = (atlas_uv - face_rectangle.xy) / (face_rectangle.zw - face_rectangle.xy);
            colour.rgb = texture(top_nodust, local_uv).rgb;
        }
        // Fine, low-strength grain cannot move a generated paint/rust boundary.
        vec3 fine = scan_sample(albedo_b, prop_position, signs, weights, 0.012, vec2(0));
        float fine_grain = clamp(dot(fine, vec3(0.2126, 0.7152, 0.0722)) / 0.066 - 1.0, -1.0, 1.0);
        ALBEDO = colour.rgb * (1.0 + fine_grain * 0.025 * (1.0 - oxide));
        ROUGHNESS = face_material.g;
        METALLIC = 0.0;
        // Differentiate the same image-derived 1.5 mm raised paint, in metres.
        // Hardware pitting comes from its generated image's linear luminance.
        float height = face_size.w > 0.5 ? dot(colour.rgb, vec3(0.2126, 0.7152, 0.0722)) * 0.0003 : (1.0 - oxide) * 0.0015;
        vec3 dpdx = dFdx(VERTEX);
        vec3 dpdy = dFdy(VERTEX);
        vec3 base_normal = normalize(cross(dpdx, dpdy));
        base_normal *= dot(base_normal, geometry_normal) < 0.0 ? -1.0 : 1.0;
        vec3 r1 = cross(dpdy, base_normal);
        vec3 r2 = cross(base_normal, dpdx);
        float determinant = dot(dpdx, r1);
        vec3 gradient = (r1 * dFdx(height) + r2 * dFdy(height)) / determinant;
        NORMAL = normalize(geometry_normal - gradient);
        dust = face_material.a;
        orm.g = face_material.g;
        orm.b = 0.0;
    }
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
    } else if (diagnostic == 7) {
        EMISSION = face_size.z > 0.5 ? vec3(1, 0, 0) : (face_size.w > 1.5 ? vec3(0, 1, 0) : vec3(0, 0, 1));
        ALBEDO = vec3(0);
        METALLIC = 0.0;
        SPECULAR = 0.0;
    } else if (diagnostic == 8) {
        NORMAL = normalize(geometry_normal);
    } else if (diagnostic == 9) {
        NORMAL = normalize(geometry_normal);
        ALBEDO = vec3(0.35);
        ROUGHNESS = 0.7;
        METALLIC = 0.0;
    } else if (diagnostic >= 3) {
        EMISSION = diagnostic == 3 ? texture(region_masks, UV).rgb : (diagnostic == 4 ? vec3(orm.g, orm.b, colour.a) : (diagnostic == 6 ? vec3(0) : vec3(diagnostic_door && n.z > 0.999 ? 1.0 : 0.0)));
        ALBEDO = vec3(0);
        METALLIC = 0.0;
        SPECULAR = 0.0;
    }
}
