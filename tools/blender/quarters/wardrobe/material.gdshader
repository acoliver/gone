shader_type spatial;
render_mode cull_back;
#include "res://app/shaders/steel_sampling.gdshaderinc"
uniform sampler2D face_albedo : source_color, repeat_disable, filter_linear_mipmap_anisotropic;
uniform sampler2D face_orm : repeat_disable, filter_linear_mipmap_anisotropic;
uniform sampler2D clean_paint : source_color, repeat_disable, filter_linear;
uniform sampler2D albedo_b : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform bool aged_finish = false;
uniform int diagnostic = 0;
uniform bool relief_enabled = true;
instance uniform vec4 face_front = vec4(0, 0, 1, 1);
instance uniform vec4 face_back = vec4(0, 0, 1, 1);
instance uniform vec4 face_edge = vec4(0, 0, 1, 1);
instance uniform vec4 face_dust = vec4(0, 0, 1, 1);
instance uniform vec4 local_low = vec4(0);
instance uniform vec4 local_size = vec4(1);
// Thickness axis, broad-image horizontal/vertical axes, material class.
instance uniform vec4 projection = vec4(2, 0, 1, 1);
varying vec3 part_position;
varying vec3 part_normal;

void vertex() {
    part_position = VERTEX;
    part_normal = NORMAL;
}

vec2 atlas_uv(vec2 local, vec4 rectangle) {
    vec2 half_texel = .5 / vec2(textureSize(face_albedo, 0));
    return mix(rectangle.xy + half_texel, rectangle.zw - half_texel,
               clamp(vec2(local.x, 1.0 - local.y), vec2(0), vec2(1)));
}

void fragment() {
    vec3 n = normalize(part_normal);
    vec3 point = part_position - local_low.xyz;
    vec3 normalized = point / local_size.xyz;
    int thickness = int(projection.x);
    int horizontal = int(projection.y);
    int vertical = int(projection.z);
    vec4 rectangle = n[thickness] >= 0.0 ? face_front : face_back;
    vec2 uv = vec2(normalized[horizontal], normalized[vertical]);
    bool hardware = projection.w > 1.5;
    if (projection.w < .5) {
        // Storage infill boxes have no thin panel axis: project every broad
        // face independently instead of stretching a frame strip over a side.
        vec3 absolute = abs(n);
        uv = absolute.x > max(absolute.y, absolute.z) ? normalized.zy :
             (absolute.y > absolute.z ? normalized.xz : normalized.xy);
        rectangle = absolute.y > max(absolute.x, absolute.z) ? face_dust : face_front;
    } else if (hardware) {
        vec3 absolute = abs(n);
        vec2 metres = absolute.x > max(absolute.y, absolute.z) ? point.zy :
                      (absolute.y > absolute.z ? point.xz : point.xy);
        uv = fract(metres / .2);
    } else if (abs(n[thickness]) < .7) {
        rectangle = face_edge;
        vec3 absolute = abs(n);
        int axis = absolute.x > max(absolute.y, absolute.z) ? 0 : (absolute.y > absolute.z ? 1 : 2);
        int u = axis == 0 ? 2 : 0;
        int v = axis == 1 ? 2 : 1;
        if (local_size[u] > local_size[v]) {
            int swap = u;
            u = v;
            v = swap;
        }
        uv = vec2(point[u] / .08, point[v] / 2.2);
        if (n.y > .7) {
            rectangle = face_dust;
            uv = vec2(point.x / .952, point.z / .626);
        }
    }
    vec4 colour = texture(face_albedo, atlas_uv(uv, rectangle));
    vec4 orm = texture(face_orm, atlas_uv(uv, rectangle));
    vec3 signs = mix(vec3(-1), vec3(1), step(vec3(0), n));
    vec3 weights = pow(abs(n), vec3(4));
    weights /= dot(weights, vec3(1));
    vec3 scan = scan_sample(albedo_b, part_position, signs, weights, .20, vec2(0));
    float grain = clamp(dot(scan, vec3(.2126, .7152, .0722)) * 3.0, 0.0, 1.0);
    ALBEDO = texture(clean_paint, vec2(.5)).rgb;
    ALBEDO *= .88 + grain * .24;
    ROUGHNESS = .45;
    METALLIC = .02;
    if (projection.w > 1.5) {
        ALBEDO = projection.w < 2.5 ? vec3(.32, .36, .39) * (.9 + grain * .2) : vec3(.025, .032, .031);
        ROUGHNESS = projection.w < 2.5 ? .35 : .52;
        METALLIC = .45;
    }
    if (aged_finish) {
        ALBEDO = colour.rgb;
        ROUGHNESS = orm.g;
        METALLIC = 0.0;
        // Chroma-derived paint relief and image luminance pits do not place wear.
        float height = hardware ? dot(colour.rgb, vec3(.2126, .7152, .0722)) * .0003 : (1.0-colour.a) * .0015;
        vec3 dpdx = dFdx(VERTEX);
        vec3 dpdy = dFdy(VERTEX);
        vec3 base_normal = normalize(cross(dpdx, dpdy));
        base_normal *= dot(base_normal, NORMAL) < 0.0 ? -1.0 : 1.0;
        vec3 r1 = cross(dpdy, base_normal);
        vec3 r2 = cross(base_normal, dpdx);
        vec3 gradient = (r1*dFdx(height) + r2*dFdy(height)) / dot(dpdx, r1);
        if (relief_enabled) NORMAL = normalize(NORMAL-gradient);
    }
    SPECULAR = .32;
    if (diagnostic > 0) {
        vec3 shown = ALBEDO;
        if (diagnostic == 2) {
            bool edge = uv.x < .1 || uv.x > .9 || uv.y < .1 || uv.y > .9;
            shown = hardware ? vec3(0) : vec3(edge ? 1.0 : 0.0, edge ? 0.0 : 1.0, n.y > .7 ? 1.0 : 0.0);
        }
        if (diagnostic == 3) {
            shown = projection.w < 1.5 ? vec3(0, 1, 0) : (projection.w < 2.5 ? vec3(0, 0, 1) : vec3(1, 0, 0));
        }
        EMISSION = shown;
        ALBEDO = vec3(0);
        METALLIC = 0.0;
        SPECULAR = 0.0;
    }
}
