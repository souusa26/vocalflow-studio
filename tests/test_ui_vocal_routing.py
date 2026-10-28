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


def test_default_microphone_and_headphones_are_selected_on_first_load(qapp, tmp_path, monkeypatch):
    import app.ui.tabs.tab_vocal as vocal
    inputs = [{"id": 1, "name": "Other Mic", "hostapi": "WASAPI"},
              {"id": 4, "name": "Default Mic", "hostapi": "WASAPI"}]
    outputs = [{"id": 2, "name": "Other", "hostapi": "WASAPI", "is_virtual": False},
               {"id": 5, "name": "Headphones", "hostapi": "WASAPI", "is_virtual": False}]
    monkeypatch.setattr(vocal, "get_audio_devices", lambda: (inputs, outputs))
    monkeypatch.setattr(vocal, "find_virtual_cable_output", lambda: None)
    monkeypatch.setattr(vocal, "find_default_input", lambda: {"id": 4})
    monkeypatch.setattr(vocal, "find_default_output", lambda: {"id": 5})
    engine = AudioEngine()
    tab = TabVocal(engine, PresetManager(tmp_path))
    assert engine.input_device_id == 4
    assert engine.monitor1_device_id == 5
    tab.combo_mon1.setCurrentIndex(tab.combo_mon1.findData(2))
    tab._refresh_devices()
    assert engine.monitor1_device_id == 2
    tab.meter_timer.stop()
    tab.deleteLater()


def test_audio_diagnostics_warns_after_repeated_device_failures(qapp, tmp_path, no_audio_devices):
    engine = AudioEngine()
    tab = TabVocal(engine, PresetManager(tmp_path))
    engine.is_running = True
    engine.input_overflows = 3
    tab._update_meters()
    assert not tab.lbl_audio_warning.isHidden()
    assert "1024" in tab.lbl_audio_warning.text()
    engine.is_running = False
    tab._update_meters()
    assert tab.lbl_audio_warning.isHidden()
    tab.meter_timer.stop()
    tab.deleteLater()
