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
