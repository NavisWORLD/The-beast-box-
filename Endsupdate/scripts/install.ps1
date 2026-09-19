param(
    [ValidateSet('core','quantum','hf','huggingface','ml','full','dev')]
    [string]$Extra = 'core',
    [string]$Python = 'python'
)

$ErrorActionPreference = 'Stop'
& $Python -m venv .venv
$Py = Join-Path $PWD '.venv\Scripts\python.exe'
& $Py -m pip install --upgrade pip setuptools wheel
switch ($Extra) {
    'core'        { & $Py -m pip install -e . }
    'quantum'     { & $Py -m pip install -e '.[quantum]' }
    'hf'          { & $Py -m pip install -e '.[huggingface]' }
    'huggingface' { & $Py -m pip install -e '.[huggingface]' }
    'ml'          { & $Py -m pip install -e '.[ml]' }
    'full'        { & $Py -m pip install -e '.[full]' }
    'dev'         { & $Py -m pip install -e '.[dev]' }
}
& (Join-Path $PWD '.venv\Scripts\beastbox.exe') doctor
