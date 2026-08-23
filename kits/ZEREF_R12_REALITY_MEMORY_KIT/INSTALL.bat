@echo off
setlocal
cd /d "%~dp0\..\.."

where py >nul 2>nul
if %errorlevel%==0 (
  set "PY=py -3"
) else (
  set "PY=python"
)

if not exist .venv (
  %PY% -m venv .venv || exit /b 1
)
call .venv\Scripts\activate.bat || exit /b 1
python -m pip install --upgrade pip || exit /b 1
pip install -e ".[dev,ml]" || exit /b 1
beastbox init || exit /b 1
beastbox doctor || exit /b 1
python kits\ZEREF_R12_REALITY_MEMORY_KIT\verify_kit.py --repo-root . || exit /b 1
beastbox zeref status || exit /b 1
echo.
echo Zeref R12 kit installed and verified.
exit /b 0
