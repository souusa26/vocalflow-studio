import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from app import config


@pytest.fixture(autouse=True)
def isolated_application_data(tmp_path, monkeypatch):
    """Tests must never change the developer's actual lyrics or presets."""
    monkeypatch.setattr(config, "get_base_dir", lambda: tmp_path)
    (tmp_path / "portable.txt").touch()


@pytest.fixture(scope="session")
def qapp():
    from PyQt6.QtWidgets import QApplication
    application = QApplication.instance() or QApplication([])
    yield application


@pytest.fixture
def no_audio_devices(monkeypatch):
    import sounddevice as sd
    monkeypatch.setattr(sd, "query_devices", lambda: [])
    monkeypatch.setattr(sd, "query_hostapis", lambda: [])
