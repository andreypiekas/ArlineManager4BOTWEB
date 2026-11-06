# Instalação fácil no Raspberry Pi OS e Ubuntu

Instalador destinado a **Raspberry Pi OS (Debian Bookworm/Trixie)** e **Ubuntu 22.04+**. O programa roda em segundo plano, com painel web e serviço `systemd`, sem interface gráfica local. Recomendamos **Raspberry Pi OS 64 bits** nos Raspberry Pi 3/4/5.

## Instalação pelo terminal

Copie e execute o comando no próprio Raspberry Pi ou computador Ubuntu:

```bash
git clone https://github.com/andreypiekas/ArlineManager4BOTWEB.git
cd ArlineManager4BOTWEB
bash instalar.sh --rede-local
```

**Atalho para instalação automática sem clonar antes:** confira o conteúdo do arquivo remoto antes de executá-lo. Uma alternativa é:

```bash
curl -fsSL https://raw.githubusercontent.com/andreypiekas/ArlineManager4BOTWEB/main/instalar.sh -o instalar.sh
bash instalar.sh --rede-local
```

Nesse segundo método, o script baixa o projeto em `$HOME/AirlineManager4Bot`. Se executado de dentro do clone, ele usa a pasta do clone e não cria uma cópia duplicada.

O script instala via APT Python, Tk e dependências básicas; no **Raspberry Pi OS/Debian**, instala `chromium` e `chromium-driver`. No **Ubuntu**, instala os pacotes de transição para Chromium distribuído por Snap. Cria `.venv`, instala `requirements.txt` isoladamente, prepara as configurações do perfil, registra `am4bot@.service` e habilita a inicialização no boot.

### Primeiro acesso

Ao final, o instalador mostra um endereço semelhante a:

```text
http://192.168.1.50:8744/?token=TOKEN_GERADO_AUTOMATICAMENTE
```

Esse endereço funciona **somente na rede local** quando foi usado `--rede-local`. O token é secreto: **não compartilhe**, não exponha a porta 8744 na internet e não publique o arquivo `config/secrets.ini`. Sem `--rede-local`, o painel fica disponível apenas em `http://127.0.0.1:8744/` no próprio Linux (pode acessar por túnel SSH).

### Firewall UFW no Ubuntu e Debian

Ao usar `--rede-local`, o instalador agora verifica automaticamente se o **UFW está ativo**. Se estiver, identifica a sub-rede da interface de rede do IP do servidor e cria uma regra de entrada **TCP restrita àquela rede**, para a porta real do perfil (por padrão, 8744). Por exemplo, um servidor com `192.168.101.234/24` recebe a regra equivalente a:

```bash
sudo ufw allow from 192.168.101.0/24 to any port 8744 proto tcp
```

Não é necessário executar esse comando manualmente quando a detecção automática funcionar. O instalador **não ativa o UFW**, não abre a porta para `any`/`0.0.0.0/0`, não remove regras já existentes e não modifica o SSH. Reexecutar a instalação mantém as configurações do bot e usa a verificação de regras duplicadas do próprio UFW.

Se o servidor possuir várias interfaces, VPNs ou redes Docker, indique a sub-rede que poderá acessar o painel (deve ser um CIDR IPv4 privado):

```bash
bash instalar.sh --rede-local --ufw-rede 192.168.101.0/24
```

Se preferir administrar o firewall por conta própria, use `--sem-ufw`. Se a detecção de rede falhar, o script **não abre nenhuma porta**: apresenta um aviso e solicita a opção `--ufw-rede`. Consulte:

```bash
sudo ufw status numbered
sudo ss -lntp | grep ':8744'
```

Uma regra antiga que já permita `8744/tcp` a partir de `Anywhere` **continua existindo**, pois o instalador não apaga regras do administrador. Revise e remova regras públicas desnecessárias de forma consciente. Não encaminhe a porta do painel no roteador para a internet.

A senha do jogo **não é solicitada por padrão**. Para configurá-la sem mostrá-la no terminal, execute o instalador com `--configurar-login`, ou rode depois:

```bash
python3 scripts/configurar_linux.py --configurar-login
sudo systemctl restart am4bot@principal
```

Os dados ficam em `config/secrets.ini` com permissão somente para o proprietário. O instalador não grava credenciais nos arquivos de código, nos logs ou na unidade systemd.

**Segurança da primeira execução:** perfis novos são criados com `dry_run = on` (simulação). O painel permite revisar configurações e acompanhar o bot. Desative a opção **Simulação (sem gastos)** na aba Opções somente quando a configuração estiver correta. Uma reinstalação **não reativa** a simulação se você já a desativou.

### Gerenciar o bot

```bash
sudo systemctl status am4bot@principal
sudo systemctl restart am4bot@principal
sudo systemctl stop am4bot@principal
sudo systemctl start am4bot@principal
sudo journalctl -u am4bot@principal -f
```

Para conferir o endereço e o token novamente:

```bash
python3 scripts/configurar_linux.py --mostrar-acesso --ip 192.168.1.50
```

### Perfis diferentes

O perfil `principal` usa a porta 8744. O instalador escolhe automaticamente outra porta livre entre os perfis configurados para novos perfis:

```bash
bash instalar.sh --rede-local --perfil companhia2
sudo systemctl status am4bot@companhia2
```

Cada perfil possui seus próprios dados, credenciais, ajustes e sessão Chromium. Não execute o mesmo perfil em dois dispositivos simultaneamente.

### Opções

