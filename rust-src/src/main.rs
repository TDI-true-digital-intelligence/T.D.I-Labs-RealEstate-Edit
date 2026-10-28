// realestate-cli — CLI wrapper: realestate-cli <input> <output> <preset>
use std::env;
fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 4 {
        eprintln!("usage: realestate-cli <input> <output> <preset>");
        eprintln!("presets: {}", realestate_engine::Preset::presets().join(", "));
        std::process::exit(2);
    }
    let img = image::open(&args[1]).unwrap_or_else(|e| { eprintln!("open error: {e}"); std::process::exit(1); });
    let name = &args[3];
    let preset = if let Some(v) = name.strip_prefix("bright:") {
        realestate_engine::Preset::brightness_only(v.parse().unwrap_or(0.3))
    } else {
        realestate_engine::Preset::named(name).unwrap_or_else(|| { eprintln!("unknown preset"); std::process::exit(2); })
    };
    let out = realestate_engine::process(&img, &preset);
    out.save(&args[2]).unwrap_or_else(|e| { eprintln!("save error: {e}"); std::process::exit(1); });
    println!("ok: {} -> {} [{}]", args[1], args[2], args[3]);
}
