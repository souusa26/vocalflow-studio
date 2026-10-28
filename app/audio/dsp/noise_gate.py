"""
Processador de Noise Gate (Redução de Ruído para Gravação Vocal).
Corta ruídos de fundo, ar-condicionado e respirações indesejadas antes da afinação e compressão.
"""

import numpy as np

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

    def process(self, audio: np.ndarray) -> np.ndarray:
        if not self.enabled or len(audio) == 0:
            return audio

        # Converte para mono para análise do envelope
        if audio.ndim == 2:
            mono = np.mean(audio, axis=1)
        else:
            mono = audio

        frames = len(mono)
        gain_envelope = np.zeros(frames, dtype=np.float32)

        thresh_linear = 10.0 ** (self.threshold_db / 20.0)
        floor_linear = 10.0 ** (self.reduction_db / 20.0)

        # Coeficientes de atenuação exponencial
        attack_coef = np.exp(-1.0 / (self.sample_rate * (self.attack_ms / 1000.0)))
        release_coef = np.exp(-1.0 / (self.sample_rate * (self.release_ms / 1000.0)))
        hold_samples = int(self.sample_rate * (self.hold_ms / 1000.0))

        cur_gain = self._current_gain
        hold_count = self._hold_counter

        for i in range(frames):
            level = abs(mono[i])
            if level >= thresh_linear:
                # Sinal acima do limiar: abre imediatamente
                target_gain = 1.0
                cur_gain = attack_coef * cur_gain + (1.0 - attack_coef) * target_gain
                hold_count = hold_samples
            else:
                if hold_count > 0:
                    hold_count -= 1
                    target_gain = 1.0
                    cur_gain = attack_coef * cur_gain + (1.0 - attack_coef) * target_gain
                else:
                    target_gain = floor_linear
                    cur_gain = release_coef * cur_gain + (1.0 - release_coef) * target_gain

            gain_envelope[i] = cur_gain

        self._current_gain = cur_gain
        self._hold_counter = hold_count

        if audio.ndim == 2:
            return audio * gain_envelope[:, np.newaxis]
        return audio * gain_envelope
