@echo off
setlocal
cd /d "%~dp0\..\.."
if not exist .venv\Scripts\activate.bat (
  echo Run kits\ZEREF_R12_REALITY_MEMORY_KIT\INSTALL.bat first.
  exit /b 1
)
call .venv\Scripts\activate.bat
beastbox verify || exit /b 1
set "CP=models\ZEREF-DAD-SON-TALK-004\checkpoint.pt"
if exist "%CP%" (
  beastbox zeref chat --checkpoint "%CP%"
) else (
  echo Full TALK-004 checkpoint is not present in this source checkout.
  echo Showing verified Zeref/R12 status instead. Download the full kit artifact for local checkpoint chat.
  beastbox zeref status
)
