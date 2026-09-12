//! Explicit post-processing chain for the normal game (issue #6 slice B).
//!
//! Nothing here is assumed from plugin defaults: the plugin set is added by
//! name, the camera components are authored by [`camera_post_components`], and
//! the auto-exposure metering mask is a checked-in asset this module owns the
//! construction of. The harness lanes never build this module's plugins; the
//! post chain exists on the game camera only.
//!
//! # Render-pass order (recorded for the eyelid pass, issue #8)
//!
//! Bevy 0.19's `Core3d` render schedule chains the sets `Prepass → MainPass →
//! EarlyPostProcess → PostProcess` (`bevy_core_pipeline::schedule`). Within
//! the `PostProcess` set, the passes this slice installs are ordered by these
//! explicit edges declared in bevy's own plugins:
//!
//! ```text
//! auto_exposure.before(tonemapping)                  // bevy_post_process::auto_exposure
//! post_processing.after(depth_of_field).before(tonemapping)  // effect stack (vignette)
//! tonemapping.in_set(Core3dSystems::PostProcess)     // bevy_core_pipeline::core_3d
//! upscaling.after(Core3dSystems::PostProcess)        // bevy_core_pipeline::core_3d
//! ```
//!
//! Auto exposure and the effect stack each pin only their edge to tonemapping,
//! so their order relative to each other is unspecified by bevy. The order
//! that is pinned, and that a future pass must respect:
//!
//! ```text
//! MainPass → [auto_exposure, effect stack (vignette)] → tonemapping → upscaling
//! ```
//!
//! The eyelid fullscreen pass (#8) will be installed AFTER tonemapping
//! (`after(Core3dSystems::PostProcess)`), compositing over the finished LDR
//! image, and it must declare its order against upscaling explicitly
//! (upscaling carries the same `after` edge, so the two are otherwise
//! unordered). Metering stays independent of eyelid occlusion for one
//! structural reason: the histogram pass reads the HDR main texture
//! (`ViewTarget::main_texture_view()`), and a pass that runs after tonemapping
//! never writes that texture. The eyelid can therefore darken the whole screen
//! without the exposure running away. The near-zero corner weight of the
//! metering mask additionally decouples metering from the one order bevy
//! leaves unspecified (vignette darkens corners only, and corner pixels carry
//! almost no histogram weight either way).
//!
//! # Validated on Metal vs assumed
//!
//! Validated on this machine (M4 Max, Metal, bevy 0.19.1): the game binary
//! boots and renders with this exact chain, all pipelines compile without
//! shader or bind-group errors, and auto exposure picks up the authored mask
//! asset (see the wiring test, which builds the real plugins without a GPU).
//! Assumed from bevy source, not observed with a frame debugger: the pass
//! edges quoted above, the histogram reading the HDR main texture, and the
//! 16-level metering-mask quantization documented on `AutoExposure`.

use bevy::app::{App, Plugin};
use bevy::asset::Handle;
use bevy::core_pipeline::tonemapping::Tonemapping;
use bevy::ecs::prelude::Resource;
use bevy::image::Image;
use bevy::post_process::auto_exposure::{AutoExposure, AutoExposurePlugin};
use bevy::post_process::effect_stack::Vignette;

/// The checked-in metering-mask asset this module owns, relative to the app's
/// asset root (`crates/gone_app/assets`).
const MASK_ASSET_PATH: &str = "post/metering_mask.png";

/// Metering-mask side length in pixels. The histogram samples the mask
/// stretched over the whole screen; 64x64 is far above its 16-level
/// quantization, so a bigger texture would change nothing.
///
/// Runtime never builds the image in code: the checked-in asset is loaded by
/// [`GamePostChainPlugin`]. This constant and the construction function below
/// exist in test space only, as the executable definition of what the
/// checked-in asset contains. The side length is `u16` so the construction
/// converts pixel indices to floats with the lossless `f32::from`.
#[cfg(test)]
const MASK_SIZE: u16 = 64;

