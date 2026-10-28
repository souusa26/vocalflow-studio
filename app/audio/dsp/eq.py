"""
Equalizador Paramétrico de 3 Bandas + Filtro High-Pass (Corte de Graves < 80Hz).
Implementado com filtros Biquad IIR de fase contínua (Cookbook de Robert Bristow-Johnson).
"""

import numpy as np
import math

class BiquadFilter:
    def __init__(self):
        self.b0 = 1.0
        self.b1 = 0.0
        self.b2 = 0.0
        self.a1 = 0.0
        self.a2 = 0.0
        # Estados para canais mono / estéreo
        self.z1 = np.zeros(2, dtype=np.float32)
        self.z2 = np.zeros(2, dtype=np.float32)

    def process_sample(self, x: float, ch: int = 0) -> float:
        y = self.b0 * x + self.z1[ch]
        self.z1[ch] = self.b1 * x - self.a1 * y + self.z2[ch]
        self.z2[ch] = self.b2 * x - self.a2 * y
        return y

    def process_block(self, audio: np.ndarray) -> np.ndarray:
        if audio.ndim == 1:
            out = np.zeros_like(audio)
            for i in range(len(audio)):
                out[i] = self.process_sample(audio[i], 0)
            return out
        else:
            out = np.zeros_like(audio)
            for i in range(len(audio)):
                out[i, 0] = self.process_sample(audio[i, 0], 0)
                out[i, 1] = self.process_sample(audio[i, 1], 1)
            return out

class Equalizer:
    def __init__(self, sample_rate: int = 48000):
        self.sample_rate = sample_rate
        self.enabled = True
        
        # Parâmetros
        self.highpass_enabled = True
        self.highpass_freq = 80.0
        
        self.low_gain_db = 0.0      # ~120 Hz
        self.mid_gain_db = 2.0      # ~2.5 kHz (Presença vocal no Rap)
        self.high_gain_db = 3.0     # ~10 kHz (Brilho e ar de estúdio)

        # Filtros Biquad
        self.hp_filter = BiquadFilter()
        self.low_filter = BiquadFilter()
        self.mid_filter = BiquadFilter()
        self.high_filter = BiquadFilter()

        self._update_coefficients()

    def set_params(self, highpass_enabled: bool = None, low_db: float = None,
                   mid_db: float = None, high_db: float = None, enabled: bool = None):
        if highpass_enabled is not None:
            self.highpass_enabled = bool(highpass_enabled)
        if low_db is not None:
            self.low_gain_db = float(low_db)
        if mid_db is not None:
            self.mid_gain_db = float(mid_db)
        if high_db is not None:
            self.high_gain_db = float(high_db)
        if enabled is not None:
            self.enabled = bool(enabled)
        self._update_coefficients()

    def _update_coefficients(self):
        fs = self.sample_rate

        # 1. High-Pass Biquad (Butterworth Q=0.707)
        w0 = 2.0 * math.pi * self.highpass_freq / fs
        cos_w0 = math.cos(w0)
        sin_w0 = math.sin(w0)
        alpha = sin_w0 / (2.0 * 0.7071)
        a0 = 1.0 + alpha
        self.hp_filter.b0 = ((1.0 + cos_w0) / 2.0) / a0
        self.hp_filter.b1 = (-(1.0 + cos_w0)) / a0
        self.hp_filter.b2 = ((1.0 + cos_w0) / 2.0) / a0
        self.hp_filter.a1 = (-2.0 * cos_w0) / a0
        self.hp_filter.a2 = (1.0 - alpha) / a0

        # 2. Low Shelf Biquad (120 Hz)
        A = 10.0 ** (self.low_gain_db / 40.0)
        w0 = 2.0 * math.pi * 120.0 / fs
        cos_w0 = math.cos(w0)
        sin_w0 = math.sin(w0)
        alpha = sin_w0 / 2.0 * math.sqrt(2.0)
        a0 = (A + 1.0) + (A - 1.0) * cos_w0 + 2.0 * math.sqrt(A) * alpha
        self.low_filter.b0 = (A * ((A + 1.0) - (A - 1.0) * cos_w0 + 2.0 * math.sqrt(A) * alpha)) / a0
        self.low_filter.b1 = (2.0 * A * ((A - 1.0) - (A + 1.0) * cos_w0)) / a0
        self.low_filter.b2 = (A * ((A + 1.0) - (A - 1.0) * cos_w0 - 2.0 * math.sqrt(A) * alpha)) / a0
        self.low_filter.a1 = (-2.0 * ((A - 1.0) + (A + 1.0) * cos_w0)) / a0
        self.low_filter.a2 = ((A + 1.0) + (A - 1.0) * cos_w0 - 2.0 * math.sqrt(A) * alpha) / a0

        # 3. Peaking Mid Filter (2.5 kHz, Q=1.0)
        A = 10.0 ** (self.mid_gain_db / 40.0)
        w0 = 2.0 * math.pi * 2500.0 / fs
        cos_w0 = math.cos(w0)
        sin_w0 = math.sin(w0)
        alpha = sin_w0 / (2.0 * 1.0)
        a0 = 1.0 + alpha / A
        self.mid_filter.b0 = (1.0 + alpha * A) / a0
        self.mid_filter.b1 = (-2.0 * cos_w0) / a0
        self.mid_filter.b2 = (1.0 - alpha * A) / a0
        self.mid_filter.a1 = (-2.0 * cos_w0) / a0
        self.mid_filter.a2 = (1.0 - alpha / A) / a0

        # 4. High Shelf Filter (9.0 kHz)
        A = 10.0 ** (self.high_gain_db / 40.0)
        w0 = 2.0 * math.pi * 9000.0 / fs
        cos_w0 = math.cos(w0)
        sin_w0 = math.sin(w0)
        alpha = sin_w0 / 2.0 * math.sqrt(2.0)
        a0 = (A + 1.0) - (A - 1.0) * cos_w0 + 2.0 * math.sqrt(A) * alpha
        self.high_filter.b0 = (A * ((A + 1.0) + (A - 1.0) * cos_w0 + 2.0 * math.sqrt(A) * alpha)) / a0
        self.high_filter.b1 = (-2.0 * A * ((A - 1.0) + (A + 1.0) * cos_w0)) / a0
        self.high_filter.b2 = (A * ((A + 1.0) + (A - 1.0) * cos_w0 - 2.0 * math.sqrt(A) * alpha)) / a0
        self.high_filter.a1 = (2.0 * ((A - 1.0) - (A + 1.0) * cos_w0)) / a0
        self.high_filter.a2 = ((A + 1.0) - (A - 1.0) * cos_w0 - 2.0 * math.sqrt(A) * alpha) / a0

    def process(self, audio: np.ndarray) -> np.ndarray:
        if not self.enabled or len(audio) == 0:
            return audio

        out = audio
        if self.highpass_enabled:
            out = self.hp_filter.process_block(out)
        out = self.low_filter.process_block(out)
        out = self.mid_filter.process_block(out)
        out = self.high_filter.process_block(out)
        return out
