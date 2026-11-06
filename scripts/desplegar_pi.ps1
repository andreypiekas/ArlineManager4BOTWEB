# Envia o código deste computador para o Raspberry e reinicia os bots em execução.
#   scripts\desplegar_pi.bat              copia o código e reinicia os bots
#   scripts\desplegar_pi.bat -Instalar    primeira instalação: cria o ambiente e registra os serviços
#   scripts\desplegar_pi.bat -SinReiniciar  apenas copia
# Não copia dados, configurações individuais, credenciais nem sessões do Chrome: cada máquina mantém os seus
# (apenas config/defaults.ini, que faz parte do código).
# Usa a chave SSH %USERPROFILE%\.ssh\am4bot_pi (autorizada no Raspberry), sem senhas.
# O IP e o usuário do Raspberry não ficam no repositório: configure nas variáveis de ambiente
#   setx AM4BOT_PI_HOST 192.168.1.50      (ou nome, padrão raspberrypi.local)
#   setx AM4BOT_PI_USER pi                (padrão pi)
# ou informe em cada execução: scripts\desplegar_pi.bat -Equipo 192.168.1.50 -Usuario pi
param(
    [string]$Equipo = $env:AM4BOT_PI_HOST,
    [string]$Usuario = $env:AM4BOT_PI_USER,
    [string[]]$Perfiles = @('principal', 'secundario'),
    [switch]$Instalar,
    [switch]$SinReiniciar
)
$ErrorActionPreference = 'Stop'
if (-not $Equipo) { $Equipo = 'raspberrypi.local' }
if (-not $Usuario) { $Usuario = 'pi' }
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$key = Join-Path $env:USERPROFILE '.ssh\am4bot_pi'
if (-not (Test-Path $key)) { throw "Chave SSH não encontrada: $key" }
$destino = "$Usuario@$Equipo"
$opciones = @('-i', $key, '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=accept-new', '-o', 'ConnectTimeout=10')

function Remoto([string]$script) {
    # Enviado como arquivo (UTF-8 sem BOM e quebras de linha Linux): PowerShell 5.1 adiciona BOM ao que
    # passa pela entrada padrão do SSH, e o Bash não reconhece esse prefixo.
    $local = Join-Path $env:TEMP 'am4bot-desplegar.sh'
    [IO.File]::WriteAllText($local, ($script -replace "`r", ''), (New-Object System.Text.UTF8Encoding $false))
    & scp.exe @opciones -q $local "${destino}:/tmp/am4bot-desplegar.sh"
    if ($LASTEXITCODE -ne 0) { throw 'Não foi possível copiar o script de instalação.' }
    Remove-Item $local
    & ssh.exe @opciones $destino 'bash /tmp/am4bot-desplegar.sh; s=$?; rm -f /tmp/am4bot-desplegar.sh; exit $s'
    if ($LASTEXITCODE -ne 0) { throw "O Raspberry retornou um erro ($LASTEXITCODE)." }
}

Write-Host "1/3 Empacotando o código ..."
$paquete = Join-Path $env:TEMP 'am4bot-codigo.tgz'
& tar.exe -czf $paquete --exclude '__pycache__' --exclude '*.pyc' src assets scripts config/defaults.ini requirements.txt README.md
if ($LASTEXITCODE -ne 0) { throw 'Não foi possível empacotar o código.' }

Write-Host "2/3 Copiando para $Equipo ..."
& scp.exe @opciones -q $paquete "${destino}:/tmp/am4bot-codigo.tgz"
if ($LASTEXITCODE -ne 0) { throw 'Não foi possível copiar o código (o Raspberry está ligado?).' }
Remove-Item $paquete

Write-Host "3/3 Instalando no Raspberry ..."
$servicios = ($Perfiles | ForEach-Object { "am4bot@$_" }) -join ' '
$script = @'
set -e
mkdir -p ~/AirlineManager4Bot && cd ~/AirlineManager4Bot
old_req="$(cat requirements.txt 2>/dev/null || true)"
rm -rf src assets scripts
tar -xzf /tmp/am4bot-codigo.tgz && rm -f /tmp/am4bot-codigo.tgz
[ -x .venv/bin/python ] || python3 -m venv .venv
if [ "$old_req" != "$(cat requirements.txt)" ] || [ ! -f .venv/.instalado ]; then
  echo "   instalando dependências do Python ..."
  .venv/bin/pip install -q --upgrade pip && .venv/bin/pip install -q -r requirements.txt && touch .venv/.instalado
fi
if [ "__INSTALAR__" = "1" ]; then
  # Instala a unidade systemd com o usuário e a pasta pessoal desta conta.
  sed -e "s|^User=.*|User=$(id -un)|" -e "s|/home/pi/AirlineManager4Bot|$HOME/AirlineManager4Bot|g" \
    scripts/raspberry/am4bot@.service | sudo tee /etc/systemd/system/am4bot@.service >/dev/null
  sudo systemctl daemon-reload
  sudo systemctl enable __SERVICIOS__ >/dev/null 2>&1
  echo "   serviços ativados: __SERVICIOS__"
fi
if [ "__REINICIAR__" = "1" ]; then
  for s in __SERVICIOS__; do
    if [ "__INSTALAR__" = "1" ]; then sudo systemctl restart "$s"; else sudo systemctl try-restart "$s"; fi
    echo "   $s: $(systemctl is-active "$s")"
  done
fi
echo "   código atualizado: $(date '+%d/%m/%Y %H:%M')"
'@
$script = $script.Replace('__INSTALAR__', $(if ($Instalar) { '1' } else { '0' })).Replace('__REINICIAR__', $(if ($SinReiniciar) { '0' } else { '1' })).Replace('__SERVICIOS__', $servicios)
Remoto $script
Write-Host "Concluído. Painéis: http://${Equipo}:8744 (principal) e http://${Equipo}:8745 (secundario)."