/// The auto-exposure metering mask resource for the game camera. Built by
/// [`GamePostChainPlugin`] from the checked-in asset; consumed by the player
/// rig spawner, which copies the handle into the camera's [`AutoExposure`].
#[derive(Resource)]
pub struct PostChainAssets {
    /// The center-weighted metering mask (`AutoExposure::metering_mask`).
    pub(crate) metering_mask: Handle<Image>,
}

/// Installs the game's explicit post chain: bevy's [`AutoExposurePlugin`]
/// (not added by `DefaultPlugins`) plus the metering-mask asset handle every
/// game camera receives. Adding camera components is deliberately separate
/// ([`camera_post_components`]): the plugin is render-graph wiring, the
/// components are camera configuration, and the rig spawner joins the two.
///
/// # Panics
/// Panics without an [`bevy::asset::AssetServer`] resource: this plugin is a
/// game feature that always builds after `DefaultPlugins`, so a missing asset
/// server means the plugins were wired in the wrong order.
pub struct GamePostChainPlugin;

impl Plugin for GamePostChainPlugin {
    fn build(&self, app: &mut App) {
        app.add_plugins(AutoExposurePlugin);
        let server = app
            .world()
            .get_resource::<bevy::asset::AssetServer>()
            .expect("GamePostChainPlugin requires the asset server (DefaultPlugins provides it)");
        let metering_mask = server.load::<Image>(MASK_ASSET_PATH);
        app.insert_resource(PostChainAssets { metering_mask });
    }
}

/// The post-chain components every game camera carries: `AgX` tonemapping, an
/// authored vignette, and auto exposure metering through `mask`.
///
/// Vignette configuration (chosen, not default): a gentle pull toward the
/// center that reads as lens fall-off, not as a tunnel. `intensity 0.35`
/// keeps the corner darkening subtle; `radius 0.85` and `smoothness 5.0`
/// spread the falloff so no hard edge exists anywhere on screen. Center and
/// roundness stay at the neutral defaults (screen center, circular).
///
/// The evidence harness may capture on/off comparisons for these components;
/// they need no toggle here. This bundle is the single home of the values.
#[must_use]
pub(crate) fn camera_post_components(mask: Handle<Image>) -> (Tonemapping, Vignette, AutoExposure) {
    (
        Tonemapping::AgX,
        Vignette {
            intensity: 0.35,
            radius: 0.85,
            smoothness: 5.0,
            ..Vignette::default()
        },
        AutoExposure {
            metering_mask: mask,
            ..AutoExposure::default()
        },
    )
}

/// Construct the metering-mask image: a radial center-weighted falloff over
/// [`MASK_SIZE`] squared pixels, stored as single-channel `R8Unorm` (auto
/// exposure samples the red channel only).
///
/// Construction, per pixel: screen coordinates normalize to `nx, ny` in
/// `[-1, 1]`; the normalized radius is `r = (nx² + ny²)⁰·⁵ / √2`, so `r` is 0
/// at the center and 1 at the corners; the weight is the window
/// `w = (1 − r²)²`, which is 1.0 at the center, 0.0 at the corners, has zero
/// slope at both ends, and concentrates the weight in the middle half of the
/// frame (a mid-edge pixel weighs 0.25); the weight is then quantized to the
/// shader's 16 discrete levels (`byte = round(15·w) · 17`) so the tested
/// bytes are exactly the weights the GPU applies. The checked-in asset
/// (`crates/gone_app/assets/post/metering_mask.png`, 8-bit grayscale PNG) is
/// this exact array serialized row-major.
#[cfg(test)]
fn metering_mask_image() -> Image {
    use bevy::asset::RenderAssetUsages;
    use bevy::render::render_resource::{Extent3d, TextureDimension, TextureFormat};

    let mut data = Vec::with_capacity(usize::from(MASK_SIZE) * usize::from(MASK_SIZE));
    for y in 0..MASK_SIZE {
        for x in 0..MASK_SIZE {
            data.push(mask_weight_byte(x, y));
        }
    }
    Image::new(
        Extent3d {
            width: u32::from(MASK_SIZE),
            height: u32::from(MASK_SIZE),
            depth_or_array_layers: 1,
        },
        TextureDimension::D2,
        data,
        TextureFormat::R8Unorm,
        // Both worlds: MAIN_WORLD keeps the bytes inspectable, RENDER_WORLD is
        // what lets the histogram pass sample the texture on the GPU.
        RenderAssetUsages::default(),
    )
}

