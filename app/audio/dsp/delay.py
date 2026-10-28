"""
Efeito de Eco / Delay em Tempo Real.
Delay estéreo estilo fita com filtro passa-baixas no feedback e controle de repetição e tempo.
"""

import numpy as np

try:
    from numba import njit
except ImportError:
    def njit(*args, **kwargs):
        return lambda fn: fn


@njit(fastmath=True)
def _delay_block(audio, buf, w_pos, delay_l, delay_r, feedback, damp, last_fb):
    frames = len(audio)
    capacity = len(buf)
    wet = np.zeros((frames, 2), dtype=np.float32)
    for i in range(frames):
        for ch in range(2):
            delay = delay_l if ch == 0 else delay_r
            tap = buf[(w_pos - delay) % capacity, ch]
            wet[i, ch] = tap
            last_fb[ch] = (1.0 - damp) * tap * feedback + damp * last_fb[ch]
            buf[w_pos, ch] = audio[i, ch] + last_fb[ch]
        w_pos = (w_pos + 1) % capacity
    return wet, w_pos

class Delay:
    def __init__(self, sample_rate: int = 48000, max_delay_seconds: float = 2.0):
        self.sample_rate = sample_rate
        self.enabled = False
        
        # Parâmetros
        self.delay_time_ms = 250.0   # Tempo do eco em ms
        self.feedback = 0.40         # Repetições (0.0 a 0.85)
        self.damping = 0.35          # Filtro suave de repetições (estilo analógico)
        self.dry_wet = 0.30          # Nível do eco no mix final
        self.stereo_offset_ms = 15.0 # Diferença sutil entre canal L e R para ambiência

        # Buffer circular de atraso estéreo
        self.max_frames = int(sample_rate * max_delay_seconds)
        self.buffer = np.zeros((self.max_frames, 2), dtype=np.float32)
        self.write_pos = 0
        self._last_feedback_sample = np.zeros(2, dtype=np.float32)

    def set_params(self, delay_time_ms: float = None, feedback: float = None,
                   damping: float = None, dry_wet: float = None, enabled: bool = None):
        if delay_time_ms is not None:
            self.delay_time_ms = max(20.0, min(1500.0, float(delay_time_ms)))
        if feedback is not None:
            self.feedback = max(0.0, min(0.85, float(feedback)))
        if damping is not None:
            self.damping = max(0.0, min(0.9, float(damping)))
        if dry_wet is not None:
            self.dry_wet = max(0.0, min(1.0, float(dry_wet)))
        if enabled is not None:
            self.enabled = bool(enabled)

    def process(self, audio: np.ndarray) -> np.ndarray:
        if not self.enabled or len(audio) == 0 or self.dry_wet <= 0.001:
            return audio

        frames = len(audio)
        if audio.ndim == 1:
            in_stereo = np.column_stack((audio, audio))
        else:
            in_stereo = audio

        delay_samples_l = int(self.sample_rate * (self.delay_time_ms / 1000.0))
        delay_samples_r = int(self.sample_rate * ((self.delay_time_ms + self.stereo_offset_ms) / 1000.0))
        delay_samples_l = min(self.max_frames - 1, max(1, delay_samples_l))
        delay_samples_r = min(self.max_frames - 1, max(1, delay_samples_r))

        in_stereo = np.ascontiguousarray(in_stereo, dtype=np.float32)
        out_wet, self.write_pos = _delay_block(
            in_stereo, self.buffer, self.write_pos, delay_samples_l, delay_samples_r,
            self.feedback, self.damping, self._last_feedback_sample)

        # Mistura Dry / Wet
        dry_gain = 1.0 - (self.dry_wet * 0.4)
        wet_gain = self.dry_wet
        mixed = dry_gain * in_stereo + wet_gain * out_wet

        if audio.ndim == 1:
            return np.mean(mixed, axis=1)
        return mixed

    def warm_up(self):
        """Compile the DSP kernel without changing the live delay state."""
        _delay_block(np.zeros((1, 2), dtype=np.float32),
                     np.zeros((2, 2), dtype=np.float32), 0, 1, 1,
                     self.feedback, self.damping, np.zeros(2, dtype=np.float32))
