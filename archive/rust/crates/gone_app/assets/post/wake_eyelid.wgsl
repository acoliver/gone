// The wake eyelid fullscreen pass (issue #8).
//
// Composites the authored wake presentation over the finished LDR frame:
// opaque top and bottom eyelids that close over the room, a blur whose
// radius follows the authored smear while the eyes are barely open, and the
// authored dark-to-neutral exposure ramp shaping the light through the
// slit. The uniform is `gone_app::wake_pass::WakeEyelidMaterial`; the pass
// is a `FullscreenMaterial` installed after tonemapping and before
// upscaling (see `crates/gone_app/src/wake_pass.rs` for the order and what
// still requires live GPU proof).
//
// The source texture at this pass's slot is display-referred sRGB output
// (the game cameras render LDR into sRGB targets), so the authored lid and
// floor colors below are display-space values.

#import bevy_core_pipeline::fullscreen_vertex_shader::FullscreenVertexOutput

struct WakeEyelid {
    // 0 fully shut, 1 fully open (the sim's lid openness).
    lid_openness: f32,
    // 0 sharp, 1 fully smeared (the sim's blur).
    blur: f32,
    // 0 the authored dark floor, 1 neutral (the sim's exposure ramp).
    exposure_ramp: f32,
    // Uniform buffers round struct size up to 16 bytes; one float pads.
    _padding: f32,
}

@group(0) @binding(0) var screen_texture: texture_2d<f32>;
@group(0) @binding(1) var screen_sampler: sampler;
@group(0) @binding(2) var<uniform> wake: WakeEyelid;

// The closed-eye presentation: a dark warm gray, deliberately not black, so
// the closed screen still carries signal (and a capture of it is not the
// zeroed "compositor declined" signature).
const LID_COLOR: vec3<f32> = vec3<f32>(0.020, 0.012, 0.010);

// The light through the slit at exposure ramp zero: the authored dark floor
// the ramp rises from, a touch deeper than the lid color.
const RAMP_FLOOR: vec3<f32> = vec3<f32>(0.008, 0.005, 0.004);

// Half-width of the soft lid edge, in screen-v units. The edges ease over
// this band inside the slit, so the lids never carry a hard aliased edge;
// the aperture math below also retracts the lids one band beyond the screen
// so full openness leaves no residue.
const LID_SOFT: f32 = 0.045;

// How far the lid corners droop into the aperture, in screen-v units at the
// screen's left and right edges (zero at the center): a lens-shaped slit
// instead of a straight banded one.
const LID_ARC: f32 = 0.030;

// The blurred scene color: a golden-angle spiral of taps whose radius grows
// with the authored blur. Zero blur is the single tap.
fn blurred_color(uv: vec2<f32>) -> vec3<f32> {
    if (wake.blur < 1e-4) {
        return textureSampleLevel(screen_texture, screen_sampler, uv, 0.0).rgb;
    }
    let dims = vec2<f32>(textureDimensions(screen_texture));
    let radius = wake.blur * 0.02 * min(dims.x, dims.y);
    let step_angle = 2.399963229728653;
    var sum = textureSampleLevel(screen_texture, screen_sampler, uv, 0.0).rgb;
    for (var tap = 1u; tap < 9u; tap++) {
        let angle = step_angle * f32(tap);
        let offset = vec2<f32>(cos(angle), sin(angle)) * (radius * sqrt(f32(tap)) / sqrt(9.0));
        sum += textureSampleLevel(
            screen_texture,
            screen_sampler,
            uv + offset / dims,
            0.0,
        ).rgb;
    }
    return sum / 9.0;
}

// Coverage of the two eyelids at this pixel, 0 fully revealed, 1 fully
// covered. The slit's half-height h retracts from -LID_SOFT (lids overlapped
// past the center, fully shut) to 0.5 + LID_SOFT (lids retracted past the
// screen edges, no residue at full openness); the top lid's soft band eases
// inward from its edge, the bottom lid's mirrors it, so at full shut their
// union is opaque everywhere on screen.
fn lid_coverage(uv: vec2<f32>) -> f32 {
    let x = uv.x - 0.5;
    let y = uv.y - 0.5;
    // The lens-shaped aperture: the corners droop inward by LID_ARC.
    let droop = LID_ARC * (4.0 * x * x);
    // The retracted end clears the screen by the soft band plus the corner
    // droop, so full openness leaves no lid residue anywhere on screen.
    let h = mix(-LID_SOFT, 0.5 + LID_SOFT + LID_ARC, wake.lid_openness);
    let edge_top = -h + droop;
    let edge_bottom = h - droop;
    let cover_top = 1.0 - smoothstep(edge_top, edge_top + LID_SOFT, y);
    let cover_bottom = smoothstep(edge_bottom - LID_SOFT, edge_bottom, y);
    return max(cover_top, cover_bottom);
}

@fragment
fn fragment(in: FullscreenVertexOutput) -> @location(0) vec4<f32> {
    let scene = mix(RAMP_FLOOR, blurred_color(in.uv), wake.exposure_ramp);
    let color = mix(scene, LID_COLOR, lid_coverage(in.uv));
    return vec4<f32>(color, 1.0);
}
