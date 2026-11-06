"""Testes da abertura segura da LAN via UFW, sem alterar o firewall real."""
from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("configurar_ufw", ROOT / "scripts/configurar_ufw.py")
assert SPEC and SPEC.loader
ufw = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ufw)

IP_SAIDA = (
    "2: enp0s3    inet 192.168.101.234/24 brd 192.168.101.255 "
    "scope global dynamic noprefixroute enp0s3\n"
    "3: docker0    inet 172.17.0.1/16 brd 172.17.255.255 "
    "scope global docker0\n"
)


@pytest.fixture
def projeto(tmp_path: Path) -> Path:
    (tmp_path / "config").mkdir()
    (tmp_path / "config/defaults.ini").write_text(
        "[web]\nport = 8744\nhost = 127.0.0.1\n", encoding="utf-8",
    )
    return tmp_path


def simular_ufw(monkeypatch, *, ativo=True, ip_saida=IP_SAIDA):
    chamadas = []
    monkeypatch.setattr(ufw, "ufw_disponivel", lambda: True)
    monkeypatch.setattr(ufw.shutil, "which", lambda nome: "/usr/bin/ip" if nome == "ip" else None)

    def executar(cmd, **_kwargs):
        chamadas.append(cmd)
        if cmd[:3] == ["sudo", "ufw", "status"]:
            return subprocess.CompletedProcess(
                cmd, 0, stdout="Status: active\n" if ativo else "Status: inactive\n",
            )
        if cmd[0] == "/usr/bin/ip":
            return subprocess.CompletedProcess(cmd, 0, stdout=ip_saida)
        if cmd[:3] == ["sudo", "ufw", "allow"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="Rule added\n")
        raise AssertionError(f"Comando inesperado: {cmd}")

    monkeypatch.setattr(ufw.subprocess, "run", executar)
    return chamadas


def test_ufw_ativo_abre_somente_a_subrede_do_servidor(monkeypatch, projeto, capsys):
    chamadas = simular_ufw(monkeypatch)
    assert ufw.configurar_ufw(projeto, "principal", "192.168.101.234")
    regra = chamadas[-1]
    assert regra == [
        "sudo", "ufw", "allow", "from", "192.168.101.0/24", "to", "any",
        "port", "8744", "proto", "tcp", "comment", "AM4 Bot principal",
    ]
    assert "porta 8744" in capsys.readouterr().out
    assert ["sudo", "ufw", "enable"] not in chamadas
    assert ["sudo", "ufw", "disable"] not in chamadas


def test_ufw_inativo_nao_eh_ativado(monkeypatch, projeto):
    chamadas = simular_ufw(monkeypatch, ativo=False)
    assert not ufw.configurar_ufw(projeto, "principal", "192.168.101.234")
    assert chamadas == [["sudo", "ufw", "status"]]


def test_ufw_inexistente_nao_gera_comando(monkeypatch, projeto):
    monkeypatch.setattr(ufw, "ufw_disponivel", lambda: False)
    chamadas = []
    monkeypatch.setattr(ufw.subprocess, "run", lambda *args, **kwargs: chamadas.append(args))
    assert not ufw.configurar_ufw(projeto, "principal", "192.168.101.234")
    assert chamadas == []


def test_ip_desconhecido_nao_abre_regra_de_outra_interface(monkeypatch, projeto, capsys):
    chamadas = simular_ufw(monkeypatch)
    assert not ufw.configurar_ufw(projeto, "principal", "192.168.200.100")
    assert all(cmd[:3] != ["sudo", "ufw", "allow"] for cmd in chamadas)
    assert "--ufw-rede" in capsys.readouterr().out


def test_ufw_permanece_restrito_a_rede_privada_escolhida(monkeypatch, projeto):
    chamadas = simular_ufw(monkeypatch)
    assert ufw.configurar_ufw(projeto, "principal", "192.168.101.234", "10.20.30.0/24")
    assert chamadas[-1][3:5] == ["from", "10.20.30.0/24"]
    assert all(cmd[0:3] != ["sudo", "ufw", "delete"] for cmd in chamadas)


@pytest.mark.parametrize("rede", [
    "0.0.0.0/0", "1.2.3.0/24", "2001:db8::/64", "192.168.0.0/8", "texto",
])
def test_origens_publicas_ou_invalidas_sao_rejeitadas(rede):
    with pytest.raises(ValueError):
        ufw.validar_rede(rede)


def test_porta_personalizada_do_perfil_eh_respeitada(monkeypatch, projeto):
    (projeto / "profiles/base-a").mkdir(parents=True)
    (projeto / "profiles/base-a/settings.ini").write_text(
        "[web]\nport = 8749\n", encoding="utf-8",
    )
    chamadas = simular_ufw(monkeypatch)
    assert ufw.configurar_ufw(projeto, "base-a", "192.168.101.234")
    assert chamadas[-1][8] == "8749"
    assert chamadas[-1][-1] == "AM4 Bot base-a"


def test_ajuda_do_instalador_contem_as_opcoes_ufw():
    texto = (ROOT / "instalar.sh").read_text(encoding="utf-8")
    assert "--ufw-rede CIDR" in texto
    assert "--sem-ufw" in texto
    assert 'if ((REDE_LOCAL && ! SEM_UFW)); then' in texto
    assert 'scripts/configurar_ufw.py' in texto
