"""
Reprodutor Multi-Pista de Stems (Stem Player Engine).
Permite tocar as faixas sincronizadas com controles individuais de Volume, Mute, Solo,
Seek na timeline e roteamento selecionável para Monitores e Microfone Virtual.
"""

import threading
from pathlib import Path
from typing import Dict, Optional, Tuple
import numpy as np
import soundfile as sf

class StemTrack:
    def __init__(self, name: str, file_path: Path, data: np.ndarray, sample_rate: int):
        self.name = name
        self.file_path = file_path
        self.data = data  # Shape (N, 2), float32
        self.sample_rate = sample_rate
        self.volume = 1.0
        self.mute = False
        self.solo = False

class StemPlayer:
    def __init__(self, sample_rate: int = 48000):
        self.target_sample_rate = sample_rate
        self.tracks: Dict[str, StemTrack] = {}
        self.playhead_frame = 0
        self.total_frames = 0
        self.is_playing = False
        self.loop = False
        
        # Flags de roteamento do instrumental/stems
        self.send_to_monitors = True       # Envia aos fones / caixas
        self.send_to_virtual_mic = False    # Proteção: Desativado por padrão para o Discord

        self.lock = threading.Lock()

    def load_stems(self, stems_dict: Dict[str, Path]):
        """Carrega e sincroniza todas as pistas de stems."""
        with self.lock:
            self.tracks.clear()
            max_frames = 0
            
            for stem_name, path in stems_dict.items():
                if not Path(path).exists():
                    continue
                try:
                    data, sr = sf.read(str(path), dtype="float32")
                    # Converte para estéreo
                    if data.ndim == 1:
                        data = np.column_stack((data, data))
                    elif data.shape[1] > 2:
                        data = data[:, :2]

                    track = StemTrack(stem_name, Path(path), data, sr)
                    self.tracks[stem_name] = track
                    if len(data) > max_frames:
                        max_frames = len(data)
                except Exception as e:
                    print(f"[StemPlayer] Erro ao carregar stem {stem_name}: {e}")

            self.total_frames = max_frames
            self.playhead_frame = 0
            self.is_playing = False

    def play(self):
        with self.lock:
            self.is_playing = True

    def pause(self):
        with self.lock:
            self.is_playing = False

    def stop(self):
        with self.lock:
            self.is_playing = False
            self.playhead_frame = 0

    def seek_seconds(self, seconds: float):
        with self.lock:
            frame = int(seconds * self.target_sample_rate)
            self.playhead_frame = max(0, min(self.total_frames, frame))

    def get_position_seconds(self) -> float:
        with self.lock:
            return self.playhead_frame / float(self.target_sample_rate or 48000)

    def get_duration_seconds(self) -> float:
        with self.lock:
            return self.total_frames / float(self.target_sample_rate or 48000)

    def set_stem_volume(self, stem_name: str, volume: float):
        with self.lock:
            if stem_name in self.tracks:
                self.tracks[stem_name].volume = max(0.0, min(1.5, float(volume)))

    def set_stem_mute(self, stem_name: str, mute: bool):
        with self.lock:
            if stem_name in self.tracks:
                self.tracks[stem_name].mute = bool(mute)

    def set_stem_solo(self, stem_name: str, solo: bool):
        with self.lock:
            if stem_name in self.tracks:
                self.tracks[stem_name].solo = bool(solo)

    def get_next_block(self, frames: int) -> np.ndarray:
        """
        Gera o próximo bloco de áudio misturado para o mixer em tempo real.
        Respeita Mute, Solo e Volume de cada faixa.
        """
        out = np.zeros((frames, 2), dtype=np.float32)
        
        with self.lock:
            if not self.is_playing or self.total_frames == 0 or not self.tracks:
                return out

            start = self.playhead_frame
            end = start + frames

            # Verifica se há faixas em modo Solo
            any_solo = any(t.solo for t in self.tracks.values())

            for stem_name, track in self.tracks.items():
                # Regras de Solo e Mute
                if any_solo and not track.solo:
                    continue
                if track.mute:
                    continue
                if track.volume <= 0.001:
                    continue

                track_len = len(track.data)
                if start < track_len:
                    read_end = min(end, track_len)
                    chunk_len = read_end - start
                    out[:chunk_len] += track.data[start:read_end] * track.volume

            self.playhead_frame += frames

            # Fim da música ou loop
            if self.playhead_frame >= self.total_frames:
                if self.loop:
                    self.playhead_frame = 0
                else:
                    self.playhead_frame = self.total_frames
                    self.is_playing = False

        return out
