[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$source = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$modSources = Join-Path $env:USERPROFILE "Documents\My Games\Terraria\tModLoader\ModSources"
$destination = Join-Path $modSources "HyperTerraria"

New-Item -ItemType Directory -Path $modSources -Force | Out-Null

if (Test-Path $destination) {
    throw "O destino já existe. Remova ou renomeie antes de criar o link: $destination"
}

try {
    New-Item -ItemType SymbolicLink -Path $destination -Target $source | Out-Null
}
catch {
    throw @"
Não foi possível criar o link simbólico.
Ative o Modo de Desenvolvedor do Windows ou execute o PowerShell como administrador.
Detalhe: $($_.Exception.Message)
"@
}

Write-Host "Link simbólico criado:"
Write-Host "$destination -> $source"

