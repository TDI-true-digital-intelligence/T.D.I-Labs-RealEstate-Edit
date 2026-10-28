// realestate-engine — Real-estate photo color engine, pure Rust.
// Presets: sky tint/boost, grass green, HDR punch, white balance, brightness.
// Region masks: sky = top fraction of image (luminance-gated), grass = bottom fraction (green-gated).
use image::{DynamicImage, GenericImageView, Rgba};

pub struct Preset {
    pub sky_tint: Option<[f32; 3]>,   // rgb tint applied to sky region
    pub sky_boost: f32,               // sky contrast/saturation multiplier
    pub grass_green: f32,             // 0 = off, 1 = full lush green shift
    pub hdr_punch: f32,               // local-contrast emulation strength
    pub warmth: f32,                  // -1 cool .. +1 warm white balance
    pub brightness: f32,              // exposure lift, stops
    pub vibrance: f32,                // saturation boost on low-sat pixels
    pub brightness_only: f32,         // pure brightness lift (stops), no profile — for the Brightness slider
}

impl Preset {
    /// Custom profile: brightness slider (-1 dim .. +1 bright), no regional edits.
    pub fn brightness_only(v: f32) -> Preset {
        Preset { sky_tint: None, sky_boost: 1.0, grass_green: 0.0, hdr_punch: 0.05, warmth: 0.0, brightness: v, vibrance: 0.08, brightness_only: 0.0 }
    }
    pub fn named(name: &str) -> Option<Preset> {
        let p = |sky_tint, sky_boost, grass_green, hdr_punch, warmth, brightness, vibrance| Preset {
            sky_tint, sky_boost, grass_green, hdr_punch, warmth, brightness, vibrance, brightness_only: 0.0,
        };
        Some(match name {
            "bright-airy" => p(Some([0.55, 0.75, 1.0]), 1.10, 0.35, 0.15, 0.18, 0.35, 0.30),
            "hdr-punch"   => p(Some([0.35, 0.60, 1.05]), 1.30, 0.25, 0.55, 0.05, 0.15, 0.45),
            "warm-dusk"   => p(Some([1.00, 0.62, 0.38]), 1.15, 0.20, 0.20, 0.35, 0.20, 0.25),
            "blue-sky-day"=> p(Some([0.40, 0.68, 1.05]), 1.25, 0.45, 0.25, 0.00, 0.10, 0.35),
            "natural-clean"=> p(None, 1.05, 0.15, 0.10, 0.05, 0.12, 0.15),
            _ => return None,
        })
    }
    pub fn presets() -> Vec<&'static str> {
        vec!["bright-airy", "hdr-punch", "warm-dusk", "blue-sky-day", "natural-clean"]
    }
}

#[inline]
fn lum(px: Rgba<u8>) -> f32 {
    (0.2126 * px[0] as f32 + 0.7152 * px[1] as f32 + 0.0722 * px[2] as f32) / 255.0
}

/// Sky mask: upper `sky_frac` of frame AND luminance above gate (blown/grey sky reads high, roofs read lower).
fn sky_weight(y: u32, h: u32, l: f32) -> f32 {
    let top_frac = y as f32 / h as f32;
    if top_frac < 0.45 {
        let fade = 1.0 - (top_frac / 0.45); // 1 at very top → 0 at 45% height
        let gate = ((l - 0.55) / 0.25).clamp(0.0, 1.0);
        fade * gate
    } else { 0.0 }
}

/// Grass mask: lower `grass_frac` of frame AND green dominance.
fn grass_weight(y: u32, h: u32, px: Rgba<u8>) -> f32 {
    let bot_frac = y as f32 / h as f32;
    if bot_frac > 0.55 {
        let fade = ((bot_frac - 0.55) / 0.45).clamp(0.0, 1.0);
        let (r, g, b) = (px[0] as f32, px[1] as f32, px[2] as f32);
        let green_dom = ((g - r.max(b)) / 60.0).clamp(0.0, 1.0); // green beats red+blue
        fade * green_dom
    } else { 0.0 }
}