/// The quantized mask weight for one pixel, as the `R8Unorm` byte. Identical
/// to `byte = round(15 · w) · 17` with `w = (1 − r²)²`: for the nonnegative
/// weights this construction produces (r² stays in [0, 1]), counting the
/// half-integer thresholds the scaled weight reaches equals `round` with the
/// clamp never binding, so the level is derived without a float-to-int cast.
#[cfg(test)]
fn mask_weight_byte(x: u16, y: u16) -> u8 {
    let px = (f32::from(x) + 0.5) / f32::from(MASK_SIZE) * 2.0 - 1.0;
    let py = (f32::from(y) + 0.5) / f32::from(MASK_SIZE) * 2.0 - 1.0;
    let normalized_radius_squared = (px * px).midpoint(py * py);
    let scaled = (1.0 - normalized_radius_squared).powi(2) * 15.0;
    let level = u8::try_from(
        (1u8..=15)
            .filter(|&threshold| scaled >= f32::from(threshold) - 0.5)
            .count(),
    )
    .expect("at most fifteen thresholds exist, so the count fits u8");
    level * 17
}

#[cfg(test)]
mod tests {
    use super::{MASK_SIZE, camera_post_components, mask_weight_byte, metering_mask_image};
    use bevy::asset::Handle;
    use bevy::core_pipeline::tonemapping::Tonemapping;
    use bevy::image::Image;

    /// The constructed mask's pixel bytes (the `Image` carries them behind an
    /// `Option`; construction always populates them).
    fn mask_bytes() -> Vec<u8> {
        metering_mask_image()
            .data
            .expect("construction always populates the pixel bytes")
    }

    #[test]
    fn mask_center_heaviest_and_corner_lightest() {
        let bytes = mask_bytes();
        let center = center_index();
        let corner = 0usize;
        assert!(
            bytes[center] > bytes[corner],
            "center weight {} must exceed corner weight {}",
            bytes[center],
            bytes[corner]
        );
        // The center pixel is fully weighted, the corner fully ignored.
        assert_eq!(bytes[center], 255);
        assert_eq!(bytes[corner], 0);
    }

    #[test]
    fn mask_falls_off_monotonically_from_the_center() {
        let bytes = mask_bytes();
        let (cx, cy) = (MASK_SIZE / 2, MASK_SIZE / 2);
        // Along the center row, the column axis, and the diagonal, the bytes
        // are non-increasing as the pixel moves away from the center (the
        // 16-level quantization makes plateaus legal; rises are not). The
        // bound stays one short of the far edge so the +1 neighbor index is
        // the last pixel, not past it.
        for offset in 0..cx - 1 {
            assert!(bytes[byte_index(cx + offset, cy)] >= bytes[byte_index(cx + offset + 1, cy)]);
            assert!(bytes[byte_index(cx, cy + offset)] >= bytes[byte_index(cx, cy + offset + 1)]);
            assert!(
                bytes[byte_index(cx + offset, cy + offset)]
                    >= bytes[byte_index(cx + offset + 1, cy + offset + 1)]
            );
        }
    }

    #[test]
    fn mask_edges_are_mirror_symmetric() {
        // The radial construction must not drift with integer pixel centers.
        for offset in 0..MASK_SIZE / 2 {
            assert_eq!(
                mask_weight_byte(MASK_SIZE / 2 + offset, MASK_SIZE / 2),
                mask_weight_byte(MASK_SIZE / 2 - offset - 1, MASK_SIZE / 2)
            );
        }
    }

