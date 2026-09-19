use cst_core::{gaussian_affinity, lorenz_step, phos_ffn_width, update_dyn12, PHI};
use std::env;
use std::process::ExitCode;

fn parse_vec(raw: &str) -> Result<Vec<f64>, String> {
    raw.split(',').filter(|s| !s.trim().is_empty()).map(|s| s.trim().parse::<f64>().map_err(|e| format!("invalid float {s:?}: {e}"))).collect()
}

fn help() {
    eprintln!("cosmic-cypher-rs\n\ncommands:\n  phi [d_model]                 print phi and optional PHOS FFN width\n  affinity A B [sigma]          Gaussian affinity for comma vectors\n  dyn12 STATE DRIVE [step]      update exactly 12 comma scalars\n  lorenz X,Y,Z [dt]             one Lorenz step (10,28,8/3)\n");
}

fn main() -> ExitCode {
    match real_main() {
        Ok(()) => ExitCode::SUCCESS,
        Err(msg) => { eprintln!("error: {msg}"); ExitCode::from(2) }
    }
}

fn real_main() -> Result<(), String> {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 { help(); return Ok(()); }
    match args[1].as_str() {
        "phi" => {
            println!("phi={PHI:.15}");
            if let Some(raw) = args.get(2) {
                let d: usize = raw.parse().map_err(|e| format!("invalid d_model: {e}"))?;
                println!("phos_ffn_width={}", phos_ffn_width(d));
            }
        }
        "affinity" => {
            let a = parse_vec(args.get(2).ok_or("missing A")?)?;
            let b = parse_vec(args.get(3).ok_or("missing B")?)?;
            let sigma: f64 = args.get(4).map(|s| s.parse()).transpose().map_err(|e| format!("invalid sigma: {e}"))?.unwrap_or(0.75);
            println!("{:.15}", gaussian_affinity(&a, &b, sigma).map_err(|e| e.to_string())?);
        }
        "dyn12" => {
            let raw_state = parse_vec(args.get(2).ok_or("missing STATE")?)?;
            if raw_state.len() != 12 { return Err(format!("STATE must have 12 scalars, got {}", raw_state.len())); }
            let mut state = [0.0; 12]; state.copy_from_slice(&raw_state);
            let drive = parse_vec(args.get(3).ok_or("missing DRIVE")?)?;
            let step: u64 = args.get(4).map(|s| s.parse()).transpose().map_err(|e| format!("invalid step: {e}"))?.unwrap_or(0);
            let out = update_dyn12(&state, &drive, step).map_err(|e| e.to_string())?;
            println!("{}", out.iter().map(|x| format!("{x:.12}")).collect::<Vec<_>>().join(","));
        }
        "lorenz" => {
            let raw = parse_vec(args.get(2).ok_or("missing X,Y,Z")?)?;
            if raw.len() != 3 { return Err("Lorenz state must have exactly 3 values".into()); }
            let dt: f64 = args.get(3).map(|s| s.parse()).transpose().map_err(|e| format!("invalid dt: {e}"))?.unwrap_or(0.01);
            let out = lorenz_step([raw[0], raw[1], raw[2]], dt, 10.0, 28.0, 8.0 / 3.0);
            println!("{:.12},{:.12},{:.12}", out[0], out[1], out[2]);
        }
        "help" | "--help" | "-h" => help(),
        other => return Err(format!("unknown command {other:?}")),
    }
    Ok(())
}
