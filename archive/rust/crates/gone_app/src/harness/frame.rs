//! The frame-code encoding for the harness bootstrap lane (issue #6 / slice A).
//!
//! The harness lane renders to an off-window image target whose pixels *are* a
//! machine-readable number: the top band encodes the logical tick and the bottom band
//! the rendered frame, each split into fixed-width digit cells, each digit drawn by
//! lighting the `ON_COLOR` vs the `OFF_COLOR` lattice pattern for that digit. The
//! runner decodes the exact top-left rectangle of each captured PNG and asserts it
//! equals the beat's (tick, frame), so a beat capture is machine-provable
//! evidence about *which simulated moment* it depicts.
//!
//! Palette contract (exact values, so the app and the runner share one truth): the
//! off pixels are near-black; the on pixels are a hard blue. `is_on` is the
//! shared decision: a pixel whose red, green, and blue all exceed `IS_ON_MIN`
//! reads as on. `OFF_COLOR` stays far below every threshold so the background can
//! never read as on.

/// Horizontal pixels of one digit cell including its right padding column.
pub const CELL_W: u32 = 4;
/// Vertical pixels of one digit band (the 3 lattice rows plus spare rows).
pub const CELL_H: u32 = 5;
/// Number of digits used to encode each of tick and frame.
pub const DIGITS: u32 = 6;
/// Lattice rows inside each cell used for the digit body.
pub const ROWS: u32 = 3;
/// Lattice columns inside each cell used for the digit body.
pub const COLS: u32 = 3;
/// Lattice pitch (on/off) threshold shared by every decoder: a pixel whose red,
/// green, and blue are all above this lane reads as "on".
pub const IS_ON_MIN: u8 = 60;
/// RGB the rendered chip paints when a lattice cell is "on".
pub const ON_COLOR: (u8, u8, u8) = (0x7f, 0xb8, 0xff);
/// RGB the rendered chip paints for the cell background.
pub const OFF_COLOR: (u8, u8, u8) = (0x05, 0x05, 0x06);

/// The chip block is anchored in the image's top-left corner at these pixel offsets.
#[must_use]
pub const fn chip_origin() -> (u32, u32) {
    (0, 0)
}

/// `(width, height)` of the full chip block in pixels.
#[must_use]
pub const fn chip_size() -> (u32, u32) {
    (DIGITS * CELL_W, 2 * CELL_H)
}

/// A single digit's 3x3 on/off pattern. Index is row then column.
#[must_use]
pub fn digit_pattern(digit: u8) -> [[bool; 3]; 3] {
    debug_assert!(digit < 10, "single decimal digit required");
    match digit {
        0 => [[true, true, true], [true, false, true], [true, true, true]],
        1 => [
            [false, true, false],
            [false, true, false],
            [false, true, false],
        ],
        2 => [[true, true, true], [false, true, true], [true, true, false]],
        3 => [[true, true, true], [false, true, true], [true, true, true]],
        4 => [
            [true, false, true],
            [true, true, true],
            [false, false, true],
        ],
        5 => [[true, true, false], [true, true, true], [true, true, true]],
        6 => [[true, true, false], [true, true, true], [true, false, true]],
        7 => [
            [true, true, true],
            [false, false, true],
            [false, false, true],
        ],
        8 => [[true, true, true], [true, true, true], [true, true, true]],
        9 => [[true, true, true], [true, true, true], [false, false, true]],
        _ => unreachable!("digits are 0..=9"),
    }
}

/// Split a value into its `DIGITS` digit cells, most significant first,
/// zero-padded. Values at or above `10^DIGITS` are truncated to the low
/// `DIGITS` digits.
#[must_use]
pub fn digit_cells(value: u64) -> [u8; 6] {
    let mut digits = [0u8; 6];
    let mut remaining = value;
    for slot in digits.iter_mut().rev() {
        *slot = (remaining % 10) as u8;
        remaining /= 10;
    }
    digits
}

/// Interpret a `[u8; 6]` of digit cells (most significant first) as a number.
#[must_use]
pub fn number_from_cells(digits: &[u8]) -> u64 {
    digits.iter().fold(0u64, |acc, &d| acc * 10 + u64::from(d))
}

/// Color of the rendered chip pixel at local `(px, py)` inside a
/// `(DIGITS*CELL_W, 2*CELL_H)` chip for tick `tick` and frame `frame`.
#[must_use]
pub fn chip_pixel(tick: u64, frame: u64, px: u32, py: u32) -> (u8, u8, u8) {
    let (w, h) = chip_size();
    if px >= w || py >= h {
        return OFF_COLOR;
    }
    let band = if py < CELL_H { tick } else { frame };
    let py_in_band = py % CELL_H;
    let cell = px / CELL_W;
    let inner_col = px % CELL_W;
    if cell >= DIGITS || inner_col >= COLS || py_in_band >= ROWS {
        return OFF_COLOR;
    }
    let digit = digit_cells(band)[cell as usize];
    if digit_pattern(digit)[py_in_band as usize][inner_col as usize] {
        ON_COLOR
    } else {
        OFF_COLOR
    }
}

