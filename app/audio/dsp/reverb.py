"""
Reverb Algorítmico Estéreo para Vocais (Modelo Freeverb / Schroeder Reverb).
Cria ambiência de estúdio rica, desde sala pequena até espaço amplo e atmosférico de Trap.
"""

import numpy as np

try:
    from numba import njit
except ImportError:
    def njit(*args, **kwargs):
        return lambda fn: fn


@njit(fastmath=True)
def _reverb_block(mono, feedback, damp, comb_buf, comb_sizes, comb_pos,
                  comb_stores, ap_buf, ap_sizes, ap_pos):
    wet = np.zeros((len(mono), 2), dtype=np.float32)
    for i in range(len(mono)):
        inp = mono[i] * 0.015
        for ch in range(2):
            value = 0.0
            for j in range(comb_sizes.shape[1]):
                pos = comb_pos[ch, j]
                out = comb_buf[ch, j, pos]
                store = out * (1.0 - damp) + comb_stores[ch, j] * damp
                comb_stores[ch, j] = store
                comb_buf[ch, j, pos] = inp + store * feedback
                comb_pos[ch, j] = (pos + 1) % comb_sizes[ch, j]
                value += out
            for j in range(ap_sizes.shape[1]):
                pos = ap_pos[ch, j]
                stored = ap_buf[ch, j, pos]
                next_value = -value + stored
                ap_buf[ch, j, pos] = value + stored * 0.5
                ap_pos[ch, j] = (pos + 1) % ap_sizes[ch, j]
                value = next_value
            wet[i, ch] = value
    return wet

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

        # Contiguous buffers let the native DSP kernel process all filters per block.
        self._comb_sizes = np.array([[int(t * scale) for t in COMB_TUNINGS],
            [int((t + STEREO_SPREAD) * scale) for t in COMB_TUNINGS]], dtype=np.int64)
        self._ap_sizes = np.array([[int(t * scale) for t in ALLPASS_TUNINGS],
            [int((t + STEREO_SPREAD) * scale) for t in ALLPASS_TUNINGS]], dtype=np.int64)
        self._comb_buf = np.zeros((2, len(COMB_TUNINGS), self._comb_sizes.max()), dtype=np.float32)
        self._ap_buf = np.zeros((2, len(ALLPASS_TUNINGS), self._ap_sizes.max()), dtype=np.float32)
        self._comb_pos = np.zeros_like(self._comb_sizes)
        self._ap_pos = np.zeros_like(self._ap_sizes)
        self._comb_stores = np.zeros(self._comb_sizes.shape, dtype=np.float64)

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

        wet = _reverb_block(np.ascontiguousarray(in_mono, dtype=np.float32), feedback, damp,
                            self._comb_buf, self._comb_sizes, self._comb_pos, self._comb_stores,
                            self._ap_buf, self._ap_sizes, self._ap_pos)
        wet_l, wet_r = wet[:, 0], wet[:, 1]

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

    def warm_up(self):
        """Compile the DSP kernel without changing the live reverb state."""
        _reverb_block(np.zeros(1, dtype=np.float32), 0.8, self.damping,
                      self._comb_buf.copy(), self._comb_sizes, self._comb_pos.copy(),
                      self._comb_stores.copy(), self._ap_buf.copy(), self._ap_sizes,
                      self._ap_pos.copy())
