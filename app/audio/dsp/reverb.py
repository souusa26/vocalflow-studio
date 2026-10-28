"""
Reverb Algorítmico Estéreo para Vocais (Modelo Freeverb / Schroeder Reverb).
Cria ambiência de estúdio rica, desde sala pequena até espaço amplo e atmosférico de Trap.
"""

import numpy as np

# Atrasos base dos filtros comb e all-pass (ajustados para 44.1k/48k)
COMB_TUNINGS = [1116, 1188, 1277, 1356, 1422, 1491, 1557, 1617]
ALLPASS_TUNINGS = [556, 441, 341, 225]
STEREO_SPREAD = 23

class CombFilter:
    def __init__(self, size: int):
        self.buffer = np.zeros(size, dtype=np.float32)
        self.size = size
        self.pos = 0
        self.filter_store = 0.0

    def process(self, x: float, feedback: float, damp: float) -> float:
        out = self.buffer[self.pos]
        self.filter_store = out * (1.0 - damp) + self.filter_store * damp
        self.buffer[self.pos] = x + self.filter_store * feedback
        self.pos = (self.pos + 1) % self.size
        return out

class AllpassFilter:
    def __init__(self, size: int):
        self.buffer = np.zeros(size, dtype=np.float32)
        self.size = size
        self.pos = 0

    def process(self, x: float) -> float:
        buf_out = self.buffer[self.pos]
        y = -x + buf_out
        self.buffer[self.pos] = x + (buf_out * 0.5)
        self.pos = (self.pos + 1) % self.size
        return y

class Reverb:
    def __init__(self, sample_rate: int = 48000):
        self.sample_rate = sample_rate
        self.enabled = False
        
        # Parâmetros
        self.room_size = 0.65       # Tamanho da sala / Decay (0.0 a 0.95)
        self.damping = 0.30         # Absorção de agudos (0.0 a 0.9)
        self.dry_wet = 0.25         # Quantidade de reverb
        self.width = 1.0            # Abertura estéreo

        # Escala de acordo com a taxa de amostragem
        scale = sample_rate / 44100.0

        # Filtros Comb Canal Esquerdo e Direito
        self.combs_l = [CombFilter(int(t * scale)) for t in COMB_TUNINGS]
        self.combs_r = [CombFilter(int((t + STEREO_SPREAD) * scale)) for t in COMB_TUNINGS]

        # Filtros All-Pass Canal Esquerdo e Direito
        self.allpasses_l = [AllpassFilter(int(t * scale)) for t in ALLPASS_TUNINGS]
        self.allpasses_r = [AllpassFilter(int((t + STEREO_SPREAD) * scale)) for t in ALLPASS_TUNINGS]

    def set_params(self, room_size: float = None, damping: float = None,
                   dry_wet: float = None, width: float = None, enabled: bool = None):
        if room_size is not None:
            self.room_size = max(0.0, min(0.96, float(room_size)))
        if damping is not None:
            self.damping = max(0.0, min(0.9, float(damping)))
        if dry_wet is not None:
            self.dry_wet = max(0.0, min(1.0, float(dry_wet)))
        if width is not None:
            self.width = max(0.0, min(1.0, float(width)))
        if enabled is not None:
            self.enabled = bool(enabled)

    def process(self, audio: np.ndarray) -> np.ndarray:
        if not self.enabled or len(audio) == 0 or self.dry_wet <= 0.001:
            return audio

        frames = len(audio)
        if audio.ndim == 1:
            in_mono = audio
            orig_stereo = np.column_stack((audio, audio))
        else:
            in_mono = np.mean(audio, axis=1)
            orig_stereo = audio

        feedback = 0.7 + (self.room_size * 0.28)
        damp = self.damping

        wet_l = np.zeros(frames, dtype=np.float32)
        wet_r = np.zeros(frames, dtype=np.float32)

        for i in range(frames):
            inp = in_mono[i] * 0.015

            # Acumula combs
            out_l = 0.0
            out_r = 0.0
            for comb in self.combs_l:
                out_l += comb.process(inp, feedback, damp)
            for comb in self.combs_r:
                out_r += comb.process(inp, feedback, damp)

            # Difusão por all-passes
            for ap in self.allpasses_l:
                out_l = ap.process(out_l)
            for ap in self.allpasses_r:
                out_r = ap.process(out_r)

            wet_l[i] = out_l
            wet_r[i] = out_r

        # Mix estéreo com controle de largura
        wet1 = self.dry_wet * (self.width / 2.0 + 0.5)
        wet2 = self.dry_wet * ((1.0 - self.width) / 2.0)
        out_wet_l = wet_l * wet1 + wet_r * wet2
        out_wet_r = wet_r * wet1 + wet_l * wet2

        dry_gain = 1.0 - (self.dry_wet * 0.4)
        out_stereo = np.column_stack((
            orig_stereo[:, 0] * dry_gain + out_wet_l,
            orig_stereo[:, 1] * dry_gain + out_wet_r
        ))

        if audio.ndim == 1:
            return np.mean(out_stereo, axis=1)
        return out_stereo
