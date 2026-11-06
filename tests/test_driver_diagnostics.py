"""O ChromeDriver deve registrar falhas sem expor o arquivo de log."""
from __future__ import annotations

import os
import stat
from types import SimpleNamespace

import pytest

import driver


def test_log_do_chromedriver_tem_permissao_privada(tmp_path, monkeypatch):
    monkeypatch.setattr(driver.paths, "current", lambda: SimpleNamespace(data=tmp_path))
    arquivo, caminho = driver._open_driver_log()
    assert arquivo is not None
    try:
        arquivo.write(b"falha de inicializacao\n")
    finally:
        arquivo.close()
    assert caminho == tmp_path / "logs/chromedriver.log"
    assert caminho.read_bytes() == b"falha de inicializacao\n"
    if os.name != "nt":
        assert stat.S_IMODE(caminho.stat().st_mode) == 0o600


def test_log_existente_com_permissoes_inseguras_eh_corrigido(tmp_path, monkeypatch):
    monkeypatch.setattr(driver.paths, "current", lambda: SimpleNamespace(data=tmp_path))
    pasta = tmp_path / "logs"
    pasta.mkdir()
    log = pasta / "chromedriver.log"
    log.write_text("anterior\n", encoding="utf-8")
    if os.name != "nt":
        log.chmod(0o644)
    arquivo, caminho = driver._open_driver_log()
    assert arquivo is not None
    arquivo.write(b"novo\n")
    arquivo.close()
    assert caminho.read_bytes() == b"anterior\nnovo\n"
    if os.name != "nt":
        assert stat.S_IMODE(log.stat().st_mode) == 0o600


def test_driver_redireciona_saida_snap_e_fecha_descritor(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(driver.paths, "current", lambda: SimpleNamespace(data=tmp_path))
    monkeypatch.setattr(driver, "_system_chrome", lambda: ("/usr/bin/chromedriver", "/usr/bin/chromium-browser"))
    instancia = {}

    class Service:
        def __init__(self, executable_path, log_output):
            assert executable_path == "/usr/bin/chromedriver"
            instancia["output"] = log_output

    def falhar(*, service, options):
        assert options.binary_location == "/usr/bin/chromium-browser"
        service_output = instancia["output"]
        service_output.write(b"snap: sem sessao de usuario\n")
        raise RuntimeError("Service unexpectedly exited. Status code was: 1")

    monkeypatch.setattr(driver, "Service", Service)
    monkeypatch.setattr(driver.webdriver, "Chrome", falhar)

    with pytest.raises(RuntimeError, match="Status code was: 1"):
        driver.create_driver("https://example.com", headless=True)

    arquivo = tmp_path / "logs/chromedriver.log"
    assert arquivo.read_bytes() == b"snap: sem sessao de usuario\n"
    assert instancia["output"].closed
    assert str(arquivo) in caplog.text


def test_erro_ao_abrir_log_nao_impede_a_inicializacao(tmp_path, monkeypatch):
    monkeypatch.setattr(driver.paths, "current", lambda: SimpleNamespace(data=tmp_path))
    destino = tmp_path / "logs"
    destino.write_text("arquivo em vez de pasta", encoding="utf-8")
    arquivo, caminho = driver._open_driver_log()
    assert arquivo is None
    assert caminho == destino / "chromedriver.log"