/// Encode the full chip as an RGBA `width x height` row-major buffer
/// (`width = DIGITS*CELL_W`, `height = 2*CELL_H`). `0xff` alpha.
#[must_use]
pub fn encode_chip_rgba(tick: u64, frame: u64) -> Vec<u8> {
    let (width, height) = chip_size();
    let mut out = Vec::with_capacity((width * height * 4) as usize);
    for py in 0..height {
        for px in 0..width {
            let (red, green, blue) = chip_pixel(tick, frame, px, py);
            out.extend_from_slice(&[red, green, blue, 0xff]);
        }
    }
    out
}

/// Does an RGB triple read as "on" by the chip convention? Red, green, and blue
/// must all exceed [`IS_ON_MIN`]; `OFF_COLOR` never does.
#[must_use]
pub const fn is_on(r: u8, g: u8, b: u8) -> bool {
    r > IS_ON_MIN && g > IS_ON_MIN && b > IS_ON_MIN
}

/// Decode a tick and frame from a chip RGBA buffer of the expected dimensions.
///
/// # Errors
/// Returns a message when the buffer size is wrong or a digit lattice does not match
/// any known digit pattern, which means the capture does not show this chip.
pub fn decode_chip_rgba(rgba: &[u8]) -> Result<(u64, u64), String> {
    let (width, height) = chip_size();
    let expected = (width * height * 4) as usize;
    if rgba.len() != expected {
        return Err(format!(
            "frame-chip buffer size mismatch: got {} bytes, expected {expected}",
            rgba.len()
        ));
    }
    let at = |px: u32, py: u32| -> (u8, u8, u8) {
        let i = ((py * width + px) * 4) as usize;
        (rgba[i], rgba[i + 1], rgba[i + 2])
    };
    let read_band = |py_base: u32| -> Result<u64, String> {
        let mut value = 0u64;
        for cell in 0..DIGITS {
            let mut lattice = [[false; 3]; 3];
            for row in 0..ROWS {
                for col in 0..COLS {
                    let (red, green, blue) = at(cell * CELL_W + col, py_base + row);
                    lattice[row as usize][col as usize] = is_on(red, green, blue);
                }
            }
            let matched = (0..=9).find(|&d| digit_pattern(d) == lattice);
            let digit = matched.ok_or_else(|| {
                "frame-chip lattice does not match any digit (capture does not show the chip)"
                    .to_string()
            })?;
            value = value * 10 + u64::from(digit);
        }
        Ok(value)
    };
    let tick = read_band(0)?;
    let frame = read_band(CELL_H)?;
    Ok((tick, frame))
}

/// Crop the top-left chip block out of a row-major RGB(A) image buffer and decode
/// it. Accepts 3 bytes (RGB) or 4 bytes (RGBA) per pixel.
///
/// # Errors
/// Returns a message when `rgb` cannot contain a chip or the chip lattice does not
/// decode.
pub fn decode_chip_from_rgb(
    rgb: &[u8],
    bytes_per_pixel: usize,
    width: u32,
    height: u32,
) -> Result<(u64, u64), String> {
    let (chip_width, chip_height) = chip_size();
    let (ox, oy) = chip_origin();
    if width < ox + chip_width || height < oy + chip_height {
        return Err(format!(
            "image {width}x{height} too small to hold the {chip_width}x{chip_height} frame chip"
        ));
    }
    let mut buf = Vec::with_capacity((chip_width * chip_height * 4) as usize);
    for yy in oy..oy + chip_height {
        for xx in ox..ox + chip_width {
            let i = (yy * width + xx) as usize * bytes_per_pixel;
            let (red, green, blue) = (rgb[i], rgb[i + 1], rgb[i + 2]);
            buf.extend_from_slice(&[red, green, blue, 0xff]);
        }
    }
    decode_chip_rgba(&buf)
}

#[cfg(test)]
mod tests {
    use super::{
        decode_chip_from_rgb, decode_chip_rgba, digit_cells, digit_pattern, encode_chip_rgba,
        number_from_cells,
    };

    #[test]
    fn cells_roundtrip() {
        assert_eq!(digit_cells(0), [0; 6]);
        assert_eq!(digit_cells(7), [0, 0, 0, 0, 0, 7]);
        assert_eq!(digit_cells(987_654), [9, 8, 7, 6, 5, 4]);
        assert_eq!(number_from_cells(&digit_cells(123_456)), 123_456);
    }

    #[test]
    fn digits_match_the_documented_patterns() {
        assert_eq!(
            digit_pattern(0),
            [[true, true, true], [true, false, true], [true, true, true]]
        );
        assert_eq!(digit_pattern(8), [[true; 3]; 3]);
    }

