"""Protege a identidade do projeto sem modificar avisos legais exigidos pela MIT."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IGNORAR = {".git", ".venv", "__pycache__", "data", "profiles", ".pytest_cache"}


def test_aviso_legal_original_permanece():
    texto = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert texto.startswith("MIT License")
    assert "Copyright (c)" in texto
    assert "The above copyright notice and this permission notice" in texto


def test_referencias_antigas_nao_aparecem_fora_da_licenca():
    referencias = (
        "Ja" + "vier" + "Ol" + "medo",
        "javier" + "olmedo",
        "hack" + "puntes",
        "jjavier" + "olmedo23",
    )
    for arquivo in ROOT.rglob("*"):
        if not arquivo.is_file() or any(parte in IGNORAR for parte in arquivo.relative_to(ROOT).parts):
            continue
        if arquivo.name == "LICENSE" or arquivo.suffix.lower() in {".png", ".ico", ".jpg", ".jpeg", ".webp", ".pyc"}:
            continue
        try:
            texto = arquivo.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for referencia in referencias:
            assert referencia.casefold() not in texto.casefold(), f"Referência antiga em {arquivo.relative_to(ROOT)}"


def test_nao_ha_patrocinio_de_terceiros():
    assert not (ROOT / ".github/FUNDING.yml").exists()
