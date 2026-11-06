#!/usr/bin/env python3
"""Abre apenas a porta TCP do painel AM4 para a sub-rede local quando o UFW está ativo.

Não ativa o firewall, não altera regras existentes e não abre a porta para
0.0.0.0/0. Em redes com várias interfaces, use --rede CIDR explicitamente.
"""
from __future__ import annotations

import argparse
import ipaddress
import os
import re
import shutil
import subprocess
import sys
from configparser import ConfigParser
from pathlib import Path

REDES_PRIVADAS = tuple(
    ipaddress.ip_network(bloco)
    for bloco in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
)


def rede_permitida(rede: ipaddress.IPv4Network) -> bool:
    return any(rede.subnet_of(privada) for privada in REDES_PRIVADAS)


def validar_rede(valor: str) -> ipaddress.IPv4Network:
    try:
        rede = ipaddress.ip_network(valor, strict=False)
    except ValueError as exc:
        raise ValueError(f"Rede inválida: {valor!r}. Informe um CIDR IPv4, por exemplo 192.168.101.0/24.") from exc
    if not isinstance(rede, ipaddress.IPv4Network) or not rede_permitida(rede):
        raise ValueError("Por segurança, a origem do UFW deve estar dentro de uma rede IPv4 privada (RFC 1918).")
    return rede


def detectar_rede(ip_servidor: str = "") -> ipaddress.IPv4Network | None:
    """Descobre a rede da interface que possui o IP exibido ao usuário.

    Não usa apenas hostname -I para deduzir uma máscara inexistente, nem
    configura regras para interfaces diferentes se o IP informado não coincidir.
    """
    executavel_ip = shutil.which("ip") or ("/usr/sbin/ip" if Path("/usr/sbin/ip").is_file() else None)
    if not executavel_ip:
        return None
    try:
        resultado = subprocess.run(
            [executavel_ip, "-o", "-4", "addr", "show", "scope", "global"],
            capture_output=True, text=True, check=False, timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if resultado.returncode != 0:
        return None
    for linha in resultado.stdout.splitlines():
        correspondencia = re.search(r"\binet\s+(\d{1,3}(?:\.\d{1,3}){3}/\d{1,2})\b", linha)
        if not correspondencia:
            continue
        try:
            interface = ipaddress.ip_interface(correspondencia.group(1))
        except ValueError:
            continue
        if not isinstance(interface, ipaddress.IPv4Interface):
            continue
        if ip_servidor and str(interface.ip) != ip_servidor:
            continue
        if rede_permitida(interface.network):
            return interface.network
    return None


def porta_painel(diretorio: Path, perfil: str) -> int:
    configuracao = ConfigParser(interpolation=None)
    pasta = diretorio / "config" if perfil == "principal" else diretorio / "profiles" / perfil
    configuracao.read(
        [diretorio / "config" / "defaults.ini", pasta / "settings.ini"],
        encoding="utf-8",
    )
    porta = configuracao.getint("web", "port", fallback=8744)
    if not 1 <= porta <= 65535:
        raise ValueError(f"Porta do painel inválida: {porta}.")
    return porta


def ufw_disponivel() -> bool:
    """Considera instalações em /usr/sbin, mesmo fora do PATH do usuário comum."""
    return bool(shutil.which("ufw") or Path("/usr/sbin/ufw").is_file())


def configurar_ufw(diretorio: Path, perfil: str, ip_servidor: str = "", rede_manual: str = "") -> bool:
    """Retorna True somente quando a regra foi aplicada/verificada pelo UFW."""
    if not ufw_disponivel():
        print("[AM4] UFW não instalado; nenhuma alteração de firewall necessária.")
        return False
    ambiente = {**os.environ, "LC_ALL": "C"}
    try:
        status = subprocess.run(
            ["sudo", "ufw", "status"], capture_output=True, text=True,
            check=False, timeout=15, env=ambiente,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"[AM4] AVISO: não foi possível consultar o UFW ({exc}); não alterei o firewall.")
        return False
    if status.returncode != 0:
        print("[AM4] AVISO: erro ao consultar o UFW; nenhuma regra foi criada.")
        return False
    if not re.search(r"^Status:\s+active\s*$", status.stdout, re.MULTILINE | re.IGNORECASE):
        print("[AM4] UFW inativo; não vou ativá-lo nem modificar suas regras.")
        return False

    rede = validar_rede(rede_manual) if rede_manual else detectar_rede(ip_servidor)
    if rede is None:
        print(
            "[AM4] AVISO: UFW ativo, mas não identifiquei a sub-rede LAN. "
            "Nenhuma porta foi aberta. Execute novamente com "
            "--rede-local --ufw-rede 192.168.101.0/24 (ajuste ao seu ambiente)."
        )
        return False

    porta = porta_painel(diretorio, perfil)
    comando = [
        "sudo", "ufw", "allow", "from", str(rede), "to", "any",
        "port", str(porta), "proto", "tcp",
        "comment", f"AM4 Bot {perfil}",
    ]
    try:
        aplicado = subprocess.run(
            comando, capture_output=True, text=True, check=False, timeout=20, env=ambiente,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"[AM4] AVISO: não foi possível configurar o UFW ({exc}).")
        return False
    if aplicado.returncode != 0:
        detalhe = (aplicado.stderr or aplicado.stdout).strip()
        print(f"[AM4] AVISO: falha ao liberar a porta {porta} no UFW: {detalhe}")
        return False
    print(f"[AM4] UFW: acesso TCP à porta {porta} permitido apenas a partir de {rede}.")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Configura o acesso LAN ao painel AM4 com regras restritivas de UFW.")
    parser.add_argument("--diretorio", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--perfil", default="principal")
    parser.add_argument("--ip", default="", help="IP do servidor na rede local (para detectar a interface correta)")
    parser.add_argument("--rede", default="", help="CIDR da rede autorizada, por exemplo 192.168.101.0/24")
    argumentos = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,23}", argumentos.perfil):
        parser.error("Nome de perfil inválido.")
    try:
        configurar_ufw(argumentos.diretorio, argumentos.perfil, argumentos.ip, argumentos.rede)
    except ValueError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
