//! Conversion of captured frames to PNG bytes (issue #15).
//!
//! The harness captures screenshots of the offscreen capture target through
//! `bevy::render::view::screenshot` and writes each capture straight to disk. The
//! captured [`Image`] carries the target's texture format
//! (`Bgra8UnormSrgb`); this module turns those bytes into a PNG. Conversion and
//! PNG encoding are pure CPU work, so the runner's decode path is exercised
//! end-to-end in tests without a GPU.

use std::io::Cursor;

use bevy::image::Image;

/// Convert one captured frame image to PNG bytes.
///
/// # Errors
/// Returns a message when the surface format has no CPU conversion or the PNG
/// encode fails; the caller turns this into an immediate scenario failure.
pub fn capture_to_png(image: &Image) -> Result<Vec<u8>, String> {
    let dynamic = image
        .clone()
        .try_into_dynamic()
        .map_err(|e| format!("capture convert: {e}"))?;
    let rgb = dynamic.to_rgb8();
    let mut bytes = Cursor::new(Vec::new());
    rgb.write_to(&mut bytes, image::ImageFormat::Png)
        .map_err(|e| format!("capture png encode: {e}"))?;
    Ok(bytes.into_inner())
}

#[cfg(test)]
mod tests {
    use bevy::asset::RenderAssetUsages;
    use bevy::image::Image;
    use bevy::render::render_resource::{Extent3d, TextureDimension, TextureFormat};

    use super::capture_to_png;
    use crate::harness::frame;

    /// A capture-shaped image in the target's BGRA format whose top-left corner
    /// carries the frame-code chip (what the GPU hands back for a real capture).
    fn fake_surface_capture(tick: u64, frame: u64) -> Image {
        let (chip_w, chip_h) = frame::chip_size();
        let (width, height) = (64u32, 48u32);
        let chip = frame::encode_chip_rgba(tick, frame);
        // Surface bytes are BGRA: swap the chip's RGBA channels into BGRA order.
        let mut bgra = Vec::with_capacity((width * height * 4) as usize);
        for row in 0..height {
            for col in 0..width {
                let in_chip = col < chip_w && row < chip_h;
                let src = ((row * chip_w + col) * 4) as usize;
                let (red, green, blue, alpha) = if in_chip {
                    (chip[src], chip[src + 1], chip[src + 2], chip[src + 3])
                } else {
                    (0x05, 0x05, 0x06, 0xff)
                };
                bgra.extend_from_slice(&[blue, green, red, alpha]);
            }
        }
        Image::new(
            Extent3d {
                width,
                height,
                depth_or_array_layers: 1,
            },
            TextureDimension::D2,
            bgra,
            TextureFormat::Bgra8UnormSrgb,
            RenderAssetUsages::MAIN_WORLD,
        )
    }

    #[test]
    fn bgra_surface_capture_decodes_to_its_frame_code() {
        // The full path a beat capture takes: GPU image (surface format) ->
        // PNG bytes -> runner-style decode of the top-left chip block.
        let png = capture_to_png(&fake_surface_capture(4321, 77)).expect("png");
        let decoded = image::load_from_memory(&png).expect("png decode").to_rgb8();
        assert_eq!(
            frame::decode_chip_from_rgb(decoded.as_raw(), 3, decoded.width(), decoded.height())
                .expect("chip decode"),
            (4321, 77)
        );
    }

    #[test]
    fn unsupported_surface_format_fails_naming_the_format() {
        let mut image = fake_surface_capture(1, 2);
        image.texture_descriptor.format = TextureFormat::Rgba16Float;
        let err = capture_to_png(&image).expect_err("must fail");
        assert!(
            err.contains("capture convert"),
            "error must carry context: {err}"
        );
    }
}
