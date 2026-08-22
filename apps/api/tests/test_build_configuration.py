import sys

from build import get_pyinstaller_command


def test_pyinstaller_bundles_alembic_runtime_files():
    command = get_pyinstaller_command()

    assert command[:3] == [sys.executable, "-m", "PyInstaller"]
    assert "alembic.ini:." in command
    assert "alembic:alembic" in command
    assert "--collect-all=sea_g2p" in command
    assert "--collect-all=vieneu" in command


def test_pyinstaller_bundles_huggingface_for_startup_model_bootstrap():
    command = get_pyinstaller_command()

    assert "--hidden-import=huggingface_hub" in command
