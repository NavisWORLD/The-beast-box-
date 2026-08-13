param(
    [string]$Python = "python",
    [string]$EnvDir = ".venv",
    [switch]$DirectGGUF
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
Write-Host "Run: $EnvDir\Scripts\cosmic.cypher-cli.exe doctor"
