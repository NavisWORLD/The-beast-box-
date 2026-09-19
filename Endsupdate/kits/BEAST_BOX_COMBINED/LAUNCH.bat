@echo off
setlocal
if defined BEASTBOX_PYTHON (
  "%BEASTBOX_PYTHON%" "%~dp0launch.py" %*
) else (
  python "%~dp0launch.py" %*
)
exit /b %errorlevel%
