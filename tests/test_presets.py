"""
Testes unitários para o gerenciamento de presets locais e de fábrica.
"""

import pytest
import shutil
from pathlib import Path
from app.presets.manager import PresetManager
from app.presets.factory_presets import FACTORY_PRESETS

@pytest.fixture
def temp_preset_manager(tmp_path):
    mgr = PresetManager(storage_dir=tmp_path)
    return mgr

def test_factory_presets_initialization(temp_preset_manager):
    presets = temp_preset_manager.list_presets()
    for name in FACTORY_PRESETS.keys():
        assert name in presets

def test_load_factory_preset(temp_preset_manager):
    data = temp_preset_manager.load_preset("Trap Autotune (Travis Style)")
    assert data is not None
    assert data["autotune"]["enabled"] is True
    assert data["autotune"]["snap_speed"] == 0.0

def test_save_and_load_user_preset(temp_preset_manager):
    custom_state = {
        "input_gain": 1.2,
        "output_gain": 0.9,
        "autotune": {"enabled": True, "root_note": "F#", "scale_name": "Pentatônica Menor (Hip-Hop)"}
    }
    success = temp_preset_manager.save_preset("Meu Preset Teste", custom_state, "Descrição teste")
    assert success is True
    
    loaded = temp_preset_manager.load_preset("Meu Preset Teste")
    assert loaded is not None
    assert loaded["input_gain"] == 1.2
    assert loaded["autotune"]["root_note"] == "F#"

def test_protect_factory_presets_from_deletion(temp_preset_manager):
    # Não deve permitir deletar preset de fábrica
    deleted = temp_preset_manager.delete_preset("Voz Limpa (Studio Vocal)")
    assert deleted is False
    assert temp_preset_manager.load_preset("Voz Limpa (Studio Vocal)") is not None

def test_delete_user_preset(temp_preset_manager):
    temp_preset_manager.save_preset("ParaDeletar", {"input_gain": 1.0})
    assert "ParaDeletar" in temp_preset_manager.list_presets()
    
    deleted = temp_preset_manager.delete_preset("ParaDeletar")
    assert deleted is True
    assert "ParaDeletar" not in temp_preset_manager.list_presets()

def test_import_export_preset(temp_preset_manager, tmp_path):
    temp_preset_manager.save_preset("PresetExportavel", {"input_gain": 0.85})
    export_file = tmp_path / "exportado.json"
    
    exported = temp_preset_manager.export_preset("PresetExportavel", export_file)
    assert exported is True
    assert export_file.exists()
    
    # Importa em outro gerenciador
    second_dir = tmp_path / "second_presets"
    mgr2 = PresetManager(storage_dir=second_dir)
    imported_name = mgr2.import_preset(export_file)
    assert imported_name == "PresetExportavel"
    assert mgr2.load_preset("PresetExportavel")["input_gain"] == 0.85