    #[test]
    fn mask_bytes_are_exact_16_level_quantizations() {
        // `byte = level * 17` for level in 0..=15, so every byte is a multiple
        // of 17: the tested weights are exactly what the shader quantizes to.
        for byte in mask_bytes() {
            assert_eq!(
                u32::from(byte) % 17,
                0,
                "byte {byte} is not a 16-level quantization"
            );
        }
        // The falloff exercises every one of the sixteen levels, in order.
        let mut levels: Vec<u8> = mask_bytes().iter().map(|byte| byte / 17).collect();
        levels.sort_unstable();
        levels.dedup();
        assert_eq!(levels, Vec::<u8>::from_iter(0u8..=15));
    }

    #[test]
    fn mask_image_shape_is_r8_square() {
        let image = metering_mask_image();
        assert_eq!(image.width(), u32::from(MASK_SIZE));
        assert_eq!(image.height(), u32::from(MASK_SIZE));
        assert_eq!(
            image.texture_descriptor.format,
            bevy::render::render_resource::TextureFormat::R8Unorm
        );
        assert_eq!(
            image.data.expect("bytes exist").len(),
            usize::from(MASK_SIZE) * usize::from(MASK_SIZE)
        );
    }

    #[test]
    fn camera_components_carry_the_authored_configuration() {
        let mask: Handle<Image> = Handle::default();
        let (tonemapping, vignette, exposure) = camera_post_components(mask.clone());
        assert_eq!(tonemapping, Tonemapping::AgX);
        assert!((vignette.intensity - 0.35).abs() < f32::EPSILON);
        assert!((vignette.radius - 0.85).abs() < f32::EPSILON);
        assert!((vignette.smoothness - 5.0).abs() < f32::EPSILON);
        assert_eq!(vignette.center, bevy::math::Vec2::new(0.5, 0.5));
        assert_eq!(vignette.color, bevy::color::Color::BLACK);
        assert_eq!(exposure.metering_mask, mask);
        assert_eq!(exposure.range, -8.0..=8.0);
        assert_eq!(exposure.filter, 0.10..=0.90);
    }

    /// The checked-in asset's generator: serializes [`metering_mask_image`]
    /// to the 8-bit grayscale PNG the game loads at
    /// `assets/post/metering_mask.png`, reads it back, and fails if the file
    /// ever drifts from the construction. Ignored so the normal test run has
    /// no write side effects; run explicitly with
    /// `cargo test -p gone_app generate_metering_mask_asset -- --ignored`
    /// whenever the construction changes.
    #[test]
    #[ignore = "asset generator: writes assets/post/metering_mask.png"]
    fn generate_metering_mask_asset() {
        let image = metering_mask_image();
        let (width, height) = (image.width(), image.height());
        let bytes = image.data.expect("construction always populates the bytes");
        let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("assets")
            .join(super::MASK_ASSET_PATH);
        std::fs::create_dir_all(path.parent().expect("asset dir parent"))
            .expect("create asset dir");
        image::save_buffer(&path, &bytes, width, height, image::ExtendedColorType::L8)
            .expect("write metering mask PNG");
        // The written file must decode back to the constructed bytes exactly:
        // the asset on disk is the construction, nothing more.
        let decoded = image::open(&path)
            .expect("re-read metering mask PNG")
            .to_luma8();
        assert_eq!(decoded.width(), width);
        assert_eq!(decoded.height(), height);
        assert_eq!(decoded.as_raw().as_slice(), bytes.as_slice());
    }

    /// Flat index of the byte nearest the mask center (size is even, so the
    /// center sits between four pixels; the top-left of that quadrant is the
    /// brightest of them and the first byte in row-major order).
    fn center_index() -> usize {
        byte_index(MASK_SIZE / 2, MASK_SIZE / 2)
    }

    fn byte_index(x: u16, y: u16) -> usize {
        usize::from(y) * usize::from(MASK_SIZE) + usize::from(x)
    }
}
