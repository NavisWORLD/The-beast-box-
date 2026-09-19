@echo off
setlocal
if defined BEASTBOX_PYTHON (
  "%BEASTBOX_PYTHON%" "%~dp0install.py" %*
) else (
  python "%~dp0install.py" %*
)
exit /b %errorlevel%