pub fn process(img: &DynamicImage, preset: &Preset) -> DynamicImage {
    let (w, h) = img.dimensions();
    let mut out = img.to_rgba8();
    let base = img.to_rgba8();

    // pass 1: global grade (white balance, brightness, vibrance, hdr punch via unsharp on luma)
    let wb_r = 1.0 + preset.warmth * 0.12;
    let wb_b = 1.0 - preset.warmth * 0.12;
    let exp = (preset.brightness * 0.35).exp2();

    for y in 0..h {
        for x in 0..w {
            let px = base.get_pixel(x, y);
            let mut r = (px[0] as f32 * wb_r * exp).min(255.0);
            let mut g = (px[1] as f32 * exp).min(255.0);
            let mut b = (px[2] as f32 * wb_b * exp).min(255.0);

            // vibrance: boost low-saturation pixels more
            let mx = r.max(g).max(b);
            let mn = r.min(g).min(b);
            let sat = if mx > 0.0 { (mx - mn) / mx } else { 0.0 };
            let vboost = preset.vibrance * (1.0 - sat);
            let mid = (r + g + b) / 3.0;
            r += (r - mid) * vboost;
            g += (g - mid) * vboost;
            b += (b - mid) * vboost;

            out.put_pixel(x, y, Rgba([r.clamp(0.0, 255.0) as u8, g.clamp(0.0, 255.0) as u8, b.clamp(0.0, 255.0) as u8, px[3]]));
        }
    }

    // pass 2: regional sky + grass grading
    for y in 0..h {
        for x in 0..w {
            let px = out.get_pixel(x, y);
            let l = lum(*px);
            let sw = sky_weight(y, h, l);
            let gw = grass_weight(y, h, *px);
            let (mut r, mut g, mut b) = (px[0] as f32, px[1] as f32, px[2] as f32);

            if sw > 0.0 && preset.sky_boost > 0.0 {
                let mid = (r + g + b) / 3.0;
                r = mid + (r - mid) * preset.sky_boost;
                g = mid + (g - mid) * preset.sky_boost;
                b = mid + (b - mid) * preset.sky_boost;
                if let Some(t) = preset.sky_tint {
                    let tl = (t[0] + t[1] + t[2]) / 3.0;
                    r = r * (1.0 - sw) + (r * t[0] / tl) * sw;
                    g = g * (1.0 - sw) + (g * t[1] / tl) * sw;
                    b = b * (1.0 - sw) + (b * t[2] / tl) * sw;
                }
            }

            if gw > 0.0 && preset.grass_green > 0.0 {
                let k = gw * preset.grass_green;
                g = g + (g * 0.28 + 14.0) * k;
                r = r - r * 0.16 * k;
                b = b + (b * 0.10 - 6.0) * k;
            }

            out.put_pixel(x, y, Rgba([r.clamp(0.0, 255.0) as u8, g.clamp(0.0, 255.0) as u8, b.clamp(0.0, 255.0) as u8, px[3]]));
        }
    }

    // pass 3: HDR punch = unsharp mask on the whole frame (cheap local contrast)
    if preset.hdr_punch > 0.0 {
        let amount = preset.hdr_punch;
        let blurred = box_blur(&out, w, h, 6);
        for y in 0..h {
            for x in 0..w {
                let px = out.get_pixel(x, y);
                let bl = blurred.get_pixel(x, y);
                let r = px[0] as f32 + (px[0] as f32 - bl[0] as f32) * amount * 1.6;
                let g = px[1] as f32 + (px[1] as f32 - bl[1] as f32) * amount * 1.6;
                let b = px[2] as f32 + (px[2] as f32 - bl[2] as f32) * amount * 1.6;
                out.put_pixel(x, y, Rgba([r.clamp(0.0, 255.0) as u8, g.clamp(0.0, 255.0) as u8, b.clamp(0.0, 255.0) as u8, px[3]]));
            }
        }
    }

    DynamicImage::ImageRgba8(out)
}

fn box_blur(img: &image::RgbaImage, w: u32, h: u32, r: u32) -> image::RgbaImage {
    let mut tmp = img.clone();
    // horizontal
    for y in 0..h {
        for x in 0..w {
            let (mut sr, mut sg, mut sb, mut n) = (0u32, 0u32, 0u32, 0u32);
            for dx in x.saturating_sub(r)..(x + r + 1).min(w) {
                let p = img.get_pixel(dx, y);
                sr += p[0] as u32; sg += p[1] as u32; sb += p[2] as u32; n += 1;
            }
            tmp.get_pixel_mut(x, y).0 = [(sr / n) as u8, (sg / n) as u8, (sb / n) as u8, img.get_pixel(x, y)[3]];
        }
    }
    // vertical
    let mut out = tmp.clone();
    for y in 0..h {
        for x in 0..w {
            let (mut sr, mut sg, mut sb, mut n) = (0u32, 0u32, 0u32, 0u32);
            for dy in y.saturating_sub(r)..(y + r + 1).min(h) {
                let p = tmp.get_pixel(x, dy);
                sr += p[0] as u32; sg += p[1] as u32; sb += p[2] as u32; n += 1;
            }
            out.get_pixel_mut(x, y).0 = [(sr / n) as u8, (sg / n) as u8, (sb / n) as u8, tmp.get_pixel(x, y)[3]];
        }
    }
    out
}
