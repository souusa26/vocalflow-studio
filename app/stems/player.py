"""
Reprodutor Multi-Pista de Stems (Stem Player Engine).
Permite tocar as faixas sincronizadas com controles individuais de Volume, Mute, Solo,
Seek na timeline e roteamento selecionável para Monitores e Microfone Virtual.
"""

import threading
import math
from scipy.signal import resample_poly
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

    @staticmethod
    def _resample(data, source_rate, target_rate):
        if source_rate == target_rate:
            return data
        divisor = math.gcd(source_rate, target_rate)
        return resample_poly(data, target_rate // divisor,
                             source_rate // divisor, axis=0).astype(np.float32)

    def load_stems(self, stems_dict: Dict[str, Path]):
        """Decode/resample outside the callback lock, then swap the complete session."""
        tracks = {}
        for name, path in stems_dict.items():
            data, sr = sf.read(str(path), dtype="float32", always_2d=True)
            data = np.repeat(data, 2, axis=1) if data.shape[1] == 1 else data[:, :2]
            data = self._resample(data, sr, self.target_sample_rate)
            tracks[name] = StemTrack(name, Path(path), data, self.target_sample_rate)
        if not tracks:
            raise ValueError("Nenhuma faixa de áudio foi carregada.")
        # The full instrumental and its constituent tracks are alternative mixes.
        if "instrumental" in tracks and any(name in tracks for name in ("drums", "bass", "other")):
            tracks["instrumental"].mute = True
        with self.lock:
            self.tracks = tracks
            self.total_frames = max(len(t.data) for t in tracks.values())
            self.playhead_frame = 0
            self.is_playing = False

    def set_sample_rate(self, sample_rate):
        with self.lock:
            position = self.playhead_frame / self.target_sample_rate
            for track in self.tracks.values():
                track.data = self._resample(track.data, track.sample_rate, sample_rate)
                track.sample_rate = sample_rate
            self.target_sample_rate = sample_rate
            self.total_frames = max((len(t.data) for t in self.tracks.values()), default=0)
            self.playhead_frame = min(self.total_frames, round(position * sample_rate))

    def play(self):
        with self.lock:
            # Pressing play after reaching the end should replay the song.
            if self.total_frames and self.playhead_frame >= self.total_frames:
                self.playhead_frame = 0
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

            offset = 0
            any_solo = any(t.solo for t in self.tracks.values())
            while offset < frames and self.is_playing:
                start = self.playhead_frame
                count = min(frames - offset, self.total_frames - start)
                for track in self.tracks.values():
                    if (any_solo and not track.solo) or track.mute or track.volume <= 0.001:
                        continue
                    length = max(0, min(count, len(track.data) - start))
                    out[offset:offset + length] += track.data[start:start + length] * track.volume
                offset += count
                self.playhead_frame += count
                if self.playhead_frame >= self.total_frames:
                    if self.loop:
                        self.playhead_frame = 0
                    else:
                        self.is_playing = False
        return out
