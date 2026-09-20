@echo off
setlocal
cd /d "%~dp0.."
where py >nul 2>&1
if %ERRORLEVEL% EQU 0 (set "PY=py -3") else (set "PY=python")
set "PYTHONPATH=%CD%\..;%CD%"
if not exist "outputs\neural_dependency\runs.jsonl" (
 echo Run RUN_NEURAL_EXPERIMENT.bat first.
 exit /b 2
)
where ffmpeg >nul 2>&1
if errorlevel 1 (echo ffmpeg is required on PATH.&exit /b 2)
%PY% render_neural_dependency.py --out "outputs\neural_dependency" --output "outputs\neural_dependency\neural_replay.mp4"
exit /b %ERRORLEVEL%
