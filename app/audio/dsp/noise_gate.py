"""
Processador de Noise Gate (Redução de Ruído para Gravação Vocal).
Corta ruídos de fundo, ar-condicionado e respirações indesejadas antes da afinação e compressão.
"""

import numpy as np

try:
    from numba import njit
except ImportError:
    def njit(*args, **kwargs):
        return lambda func: func


@njit()
def _gate_envelope(mono, thresh, floor, attack, release, hold_samples, gain, hold):
    envelope = np.zeros(len(mono), dtype=np.float32)
    for i in range(len(mono)):
        if abs(mono[i]) >= thresh:
            gain = attack * gain + (1.0 - attack)
            hold = hold_samples
        elif hold > 0:
            hold -= 1
            gain = attack * gain + (1.0 - attack)
        else:
            gain = release * gain + (1.0 - release) * floor
        envelope[i] = gain
    return envelope, gain, hold

class NoiseGate:
    def __init__(self, sample_rate: int = 48000):
        self.sample_rate = sample_rate
        self.enabled = True
        
        # Parâmetros
        self.threshold_db = -45.0  # Nível abaixo do qual o gate fecha
        self.attack_ms = 2.0       # Tempo para abrir
        self.hold_ms = 20.0        # Tempo para manter aberto após sinal cair
        self.release_ms = 80.0     # Tempo para fechar suavemente
        self.reduction_db = -60.0  # Atenuação quando fechado

        # Estado interno
        self._current_gain = 1.0
        self._hold_counter = 0

    def set_params(self, threshold_db: float = None, attack_ms: float = None,
                   release_ms: float = None, hold_ms: float = None,
                   reduction_db: float = None, enabled: bool = None):
        if threshold_db is not None:
            self.threshold_db = float(threshold_db)
        if attack_ms is not None:
            self.attack_ms = max(0.1, float(attack_ms))
        if release_ms is not None:
            self.release_ms = max(1.0, float(release_ms))
        if hold_ms is not None:
            self.hold_ms = max(0.0, float(hold_ms))
        if reduction_db is not None:
            self.reduction_db = float(reduction_db)
        if enabled is not None:
            self.enabled = bool(enabled)

    def warm_up(self):
        _gate_envelope(np.zeros(1, dtype=np.float32), 0.01, 0.001,
                       0.9, 0.99, 1, 1.0, 0)

    def process(self, audio: np.ndarray) -> np.ndarray:
        if not self.enabled or len(audio) == 0:
            return audio

        # Converte para mono para análise do envelope
        if audio.ndim == 2:
            mono = np.mean(audio, axis=1)
        else:
            mono = audio

        thresh_linear = 10.0 ** (self.threshold_db / 20.0)
        floor_linear = 10.0 ** (self.reduction_db / 20.0)
        attack_coef = np.exp(-1.0 / (self.sample_rate * (self.attack_ms / 1000.0)))
        release_coef = np.exp(-1.0 / (self.sample_rate * (self.release_ms / 1000.0)))
        hold_samples = int(self.sample_rate * (self.hold_ms / 1000.0))
        gain_envelope, self._current_gain, self._hold_counter = _gate_envelope(
            mono, thresh_linear, floor_linear, attack_coef, release_coef,
            hold_samples, self._current_gain, self._hold_counter)

        if audio.ndim == 2:
            return audio * gain_envelope[:, np.newaxis]
        return audio * gain_envelope
