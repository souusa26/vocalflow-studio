from app.audio.engine import AudioEngine
from app.presets.manager import PresetManager
from app.ui.tabs.tab_vocal import TabVocal


def test_virtual_output_choice_matches_engine_and_survives_refresh(qapp, tmp_path, monkeypatch):
    import app.ui.tabs.tab_vocal as vocal
    inputs = [{"id": 1, "name": "Mic", "hostapi": "WASAPI"}]
    outputs = [{"id": 2, "name": "Headphones", "hostapi": "WASAPI", "is_virtual": False},
               {"id": 3, "name": "Cable Input", "hostapi": "WASAPI", "is_virtual": True}]
    monkeypatch.setattr(vocal, "get_audio_devices", lambda: (inputs, outputs))
    monkeypatch.setattr(vocal, "find_virtual_cable_output", lambda: None)
    engine = AudioEngine()
    tab = TabVocal(engine, PresetManager(tmp_path))
    assert tab.combo_virtual.currentData() is None
    assert engine.virtual_device_id is None
    tab.combo_virtual.setCurrentIndex(tab.combo_virtual.findData(3))
    tab._refresh_devices()
    assert tab.combo_virtual.currentData() == engine.virtual_device_id == 3
    tab.combo_virtual.setCurrentIndex(0)
    tab._refresh_devices()
    assert tab.combo_virtual.currentData() is None
    assert engine.virtual_device_id is None
    tab.meter_timer.stop()
    tab.deleteLater()
