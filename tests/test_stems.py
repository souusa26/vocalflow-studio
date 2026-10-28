"""
Testes unitários para o reprodutor de stems, mixer multi-pista e separador de áudio.
"""

import pytest
from pathlib import Path
import numpy as np
import soundfile as sf

from app.stems.player import StemPlayer
from app.stems.separator import SeparationEngine
from app.stems.exporter import StemExporter

@pytest.fixture
def sample_stems(tmp_path):
    sr = 48000
    duration = 1.0  # 1 segundo
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    
    # Gera sinais sintéticos diferentes para cada stem
    vocals = (0.4 * np.sin(2.0 * np.pi * 440.0 * t)).astype(np.float32)
    drums = (0.5 * np.sign(np.sin(2.0 * np.pi * 60.0 * t))).astype(np.float32)
    bass = (0.6 * np.sin(2.0 * np.pi * 80.0 * t)).astype(np.float32)
    other = (0.2 * np.sin(2.0 * np.pi * 880.0 * t)).astype(np.float32)
    
    paths = {
        "vocals": tmp_path / "vocals.wav",
        "drums": tmp_path / "drums.wav",
        "bass": tmp_path / "bass.wav",
        "other": tmp_path / "other.wav",
    }
    
    for name, p in paths.items():
        data = locals()[name]
        sf.write(str(p), np.column_stack((data, data)), sr)
        
    return paths

def test_stem_player_playback_and_mixing(sample_stems):
    player = StemPlayer(sample_rate=48000)
    player.load_stems(sample_stems)
    
    assert "vocals" in player.tracks
    assert "drums" in player.tracks
    assert player.get_duration_seconds() > 0.95
    
    player.play()
    assert player.is_playing is True
    
    # Lê um bloco de áudio
    block = player.get_next_block(512)
    assert block.shape == (512, 2)
    assert np.max(np.abs(block)) > 0.0

def test_stem_player_mute_solo(sample_stems):
    player = StemPlayer(sample_rate=48000)
    player.load_stems(sample_stems)
    player.play()
    
    # 1. Muta vocais
    player.set_stem_mute("vocals", True)
    assert player.tracks["vocals"].mute is True
    
    # 2. Ativa solo apenas na bateria
    player.set_stem_solo("drums", True)
    assert player.tracks["drums"].solo is True
    
    block = player.get_next_block(512)
    assert block.shape == (512, 2)
    assert np.max(np.abs(block)) > 0.0

def test_stem_player_routing_protection_defaults(sample_stems):
    player = StemPlayer(sample_rate=48000)
    # Por padrão, deve ir aos monitores, mas NÃO ao microfone virtual!
    assert player.send_to_monitors is True
    assert player.send_to_virtual_mic is False

def test_export_stem_and_mix(sample_stems, tmp_path):
    player = StemPlayer(sample_rate=48000)
    player.load_stems(sample_stems)
    
    export_stem_path = tmp_path / "exported_vocals.wav"
    ok1 = StemExporter.export_stem(player, "vocals", export_stem_path)
    assert ok1 is True
    assert export_stem_path.exists()
    
    export_mix_path = tmp_path / "exported_mix.wav"
    ok2 = StemExporter.export_custom_mix(player, export_mix_path)
    assert ok2 is True
    assert export_mix_path.exists()

def test_native_spectral_separation(tmp_path):
    sr = 48000
    t = np.linspace(0, 0.5, int(sr * 0.5), endpoint=False)
    # Mix estéreo sintético (vocal central + harmônico)
    mix = 0.5 * np.sin(2 * np.pi * 440 * t) + 0.3 * np.sin(2 * np.pi * 100 * t)
    audio_file = tmp_path / "song_test.wav"
    sf.write(str(audio_file), np.column_stack((mix, mix)), sr)
    
    engine = SeparationEngine()
    progress_records = []
    
    def on_prog(pct, msg):
        progress_records.append((pct, msg))
        
    stems = engine.separate(audio_file, use_ai_model=False, progress_cb=on_prog)
    assert "vocals" in stems
    assert "instrumental" in stems
    assert stems["vocals"].exists()
    assert stems["instrumental"].exists()
    assert len(progress_records) > 0
