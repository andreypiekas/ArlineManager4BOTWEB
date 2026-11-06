# Abre o painel web do Airline Manager 4 Bot. Se não houver bot em execução (desktop
# ou web), inicia o bot em modo web (sem janela) neste terminal e abre o navegador.
# Para interromper: scripts\web_parar.bat (fecha o Chrome corretamente), ou Ctrl+C neste terminal.
# Outro perfil (outra conta no jogo): web.bat -Perfil realismo
param([string]$Perfil = '')
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$env:PYTHONUTF8 = '1'
if ($Perfil -and $Perfil -ne 'principal') { $dir = "profiles\$Perfil" } else { $Perfil = ''; $dir = 'config' }

function Read-Ini([string]$path, [string]$section, [string]$key) {
    if (-not (Test-Path $path)) { return $null }
    $current = ''
    foreach ($line in Get-Content $path -Encoding UTF8) {
        if ($line -match '^\s*\[(.+?)\]\s*$') { $current = $Matches[1]; continue }
        if ($current -eq $section -and $line -match "^\s*$([regex]::Escape($key))\s*=\s*(.*?)\s*$") { return $Matches[1] }
    }
    return $null
}

$port = Read-Ini "$dir\settings.ini" 'web' 'port'
if (-not $port) { $port = Read-Ini 'config\defaults.ini' 'web' 'port' }
if (-not $port) { $port = '8744' }
$token = Read-Ini "$dir\secrets.ini" 'web' 'token'
$url = "http://127.0.0.1:$port/"
if ($token) { $url += "?token=$token" }

if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
    Write-Host "Airline Manager 4 Bot já está em execução: abrindo o painel."
    Start-Process $url
    exit 0
}
if (-not (Test-Path '.venv\Scripts\python.exe')) {
    Write-Host 'O ambiente .venv não existe. Crie o ambiente antes (veja README: python -m venv .venv e pip install -r requirements.txt).'
    Read-Host 'Pressione Enter para fechar'
    exit 1
}

# O navegador abre alguns segundos depois, quando o servidor estiver pronto.
Start-Process powershell -WindowStyle Hidden -ArgumentList '-NoProfile', '-Command', "Start-Sleep -Seconds 4; Start-Process '$url'"
if ($Perfil) {
    & '.venv\Scripts\python.exe' 'src\main.py' '--web' '--profile' $Perfil
} else {
    & '.venv\Scripts\python.exe' 'src\main.py' '--web'
}
if ($LASTEXITCODE -ne 0) { Read-Host 'O bot foi encerrado com erro. Pressione Enter para fechar' }
