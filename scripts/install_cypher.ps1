param(
    [string]$Python = "python",
    [string]$EnvDir = ".venv",
    [switch]$DirectGGUF,
    [switch]$SetupZeref
)
$ErrorActionPreference = "Stop"
& $Python -m venv $EnvDir
$Py = Join-Path $EnvDir "Scripts\python.exe"
& $Py -m pip install --upgrade pip
if ($DirectGGUF) {
    & $Py -m pip install -e ".[local-llm]"
} else {
    & $Py -m pip install -e .
}
Write-Host "Cosmic Cypher installed."
Write-Host "Easy Ollama launch: $EnvDir\Scripts\zeref.exe"
Write-Host "Or double-click START_ZEREF.bat"
if ($SetupZeref) {
    & $Py -m beastbox.cypher.easy_ollama --setup-only
}
