@echo off
setlocal
cd /d "%~dp0.."
where cargo >nul 2>&1
if errorlevel 1 (echo cargo required.&exit /b 2)
cargo build --offline --release --manifest-path "native\rust\Cargo.toml"
if errorlevel 1 exit /b %ERRORLEVEL%
"native\rust\target\release\cosmic_fruit_fly_neural_step.exe" "native\fixtures\step4.txt"
exit /b %ERRORLEVEL%
