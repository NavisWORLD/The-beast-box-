@echo off
setlocal
cd /d "%~dp0.."
where py >nul 2>&1
if %ERRORLEVEL% EQU 0 (set "PY=py -3") else (set "PY=python")
set "PYTHONPATH=%CD%\..;%CD%"
%PY% -m pytest -q tests
exit /b %ERRORLEVEL%
