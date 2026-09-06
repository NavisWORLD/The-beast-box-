//! Native Rust process client; JSON and durable state are handled by Beast.
use std::{env, process::{Command, ExitCode}};
fn main() -> ExitCode {
    let args: Vec<String> = env::args().skip(1).collect();
    if args.len() < 2 {
        eprintln!("Usage: beast-client PYTHON DATA_DIR [runtime model options]\nJSON request on stdin");
        return ExitCode::from(2);
    }
    match Command::new(&args[0]).args(["-m", "beastbox", "runtime", "exchange", "--data-dir"])
        .arg(&args[1]).args(&args[2..]).status() {
        Ok(status) => ExitCode::from(status.code().unwrap_or(2) as u8),
        Err(_) => { eprintln!("Cannot start configured Beast Python runtime"); ExitCode::from(2) }
    }
}
