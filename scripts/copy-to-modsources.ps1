[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$source = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$modSources = Join-Path $env:USERPROFILE "Documents\My Games\Terraria\tModLoader\ModSources"
$destination = Join-Path $modSources "HyperTerraria"

New-Item -ItemType Directory -Path $modSources -Force | Out-Null

if (Test-Path $destination) {
    $item = Get-Item $destination -Force
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw "O destino é um link simbólico. Remova-o antes de executar o script de cópia: $destination"
    }
}

# robocopy retorna códigos de 0 a 7 para execuções bem-sucedidas.
& robocopy $source $destination /E /PURGE /XD .git bin obj /XF *.tmod
$exitCode = $LASTEXITCODE

if ($exitCode -ge 8) {
    throw "Falha ao copiar o projeto. Código do robocopy: $exitCode"
}

Write-Host "HyperTerraria copiado para:"
Write-Host $destination

