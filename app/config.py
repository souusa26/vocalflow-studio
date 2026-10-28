"""
Configurações Globais e Gerenciamento de Caminhos (Modo Portátil vs Instalado)
"""

import os
import sys
import json
from pathlib import Path

APP_NAME = "VocalFlowStudio"
APP_TITLE = "VocalFlow Studio - Live Voice FX"
APP_VERSION = "1.0.0"

def get_base_dir() -> Path:
    """Retorna o diretório base da aplicação (suporta PyInstaller frozen e desenvolvimento)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent

def is_portable_mode() -> bool:
    """
    Detecta se a aplicação está em modo portátil.
    O modo portátil é ativado se existir um arquivo 'portable.txt' ou pasta 'data'
    no mesmo diretório do executável.
    """
    base_dir = get_base_dir()
    if (base_dir / "portable.txt").exists() or (base_dir / "data").is_dir():
        return True
    return False

def get_data_dir() -> Path:
    """
    Retorna o diretório raiz de dados do usuário:
    - Modo Portátil: <base_dir>/data
    - Modo Instalado: %APPDATA%/VocalFlowStudio (Windows) ou ~/.local/share/VocalFlowStudio (Linux)
    """
    if is_portable_mode():
        path = get_base_dir() / "data"
    else:
        if sys.platform == "win32":
            app_data = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
            path = Path(app_data) / APP_NAME
        else:
            path = Path.home() / ".local" / "share" / APP_NAME

    path.mkdir(parents=True, exist_ok=True)
    return path

def get_presets_dir() -> Path:
    """Diretório de presets de efeitos do usuário."""
    p = get_data_dir() / "presets"
    p.mkdir(parents=True, exist_ok=True)
    return p

def get_lyrics_dir() -> Path:
    """Diretório de letras de músicas do usuário."""
    p = get_data_dir() / "lyrics"
    p.mkdir(parents=True, exist_ok=True)
    return p

def get_stems_dir() -> Path:
    """Diretório de stems separados e arquivos de áudio processados."""
    p = get_data_dir() / "stems"
    p.mkdir(parents=True, exist_ok=True)
    return p

def get_models_dir() -> Path:
    """Diretório de cache de modelos de inteligência artificial (Demucs/ONNX)."""
    p = get_data_dir() / "models"
    p.mkdir(parents=True, exist_ok=True)
    return p

def get_settings_file() -> Path:
    """Arquivo JSON de configurações gerais da aplicação."""
    return get_data_dir() / "settings.json"

DEFAULT_SETTINGS = {
    "sample_rate": 48000,
    "block_size": 256,
    "input_device": None,
    "virtual_device": None,
    "monitor1_device": None,
    "monitor2_device": None,
    "monitor1_enabled": False,
    "monitor2_enabled": False,
    "monitor1_volume": 1.0,
    "monitor2_volume": 1.0,
    "input_volume": 1.0,
    "master_volume": 1.0,
    "backing_track_to_monitors": True,
    "backing_track_to_virtual": False,
    "last_preset": "Rap com Autotune",
}

def load_settings() -> dict:
    settings_file = get_settings_file()
    if settings_file.exists():
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                saved = json.load(f)
                result = dict(DEFAULT_SETTINGS)
                result.update(saved)
                return result
        except Exception as e:
            print(f"[Config] Erro ao carregar configurações: {e}")
    return dict(DEFAULT_SETTINGS)

def save_settings(settings: dict) -> None:
    settings_file = get_settings_file()
    try:
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"[Config] Erro ao salvar configurações: {e}")
