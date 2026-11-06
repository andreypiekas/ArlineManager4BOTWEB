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
| `--rede-local` | Habilita acesso pela LAN e gera token aleatório seguro se necessário |
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
- Confira os eventos: `sudo journalctl -u am4bot@principal -n 100 --no-pager`.
- Se o Chromium ou o ChromeDriver não iniciar, confira `chromium --version` (Raspberry Pi OS) ou `chromium-browser --version` (Ubuntu) e `chromedriver --version`. No Ubuntu, confirme `snap list chromium`.
- No Ubuntu minimal ou contêiner, `snapd` exige serviços do sistema ativos; instalações sem `systemd` não são suportadas.
- Não atribua permissões globais ao `config/secrets.ini` e não exponha a porta web na internet.
- O instalador é validado com testes de configuração e sintaxe; a navegação real do Selenium precisa ser conferida no dispositivo de destino.

### Referências

- [Raspberry Pi OS: Python e ambientes virtuais](https://www.raspberrypi.com/documentation/computers/os.html)
- [Ubuntu: pacote Chromium distribuído por Snap](https://ubuntu.com/blog/chromium-in-ubuntu-deb-to-snap-transition)
