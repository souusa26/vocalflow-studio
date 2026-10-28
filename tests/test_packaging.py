import importlib.util
from pathlib import Path
from unittest.mock import Mock
import zipfile
from app import config


def test_only_portable_zip_includes_mode_marker(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("vocalflow_build", Path(__file__).parents[1] / "packaging" / "build.py")
    build = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build)
    (tmp_path / "README.md").write_text("test", encoding="utf-8")
    monkeypatch.setattr(build, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(build, "DIST_DIR", tmp_path / "dist")
    monkeypatch.setattr(build, "BUILD_DIR", tmp_path / "build")
    def compile_app(*args, **kwargs):
        target = tmp_path / "dist" / "VocalFlowStudio"
        target.mkdir(parents=True)
        (target / "VocalFlowStudio.exe").write_bytes(b"test executable")
        return Mock(returncode=0)
    monkeypatch.setattr(build.subprocess, "run", compile_app)
    build.build()
    assert not (tmp_path / "dist" / "VocalFlowStudio" / "portable.txt").exists()
    with zipfile.ZipFile(tmp_path / "dist" / "VocalFlowStudio_Portatil_v1.1.0.zip") as archive:
        assert "portable.txt" in archive.namelist()


def test_data_folder_alone_does_not_activate_portable_mode(tmp_path):
    (tmp_path / "portable.txt").unlink()
    (tmp_path / "data").mkdir()
    assert not config.is_portable_mode()


def test_installed_mode_migrates_legacy_data_without_deleting_original(tmp_path, monkeypatch):
    import sys
    (tmp_path / "portable.txt").unlink()
    legacy = tmp_path / "data"
    legacy.mkdir()
    (legacy / "lyrics.json").write_text("original", encoding="utf-8")
    # APPDATA is selected inside the function; Path itself remains the host's class.
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setenv("APPDATA", str(tmp_path / "profile"))
    destination = config.get_data_dir()
    assert destination == tmp_path / "profile" / config.APP_NAME
    assert (destination / "lyrics.json").read_text(encoding="utf-8") == "original"
    assert (legacy / "lyrics.json").exists()