    #[test]
    fn encode_decode_roundtrip() {
        for &(tick, frame) in &[(0u64, 0u64), (5, 42), (999_999, 0), (42, 123_456)] {
            let rgba = encode_chip_rgba(tick, frame);
            assert_eq!(
                decode_chip_rgba(&rgba).expect("chip decodes"),
                (tick, frame)
            );
        }
    }

    #[test]
    fn band_rows_are_vertically_separate() {
        let (tick, frame) = (12u64, 34u64);
        let rgba = encode_chip_rgba(tick, frame);
        assert_eq!(decode_chip_rgba(&rgba).expect("chip"), (12, 34));
        // The bands are offset by exactly one cell height; pick a lattice column
        // where the tick and frame digits differ so the bands read independently.
        assert!(chip_pixel_local_differs(tick, frame));
    }

    /// Whether the top/tick band and bottom/frame band read differently at some cell.
    fn chip_pixel_local_differs(tick: u64, frame: u64) -> bool {
        let cell = super::DIGITS - 1;
        let top = digit_pattern(super::digit_cells(tick)[cell as usize]);
        let bottom = digit_pattern(super::digit_cells(frame)[cell as usize]);
        top != bottom
    }

    #[test]
    fn wrong_size_rejected() {
        assert!(decode_chip_rgba(&[0u8; 3]).is_err());
    }

    #[test]
    fn tiny_rgb_image_with_chip_decodes() {
        // Simulate what the app writes: an RGB image whose top-left 24x10 block is
        // the chip and everything else dark.
        let (w, h) = super::chip_size();
        let rgba = super::encode_chip_rgba(77, 88);
        let mut rgb = Vec::with_capacity((w * h * 3) as usize);
        for chunk in rgba.as_chunks::<4>().0 {
            rgb.extend_from_slice(&[chunk[0], chunk[1], chunk[2]]);
        }
        assert_eq!(decode_chip_from_rgb(&rgb, 3, w, h).expect("chip"), (77, 88));
    }

    /// Paint one chip pixel with the opposite palette color (dark<->bright).
    fn flip_pixel(rgba: &mut [u8], width: u32, px: u32, py: u32) {
        let i = ((py * width + px) * 4) as usize;
        let (r, g, b) = (rgba[i], rgba[i + 1], rgba[i + 2]);
        let (nr, ng, nb) = if super::is_on(r, g, b) {
            super::OFF_COLOR
        } else {
            super::ON_COLOR
        };
        rgba[i..i + 3].copy_from_slice(&[nr, ng, nb]);
    }

    #[test]
    fn flipped_lattice_cell_is_rejected_by_both_decoders() {
        // Mutation check: the decoder is not a rubber stamp. Flip one lattice
        // cell of an encoded chip to the opposite palette color at a position
        // no digit pattern survives; both decode paths must return Err,
        // including the RGBA->RGB portability conversion the runner uses.
        let (tick, frame) = (0u64, 0u64);
        let (width, height) = super::chip_size();
        let mut rgba = encode_chip_rgba(tick, frame);
        assert_eq!(
            decode_chip_rgba(&rgba).expect("unmutated chip decodes"),
            (tick, frame)
        );
        // Pixel (0, 0) is digit 0's top-left lattice cell (on); paint it off.
        flip_pixel(&mut rgba, width, 0, 0);
        assert!(
            decode_chip_rgba(&rgba).is_err(),
            "a flipped lattice cell must not decode"
        );
        let mut rgb = Vec::with_capacity((width * height * 3) as usize);
        for chunk in rgba.as_chunks::<4>().0 {
            rgb.extend_from_slice(&[chunk[0], chunk[1], chunk[2]]);
        }
        assert!(
            decode_chip_from_rgb(&rgb, 3, width, height).is_err(),
            "a flipped lattice cell must not decode through the RGB path"
        );
    }

    #[test]
    fn tiny_generated_png_roundtrip() {
        // End-to-end through a real PNG decode: encode the chip, render a tiny
        // PNG from it, and decode it back through `decode_chip_from_rgb`.
        let (w, h) = super::chip_size();
        let rgba = super::encode_chip_rgba(123, 456);
        let mut rgb = Vec::with_capacity((w * h * 3) as usize);
        for chunk in rgba.as_chunks::<4>().0 {
            rgb.extend_from_slice(&[chunk[0], chunk[1], chunk[2]]);
        }
        let img = image::RgbImage::from_raw(w, h, rgb).expect("raw image");
        let mut bytes = std::io::Cursor::new(Vec::new());
        img.write_to(&mut bytes, image::ImageFormat::Png)
            .expect("png encode");
        let decoded = image::load_from_memory(&bytes.into_inner()).expect("png decode");
        let decoded = decoded.to_rgb8();
        assert_eq!(
            decode_chip_from_rgb(decoded.as_raw(), 3, decoded.width(), decoded.height())
                .expect("chip"),
            (123, 456)
        );
    }
}
