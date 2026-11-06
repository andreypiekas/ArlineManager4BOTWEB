# Para o Airline Manager 4 Bot (modo web ou desktop): solicita que o bot pare e feche
# o Chrome, aguarda o encerramento e, como último recurso, finaliza o processo à força.
# Outro perfil: web_parar.bat -Perfil realismo
param([string]$Perfil = '')
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
if ($Perfil -and $Perfil -ne 'principal') { $dir = "profiles\$Perfil"; $session = "profiles\$Perfil\session" } else { $dir = 'config'; $session = 'config\session' }

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
$listening = { Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue }

$pids = & $listening | Select-Object -ExpandProperty OwningProcess -Unique
if (-not $pids) {
    Write-Host "Airline Manager 4 Bot não estava em execução (nenhum serviço na porta $port)."
    Start-Sleep -Seconds 2
    exit 0
}
foreach ($id in $pids) {
    $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId=$id").CommandLine
    if ($cmd -notlike '*main.py*') {
        Write-Host "A porta $port está sendo usada por outro programa (PID $id); preservando o processo: $cmd"
        Start-Sleep -Seconds 4
        exit 1
    }
}

Write-Host 'Parando o bot (fechando o Chrome) ...'
try {
    $headers = @{ 'X-AM4' = '1' }
    if ($token) { $headers['X-Token'] = $token }
    Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:$port/api/control" -Headers $headers `
        -ContentType 'application/json' -Body '{"action": "quit"}' -TimeoutSec 5 | Out-Null
} catch {
    Write-Host "O painel não respondeu ($($_.Exception.Message))."
}
$deadline = (Get-Date).AddSeconds(45)
while ((Get-Date) -lt $deadline -and (& $listening)) { Start-Sleep -Seconds 1 }

if (& $listening) {
    Write-Host 'O processo não terminou no prazo: encerrando à força.'
    foreach ($id in $pids) { Stop-Process -Id $id -Force -ErrorAction SilentlyContinue }
    # Fecha sessões do Chrome que permaneceram abertas no perfil do bot
    Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'chrome.exe' -and $_.CommandLine -like "*AirlineManager4Bot\$session*" } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
}
Write-Host 'Airline Manager 4 Bot parado.'
Start-Sleep -Seconds 2
