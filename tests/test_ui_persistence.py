from unittest.mock import Mock
import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from app.lyrics.manager import LyricsManager
from app.ui.tabs.tab_lyrics import TabLyrics
from app.ui.main_window import MainWindow
from app.storage import write_json_atomic


def select(tab, lyric_id):
    for index in range(tab.list_lyrics.count()):
        item = tab.list_lyrics.item(index)
        if item.data(Qt.ItemDataRole.UserRole) == lyric_id:
            tab.list_lyrics.setCurrentItem(item)
            return
    raise AssertionError("Missing lyric")


@pytest.fixture
def editor(qapp, tmp_path):
    manager = LyricsManager(tmp_path / "lyrics")
    first = manager.create_lyric("A", "old")
    second = manager.create_lyric("B", "other")
    tab = TabLyrics(manager)
    select(tab, first["id"])
    yield tab, manager, first, second
    tab.autosave_timer.stop()
    tab.deleteLater()


def test_switching_lyrics_saves_the_old_editor_before_loading(editor):
    tab, manager, first, second = editor
    tab.text_editor.setPlainText("new verse")
    select(tab, second["id"])
    assert manager.get_lyric(first["id"])["content"] == "new verse"
    assert tab.text_editor.toPlainText() == "other"
    assert not tab.autosave_timer.isActive()


def test_failed_save_preserves_editor_and_selection(editor, monkeypatch):
    tab, manager, first, second = editor
    monkeypatch.setattr(manager, "update_lyric", lambda *args, **kwargs: False)
    tab.text_editor.setPlainText("unsaved verse")
    select(tab, second["id"])
    assert tab.active_lyric_id == first["id"]
    assert tab.list_lyrics.currentItem().data(Qt.ItemDataRole.UserRole) == first["id"]
    assert tab.text_editor.toPlainText() == "unsaved verse"
    assert "Falha" in tab.lbl_autosave.text()


def test_creating_new_lyric_flushes_previous_editor(editor):
    tab, manager, first, _ = editor
    tab.text_editor.setPlainText("new verse")
    tab._create_new_lyric()
    assert manager.get_lyric(first["id"])["content"] == "new verse"
    assert tab.active_lyric_id != first["id"]


def test_search_then_reselect_same_lyric_keeps_pending_text(editor):
    tab, manager, first, _ = editor
    tab.text_editor.setPlainText("pending after search")
    tab.edit_search.setText("A")
    select(tab, first["id"])
    assert tab.text_editor.toPlainText() == "pending after search"
    assert tab.flush_pending_save()
    assert manager.get_lyric(first["id"])["content"] == "pending after search"


def test_export_includes_pending_text(editor, tmp_path, monkeypatch):
    tab, manager, first, _ = editor
    path = tmp_path / "export.txt"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(path), ""))
    monkeypatch.setattr(QMessageBox, "information", lambda *args: None)
    tab.text_editor.setPlainText("last verse")
    tab._export_txt()
    assert "last verse" in path.read_text(encoding="utf-8")


def test_window_close_flushes_pending_lyrics(qapp, no_audio_devices):
    window = MainWindow()
    tab = window.tab_lyrics
    lyric_id = tab.active_lyric_id
    tab.text_editor.setPlainText("saved before closing")
    window.close()
    assert window.lyrics_mgr.get_lyric(lyric_id)["content"] == "saved before closing"
    assert not tab.autosave_timer.isActive()
    window.deleteLater()


def test_window_close_is_rejected_if_save_fails(qapp, no_audio_devices, monkeypatch):
    window = MainWindow()
    window.tab_lyrics.text_editor.setPlainText("keep me")
    monkeypatch.setattr(window.lyrics_mgr, "update_lyric", lambda *args, **kwargs: False)
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: None)
    event = Mock()
    window.closeEvent(event)
    event.ignore.assert_called_once()
    event.accept.assert_not_called()
    assert window.tab_lyrics.text_editor.toPlainText() == "keep me"
    window.tab_lyrics.autosave_timer.stop()
    window.deleteLater()


def test_atomic_save_failure_keeps_previous_document(tmp_path, monkeypatch):
    import app.storage as storage
    path = tmp_path / "lyric.json"
    write_json_atomic(path, {"content": "original"})
    original = path.read_bytes()
    monkeypatch.setattr(storage.os, "replace", Mock(side_effect=OSError("disk full")))
    with pytest.raises(OSError, match="disk full"):
        write_json_atomic(path, {"content": "replacement"})
    assert path.read_bytes() == original
    assert not list(tmp_path.glob("*.tmp"))
