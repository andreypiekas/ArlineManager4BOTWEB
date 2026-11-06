#!/usr/bin/env python3
"""Configuração segura e idempotente do AM4 Bot em Linux (somente biblioteca padrão)."""
from __future__ import annotations

import argparse
import getpass
import os
import re
import secrets
import sys
import tempfile
import warnings
from configparser import ConfigParser
from pathlib import Path
from urllib.parse import quote

PERFIL_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,23}$")
PORTA_INICIAL = 8744


def carregar(caminho: Path) -> ConfigParser:
    cfg = ConfigParser(interpolation=None)
    if caminho.is_file():
        with caminho.open(encoding="utf-8") as arquivo:
            cfg.read_file(arquivo)
    return cfg


def definir(cfg: ConfigParser, secao: str, chave: str, valor: str) -> None:
    if not cfg.has_section(secao):
        cfg.add_section(secao)
    cfg.set(secao, chave, valor)


def salvar_privado(caminho: Path, cfg: ConfigParser) -> None:
    """Grava atomicamente; nunca publica segredos com permissão de grupo ou outros."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    fd, temporario = tempfile.mkstemp(prefix=".am4-", dir=caminho.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as arquivo:
            cfg.write(arquivo)
            arquivo.flush()
            os.fsync(arquivo.fileno())
        os.replace(temporario, caminho)
        os.chmod(caminho, 0o600)
    finally:
        if os.path.exists(temporario):
            os.unlink(temporario)


def validar_perfil(perfil: str) -> str:
    perfil = perfil.strip().lower()
    if perfil != "principal" and not PERFIL_RE.fullmatch(perfil):
        raise ValueError("Perfil inválido: use até 24 caracteres (a-z, 0-9, _ e -).")
    return perfil


def arquivos(root: Path, perfil: str) -> tuple[Path, Path]:
    base = root / "config" if perfil == "principal" else root / "profiles" / perfil
    return base / "settings.ini", base / "secrets.ini"


def porta_perfil(root: Path, perfil: str, atual: ConfigParser) -> int:
    defaults = carregar(root / "config" / "defaults.ini")
    if perfil == "principal":
        return atual.getint("web", "port", fallback=defaults.getint("web", "port", fallback=PORTA_INICIAL))
    if atual.has_option("web", "port"):
        return atual.getint("web", "port")
    usadas = {defaults.getint("web", "port", fallback=PORTA_INICIAL)}
    principal = carregar(root / "config" / "settings.ini")
    if principal.has_option("web", "port"):
        usadas.add(principal.getint("web", "port"))
    for caminho in (root / "profiles").glob("*/settings.ini"):
        if caminho.parent.name == perfil:
            continue
        outro = carregar(caminho)
        if outro.has_option("web", "port"):
            usadas.add(outro.getint("web", "port"))
    porta = PORTA_INICIAL + 1
    while porta in usadas:
        porta += 1
    return porta


def configurar_login(secrets_cfg: ConfigParser) -> bool:
    """Lê as credenciais de um terminal real, com senha oculta e sem expô-la em argumentos.

    Em SSH e em certos terminais, stdin é interativo mesmo quando /dev/tty
    não está acessível. Por isso, tenta stdin primeiro; /dev/tty é apenas
    uma alternativa quando stdin está redirecionado.
    """
    pergunta_email = "E-mail do jogo (Enter para cancelar): "
    pergunta_senha = "Senha do jogo (não será exibida): "
    try:
        if sys.stdin.isatty():
            usuario = input(pergunta_email).strip()
            if not usuario:
                return False
            with warnings.catch_warnings():
                # getpass pode usar leitura visível se não conseguir desativar echo.
                # Falhar é mais seguro do que expor a senha no terminal.
                warnings.simplefilter("error", getpass.GetPassWarning)
                senha = getpass.getpass(pergunta_senha)
        else:
            with open("/dev/tty", "r+", encoding="utf-8") as tty:
                tty.write(pergunta_email)
                tty.flush()
                usuario = tty.readline().strip()
                if not usuario:
                    return False
                with warnings.catch_warnings():
                    warnings.simplefilter("error", getpass.GetPassWarning)
                    senha = getpass.getpass(pergunta_senha, stream=tty)
    except (OSError, EOFError, getpass.GetPassWarning):
        raise RuntimeError(
            "Não foi possível acessar um terminal interativo com entrada de senha oculta. "
            "Execute no terminal normal ou via 'ssh -t usuario@servidor'; "
            "alternativamente, edite config/secrets.ini e aplique chmod 600."
        ) from None
    if not senha:
        raise ValueError("Senha vazia: credenciais não alteradas.")
    definir(secrets_cfg, "login", "username", usuario)
    definir(secrets_cfg, "login", "password", senha)
    return True


def configurar(root: Path, perfil: str, rede_local: bool, login: bool) -> tuple[int, bool, bool]:
    if not (root / "config" / "defaults.ini").is_file():
        raise FileNotFoundError("Não encontrei config/defaults.ini no repositório.")
    settings_path, secrets_path = arquivos(root, perfil)
    nova_instalacao = not settings_path.exists()
    settings = carregar(settings_path)
    segredos = carregar(secrets_path)
    porta = porta_perfil(root, perfil, settings)

    definir(settings, "options", "headless", "on")
    definir(settings, "options", "start_on_launch", "on")
    # Um perfil novo começa em modo seguro: sem compras/decolagens reais.
    if nova_instalacao:
        definir(settings, "options", "dry_run", "on")
    definir(settings, "web", "enabled", "on")
    if perfil != "principal" and not settings.has_option("web", "port"):
        definir(settings, "web", "port", str(porta))
    if rede_local:
        definir(settings, "web", "host", "0.0.0.0")
        token = segredos.get("web", "token", fallback="").strip()
        if not token or token == "change-me-to-a-long-random-string":
            # Impede expor na LAN o token público de config/secrets.example.ini.
            definir(segredos, "web", "token", secrets.token_urlsafe(32))

    if login:
        configurar_login(segredos)

    salvar_privado(settings_path, settings)
    if rede_local or login or secrets_path.exists():
        salvar_privado(secrets_path, segredos)
    return porta, nova_instalacao, bool(segredos.get("login", "username", fallback="").strip())


def mostrar_acesso(root: Path, perfil: str, ip: str) -> None:
    settings_path, secrets_path = arquivos(root, perfil)
    settings = carregar(settings_path)
    segredos = carregar(secrets_path)
    porta = porta_perfil(root, perfil, settings)
    host = settings.get("web", "host", fallback="127.0.0.1")
    if host not in ("0.0.0.0", "::"):
        ip = "127.0.0.1"
    token = segredos.get("web", "token", fallback="")
    url = f"http://{ip}:{porta}/"
    if token:
        url += "?token=" + quote(token, safe="")
    print("Painel:", url)
    if host in ("0.0.0.0", "::"):
        print("Acesso apenas pela rede local. Nunca encaminhe a porta na internet.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Configura o AM4 Bot para Raspberry Pi OS/Ubuntu.")
    parser.add_argument("--diretorio", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--perfil", default="principal")
    parser.add_argument("--rede-local", action="store_true")
    parser.add_argument("--configurar-login", action="store_true")
    parser.add_argument("--mostrar-acesso", action="store_true")
    parser.add_argument("--ip", default="IP-DA-MAQUINA")
    args = parser.parse_args()

    try:
        perfil = validar_perfil(args.perfil)
        root = args.diretorio.resolve()
        if args.mostrar_acesso:
            mostrar_acesso(root, perfil, args.ip)
            return 0
        porta, novo, login_definido = configurar(root, perfil, args.rede_local, args.configurar_login)
        print(f"Perfil '{perfil}' configurado; porta {porta}.")
        if novo:
            print("Segurança: modo SIMULAÇÃO ativado para este perfil novo.")
        if not login_definido:
            print("Login pendente: configure config/secrets.ini ou execute com --configurar-login.")
        return 0
    except (ValueError, OSError, RuntimeError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
