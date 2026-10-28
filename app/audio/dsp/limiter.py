"""
Limiter de Saída e Medidor de Nível (Peak, RMS e Clip Indicator).
Evita qualquer distorção digital ou estouro de volume nas saídas e Discord/OBS.
"""

import numpy as np

try:
    from numba import njit
except ImportError:
    def njit(*args, **kwargs):
        return lambda func: func


@njit()
def _limit_envelope(peaks, ceiling, release_coef, env):
    envelope = np.ones(len(peaks), dtype=np.float32)
    for i in range(len(peaks)):
        p = peaks[i]
        target = ceiling / p if p > ceiling else 1.0
        if target < env:
            env = target
        else:
            env = release_coef * env + (1.0 - release_coef) * target
        envelope[i] = env
    return envelope, env

class LimiterAndMeter:
    def __init__(self, sample_rate: int = 48000):
        self.sample_rate = sample_rate
        self.ceiling_db = -0.3   # Teto máximo seguro em dBFS (-0.3dB)
        self.release_ms = 40.0
        
        self.input_peak_db = -100.0
        self.input_rms_db = -100.0
        self.output_peak_db = -100.0
        self.output_rms_db = -100.0
        self.clipped = False

        self._envelope = 1.0

    def calculate_levels(self, audio: np.ndarray) -> tuple[float, float, bool]:
        """Calcula Peak (dBFS), RMS (dBFS) e flag de clipagem."""
        if len(audio) == 0:
            return -100.0, -100.0, False

        abs_audio = np.abs(audio)
        peak = float(np.max(abs_audio))
        rms = float(np.sqrt(np.mean(abs_audio ** 2)))

        peak_db = 20.0 * np.log10(max(peak, 1e-5))
        rms_db = 20.0 * np.log10(max(rms, 1e-5))
        clipped = (peak >= 0.999)

        return peak_db, rms_db, clipped

    def warm_up(self):
        _limit_envelope(np.zeros(1, dtype=np.float32), 0.96, 0.99, 1.0)

    def process(self, audio: np.ndarray) -> np.ndarray:
        if len(audio) == 0:
            return audio

        # 1. Mede nível de entrada
        self.input_peak_db, self.input_rms_db, _ = self.calculate_levels(audio)

        # 2. Limiter de pico suave
        ceiling_linear = 10.0 ** (self.ceiling_db / 20.0)
        release_coef = np.exp(-1.0 / (self.sample_rate * (self.release_ms / 1000.0)))

        is_stereo = (audio.ndim == 2)
        if is_stereo:
            peaks = np.max(np.abs(audio), axis=1)
        else:
            peaks = np.abs(audio)

        gain_envelope, self._envelope = _limit_envelope(
            peaks, ceiling_linear, release_coef, self._envelope)

        # Aplica atenuação e saturação analógica tanh para picos extremos
        limited = audio * (gain_envelope[:, np.newaxis] if is_stereo else gain_envelope)
        
        # Final guard against overshoot; preserve signals below the ceiling.
        out = np.clip(limited, -ceiling_linear, ceiling_linear)

        # 3. Mede nível de saída
        self.output_peak_db, self.output_rms_db, _ = self.calculate_levels(out)
        self.clipped = self.input_peak_db >= -0.01

        return out
