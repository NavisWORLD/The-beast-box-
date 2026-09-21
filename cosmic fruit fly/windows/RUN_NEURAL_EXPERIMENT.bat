@echo off
setlocal
cd /d "%~dp0.."
where py >nul 2>&1
if %ERRORLEVEL% EQU 0 (set "PY=py -3") else (set "PY=python")
set "PYTHONPATH=%CD%\..;%CD%"
if not exist "outputs" mkdir "outputs"
%PY% neural_dependency.py --seeds 8 --output "outputs\neural_dependency"
exit /b %ERRORLEVEL%
