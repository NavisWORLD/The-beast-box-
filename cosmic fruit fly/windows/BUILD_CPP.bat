@echo off
setlocal
cd /d "%~dp0.."
where g++ >nul 2>&1
if errorlevel 1 (echo g++ required. Install MSYS2/MinGW or use a C++17 compiler.&exit /b 2)
if not exist "outputs" mkdir "outputs"
g++ -O2 -std=c++17 "native\cpp\neural_step.cpp" -o "outputs\fly_neural_step.exe"
if errorlevel 1 exit /b %ERRORLEVEL%
"outputs\fly_neural_step.exe" "native\fixtures\step4.txt"
exit /b %ERRORLEVEL%
