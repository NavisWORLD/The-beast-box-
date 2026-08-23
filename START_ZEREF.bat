@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    set "PY=py -3"
) else (
    set "PY=python"
)

if not exist ".venv\Scripts\python.exe" (
    echo [Zeref] Creating local Python environment...
    %PY% -m venv .venv || goto :error
    ".venv\Scripts\python.exe" -m pip install --upgrade pip || goto :error
    ".venv\Scripts\python.exe" -m pip install -e . || goto :error
)

".venv\Scripts\python.exe" -m beastbox.cypher.easy_ollama %*
exit /b %errorlevel%

:error
echo.
echo Zeref setup failed. Make sure Python 3.10+ and Ollama are installed.
exit /b 1
