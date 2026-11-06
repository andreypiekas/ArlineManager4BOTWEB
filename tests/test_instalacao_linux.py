"""Testes do instalador Linux sem usar sudo, rede ou um navegador real."""
from __future__ import annotations

import importlib.util
import os
import subprocess
from configparser import ConfigParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("configurar_linux", ROOT / "scripts/configurar_linux.py")
assert SPEC and SPEC.loader
modulo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(modulo)


@pytest.fixture
def projeto(tmp_path: Path) -> Path:
    (tmp_path / "config").mkdir()
    (tmp_path / "config/defaults.ini").write_text(
        "[web]\nport = 8744\nhost = 127.0.0.1\n\n[options]\ndry_run = off\n",
        encoding="utf-8",
    )
    return tmp_path


def ler_cfg(path: Path) -> ConfigParser:
    cfg = ConfigParser(interpolation=None)
    cfg.read(path, encoding="utf-8")
    return cfg


def test_nova_instalacao_eh_simulacao_e_privada(projeto: Path):
    porta, novo, login = modulo.configurar(projeto, "principal", False, False)
    cfg = ler_cfg(projeto / "config/settings.ini")
    assert (porta, novo, login) == (8744, True, False)
    assert cfg.getboolean("options", "headless")
    assert cfg.getboolean("options", "start_on_launch")
    assert cfg.getboolean("options", "dry_run")
    assert cfg.get("web", "enabled") == "on"
    assert not (projeto / "config/secrets.ini").exists()
    assert (os.stat(projeto / "config/settings.ini").st_mode & 0o777) == 0o600


def test_reinstalacao_preserva_credenciais_e_simulacao_desligada(projeto: Path):
    modulo.configurar(projeto, "principal", False, False)
    cfg = ler_cfg(projeto / "config/settings.ini")
    cfg.set("options", "dry_run", "off")
    cfg.add_section("settings")
    cfg.set("settings", "cash_reserve", "987654")
    modulo.salvar_privado(projeto / "config/settings.ini", cfg)

    segredos = ConfigParser(interpolation=None)
    segredos.add_section("login")
    segredos.set("login", "username", "piloto@example.com")
    segredos.set("login", "password", "segredo-exemplo")
    modulo.salvar_privado(projeto / "config/secrets.ini", segredos)

    porta, novo, login = modulo.configurar(projeto, "principal", False, False)
    cfg2 = ler_cfg(projeto / "config/settings.ini")
    sec2 = ler_cfg(projeto / "config/secrets.ini")
    assert (porta, novo, login) == (8744, False, True)
    assert cfg2.get("settings", "cash_reserve") == "987654"
    assert not cfg2.getboolean("options", "dry_run")
    assert sec2.get("login", "password") == "segredo-exemplo"


def test_rede_local_gera_token_e_reinstalacao_nao_troca(projeto: Path, capsys):
    modulo.configurar(projeto, "principal", True, False)
    sec_file = projeto / "config/secrets.ini"
    token = ler_cfg(sec_file).get("web", "token")
    assert len(token) >= 32
    assert (os.stat(sec_file).st_mode & 0o777) == 0o600
    assert ler_cfg(projeto / "config/settings.ini").get("web", "host") == "0.0.0.0"
    modulo.configurar(projeto, "principal", True, False)
    assert ler_cfg(sec_file).get("web", "token") == token
    modulo.mostrar_acesso(projeto, "principal", "192.168.1.17")
    assert f"http://192.168.1.17:8744/?token={token}" in capsys.readouterr().out


def test_perfis_usam_portas_distintas(projeto: Path):
    modulo.configurar(projeto, "principal", False, False)
    assert modulo.configurar(projeto, "base-a", False, False)[0] == 8745
    assert modulo.configurar(projeto, "base-b", False, False)[0] == 8746
    assert modulo.configurar(projeto, "base-a", False, False)[0] == 8745
    assert (projeto / "profiles/base-a/settings.ini").exists()


@pytest.mark.parametrize("perfil", ["../etc", "inválido", "a/b", "a b", ""])
def test_perfil_invalido_rejeitado(perfil: str):
    with pytest.raises(ValueError):
        modulo.validar_perfil(perfil)


