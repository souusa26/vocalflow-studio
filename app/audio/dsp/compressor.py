"""
Compressor Dinâmico de Estúdio para Vocais.
Controla picos repentinos, proporciona consistência e 'punch' moderno para Hip-Hop e Rap.
"""

import numpy as np

class Compressor:
    def __init__(self, sample_rate: int = 48000):
        self.sample_rate = sample_rate
        self.enabled = True
        
        # Parâmetros
        self.threshold_db = -18.0   # Limiar de atuação
        self.ratio = 4.0            # Taxa de compressão (ex: 4:1)
        self.attack_ms = 15.0       # Tempo de ataque (ms)
        self.release_ms = 120.0     # Tempo de liberação (ms)
        self.makeup_gain_db = 4.0   # Ganho de compensação (dB)
        self.knee_db = 4.0          # Soft-knee para transições suaves

        # Estado interno
        self._envelope = 0.0
        self._current_gain_reduction_db = 0.0

    def set_params(self, threshold_db: float = None, ratio: float = None,
                   attack_ms: float = None, release_ms: float = None,
                   makeup_gain_db: float = None, enabled: bool = None):
        if threshold_db is not None:
            self.threshold_db = float(threshold_db)
        if ratio is not None:
            self.ratio = max(1.0, float(ratio))
        if attack_ms is not None:
            self.attack_ms = max(0.5, float(attack_ms))
        if release_ms is not None:
            self.release_ms = max(5.0, float(release_ms))
        if makeup_gain_db is not None:
            self.makeup_gain_db = float(makeup_gain_db)
        if enabled is not None:
            self.enabled = bool(enabled)

    def get_gain_reduction_db(self) -> float:
        """Retorna a redução de ganho atual para exibição na interface visual."""
        return self._current_gain_reduction_db

    def process(self, audio: np.ndarray) -> np.ndarray:
        if not self.enabled or len(audio) == 0:
            self._current_gain_reduction_db = 0.0
            return audio

        is_stereo = (audio.ndim == 2)
        if is_stereo:
            mono = np.max(np.abs(audio), axis=1)
        else:
            mono = np.abs(audio)

        frames = len(mono)
        gain_envelope = np.zeros(frames, dtype=np.float32)

        attack_coef = np.exp(-1.0 / (self.sample_rate * (self.attack_ms / 1000.0)))
        release_coef = np.exp(-1.0 / (self.sample_rate * (self.release_ms / 1000.0)))
        makeup_linear = 10.0 ** (self.makeup_gain_db / 20.0)

        env = self._envelope
        max_gr_db = 0.0

        for i in range(frames):
            level = mono[i]
            # Detector de envelope balístico
            if level > env:
                env = attack_coef * env + (1.0 - attack_coef) * level
            else:
                env = release_coef * env + (1.0 - release_coef) * level

            # Nível em dB
            level_db = 20.0 * np.log10(max(env, 1e-6))

            # Curva de ganho com soft-knee
            gr_db = 0.0
            if level_db > (self.threshold_db + self.knee_db / 2.0):
                gr_db = (level_db - self.threshold_db) * (1.0 - 1.0 / self.ratio)
            elif level_db > (self.threshold_db - self.knee_db / 2.0):
                diff = level_db - self.threshold_db + self.knee_db / 2.0
                gr_db = (diff * diff / (2.0 * self.knee_db)) * (1.0 - 1.0 / self.ratio)

            if gr_db > max_gr_db:
                max_gr_db = gr_db

            # Ganho linear a aplicar
            linear_gain = (10.0 ** (-gr_db / 20.0)) * makeup_linear
            gain_envelope[i] = linear_gain

        self._envelope = env
        self._current_gain_reduction_db = max_gr_db

        if is_stereo:
            return audio * gain_envelope[:, np.newaxis]
        return audio * gain_envelope