| Opção | Resultado |
| --- | --- |
| `--rede-local` | Habilita acesso LAN, gera token e ajusta o UFW ativo apenas para a sub-rede detectada |
| `--ufw-rede 192.168.101.0/24` | Define explicitamente a sub-rede privada autorizada no UFW (requer `--rede-local`) |
| `--sem-ufw` | Não altera o UFW, mesmo quando o painel é habilitado na LAN |
| `--configurar-login` | Solicita e-mail/senha por meio de um terminal interativo |
| `--perfil companhia2` | Configura serviço para outro perfil |
| `--sem-iniciar` | Registra e habilita o serviço sem ligá-lo imediatamente |
| `--diretorio /caminho` | Usa um diretório de instalação personalizado, sem espaços |
| `--verificar` | Inspeciona distribuição, arquitetura e executáveis sem instalar |
| `--ajuda` | Exibe ajuda do instalador |

### Atualização e reinstalação

Se você instalou dentro do clone do GitHub:

```bash
cd ~/ArlineManager4BOTWEB
git pull --ff-only
bash instalar.sh --rede-local
```

Se utilizou o atalho de instalação em `~/AirlineManager4Bot`:

```bash
cd ~/AirlineManager4Bot
git pull --ff-only
bash instalar.sh --rede-local
```

O instalador **não executa `git reset`**, não remove arquivos de dados e não substitui credenciais. Se houver alterações locais incompatíveis com o `git pull`, resolva-as antes de atualizar. Nunca copie manualmente o mesmo diretório de sessão do Chrome com o serviço ativo.

### Diagnóstico

- Confirme o sistema: `bash instalar.sh --verificar`.
- Se o painel responder no próprio servidor mas der timeout em outros computadores, confirme `--rede-local`, a porta do perfil e o UFW com `sudo ufw status numbered`. Caso necessário, execute `bash instalar.sh --rede-local --ufw-rede 192.168.101.0/24`, ajustando a faixa à sua rede.
- Confira os eventos: `sudo journalctl -u am4bot@principal -n 100 --no-pager`.
- Se o Chromium ou o ChromeDriver não iniciar, confira `chromium --version` (Raspberry Pi OS) ou `chromium-browser --version` (Ubuntu) e `chromedriver --version`. No Ubuntu, confirme `snap list chromium`.
- No Ubuntu minimal ou contêiner, `snapd` exige serviços do sistema ativos; instalações sem `systemd` não são suportadas.
- Se `python3 scripts/configurar_linux.py --configurar-login` mostrar `Não foi possível acessar um terminal interativo`, abra uma sessão com TTY (por exemplo, `ssh -t usuario@servidor`) ou utilize o terminal integrado do servidor. O script lê e-mail pelo terminal e senha com eco desativado; não passe a senha como argumento de linha de comando.
- Caso o ambiente não forneça terminal interativo (contêiner, cron ou SSH sem alocação de TTY), configure as credenciais editando `config/secrets.ini` com uma seção `[login]`, as chaves `username` e `password`; depois execute `chmod 600 config/secrets.ini` e `sudo systemctl restart am4bot@principal`. Preserve todas as outras seções existentes.
- Não atribua permissões globais ao `config/secrets.ini` e não exponha a porta web na internet.
- O instalador é validado com testes de configuração e sintaxe; a navegação real do Selenium precisa ser conferida no dispositivo de destino.

### ChromeDriver encerra inesperadamente (Ubuntu)

Se os registros mostrarem `HTTPConnectionPool(host='localhost', port=...)` com `Connection refused`, o Selenium perdeu a comunicação com o **ChromeDriver local**. A porta aleatória é interna ao Selenium, não é a porta 8744 do painel e não envolve a regra UFW.

Se a reinicialização falhar com `Service /usr/bin/chromedriver unexpectedly exited. Status code was: 1`, possíveis causas incluem Chromium Snap, uma sessão de usuário necessária ao Snap indisponível, incompatibilidade entre navegador/driver ou o encerramento do navegador por falta de memória. O código 1 sozinho não determina a causa.

O bot atualizado captura a saída do processo ChromeDriver em **`data/logs/chromedriver.log`**, arquivo com permissões 0600. Em perfis adicionais, usa `profiles/NOME/data/logs/chromedriver.log`. O log pode conter detalhes de navegação: remova dados sensíveis antes de compartilhá-lo.

Comandos para diagnóstico, executados no servidor como usuário da instalação:

~~~bash
cd ~/AirlineManager4Bot
tail -n 80 data/logs/chromedriver.log
chromedriver --version
chromium-browser --version
snap list chromium
sudo systemctl status am4bot@principal --no-pager
sudo journalctl -u am4bot@principal -n 120 --no-pager
free -h
df -h
sudo journalctl -k --since "30 minutes ago" --no-pager | grep -Ei 'oom|out.of.memory|killed process|chrom|snap|apparmor'
~~~

No Ubuntu com Chromium Snap, verifique a disponibilidade do driver sem uma sessão interativa:

~~~bash
USUARIO=$(systemctl show am4bot@principal -p User --value)
sudo -u "$USUARIO" -H chromedriver --version
loginctl show-user "$USUARIO" -p Linger
~~~

Dependendo da configuração do Snap e do gerenciador de sessão, pode ser necessário habilitar o **linger** para o usuário do serviço, mas apenas se a investigação comprovar que essa é a causa. Não apague a sessão persistente do Chrome nem encerre todos os processos Chrome do servidor indiscriminadamente.

### Referências

- [Raspberry Pi OS: Python e ambientes virtuais](https://www.raspberrypi.com/documentation/computers/os.html)
- [Ubuntu: pacote Chromium distribuído por Snap](https://ubuntu.com/blog/chromium-in-ubuntu-deb-to-snap-transition)