def test_bash_sintaxe_e_ajuda_sem_efeitos_colaterais():
    script = ROOT / "instalar.sh"
    assert subprocess.run(["bash", "-n", str(script)], check=False).returncode == 0
    ajuda = subprocess.run(["bash", str(script), "--ajuda"], check=True, capture_output=True, text=True)
    assert "--rede-local" in ajuda.stdout
    assert "--sem-iniciar" in ajuda.stdout
    assert "SIMULAÇÃO" in ajuda.stdout

def test_token_de_exemplo_nao_pode_ser_usado_na_lan(projeto: Path):
    segredos = ConfigParser(interpolation=None)
    segredos.add_section("web")
    segredos.set("web", "token", "change-me-to-a-long-random-string")
    modulo.salvar_privado(projeto / "config/secrets.ini", segredos)

    modulo.configurar(projeto, "principal", True, False)
    token = ler_cfg(projeto / "config/secrets.ini").get("web", "token")
    assert token != "change-me-to-a-long-random-string"
    assert len(token) >= 32


def test_login_ssh_interativo_usa_stdin_e_senha_oculta(monkeypatch):
    import builtins
    import sys

    class Terminal:
        @staticmethod
        def isatty() -> bool:
            return True

    cfg = ConfigParser(interpolation=None)
    monkeypatch.setattr(sys, "stdin", Terminal())
    monkeypatch.setattr(builtins, "input", lambda prompt: "piloto@example.com")
    chamadas = []
    monkeypatch.setattr(
        modulo.getpass, "getpass",
        lambda prompt, **kwargs: (chamadas.append((prompt, kwargs)), "senha-teste")[1],
    )
    assert modulo.configurar_login(cfg) is True
    assert cfg.get("login", "username") == "piloto@example.com"
    assert cfg.get("login", "password") == "senha-teste"
    assert chamadas == [("Senha do jogo (não será exibida): ", {})]


def test_login_ssh_sem_stdin_interativo_usa_dev_tty(monkeypatch):
    import builtins
    import sys

    class Terminal:
        @staticmethod
        def isatty() -> bool:
            return False

    # Em /dev/tty real, escrever o prompt não sobrescreve a entrada.
    class TtyFake:
        def __init__(self):
            self.prompt = ""

        def write(self, texto):
            self.prompt += texto

        def flush(self):
            pass

        def readline(self):
            return "segundo@example.com\n"

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    cfg = ConfigParser(interpolation=None)
    monkeypatch.setattr(sys, "stdin", Terminal())
    monkeypatch.setattr(builtins, "open", lambda path, *args, **kwargs: TtyFake() if path == "/dev/tty" else None)
    monkeypatch.setattr(modulo.getpass, "getpass", lambda prompt, stream=None: "senha-de-teste")
    assert modulo.configurar_login(cfg) is True
    assert cfg.get("login", "username") == "segundo@example.com"
    assert cfg.get("login", "password") == "senha-de-teste"


def test_login_sem_terminal_retorna_erro_claro_e_nao_altera_config(monkeypatch):
    import builtins
    import sys

    class Terminal:
        @staticmethod
        def isatty() -> bool:
            return False

    cfg = ConfigParser(interpolation=None)
    monkeypatch.setattr(sys, "stdin", Terminal())

    def sem_terminal(*args, **kwargs):
        raise OSError("No such device")

    monkeypatch.setattr(builtins, "open", sem_terminal)
    with pytest.raises(RuntimeError, match="ssh -t"):
        modulo.configurar_login(cfg)
    assert not cfg.has_section("login")


def test_login_getpass_sem_echo_falha_em_vez_de_expor_senha(monkeypatch):
    import builtins
    import getpass
    import sys
    import warnings

    class Terminal:
        @staticmethod
        def isatty() -> bool:
            return True

    cfg = ConfigParser(interpolation=None)
    monkeypatch.setattr(sys, "stdin", Terminal())
    monkeypatch.setattr(builtins, "input", lambda prompt: "piloto@example.com")

    def senha_com_echo(prompt):
        warnings.warn("Password input may be echoed.", getpass.GetPassWarning, stacklevel=2)
        return "nao-usar"

    monkeypatch.setattr(modulo.getpass, "getpass", senha_com_echo)
    with pytest.raises(RuntimeError, match="terminal interativo"):
        modulo.configurar_login(cfg)
    assert not cfg.has_section("login")
