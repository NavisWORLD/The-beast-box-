$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host '== Rust toolchain =='
rustc --version
cargo --version

Write-Host '== Workspace tests =='
cargo test --workspace --locked

Write-Host '== Release build =='
cargo build --release --workspace --locked

$Bin = Join-Path $Root 'target/release/cosmic-cypher-rs.exe'

Write-Host '== CLI smoke =='
& $Bin phi 1024
& $Bin affinity '0,0,0' '1,1,1' 0.75
& $Bin dyn12 '0,0,0,0,0,0,0,0,0,0,0,0' '0.2,-0.1' 0
& $Bin lorenz '1,1,1' 0.01

Write-Host 'RUST_BEASTBOX_VERIFY=PASS'
