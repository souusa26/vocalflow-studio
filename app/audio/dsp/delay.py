"""
Efeito de Eco / Delay em Tempo Real.
Delay estéreo estilo fita com filtro passa-baixas no feedback e controle de repetição e tempo.
"""

import numpy as np

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

        out_wet = np.zeros((frames, 2), dtype=np.float32)
        w_pos = self.write_pos
        buf = self.buffer
        fb = self.feedback
        damp = self.damping
        last_fb = self._last_feedback_sample

        for i in range(frames):
            # Índices de leitura nos buffers de atraso
            read_pos_l = (w_pos - delay_samples_l) % self.max_frames
            read_pos_r = (w_pos - delay_samples_r) % self.max_frames

            tap_l = buf[read_pos_l, 0]
            tap_r = buf[read_pos_r, 1]

            out_wet[i, 0] = tap_l
            out_wet[i, 1] = tap_r

            # Filtro de amortecimento de altas frequências nas repetições
            fb_l = tap_l * fb
            fb_r = tap_r * fb
            filtered_fb_l = (1.0 - damp) * fb_l + damp * last_fb[0]
            filtered_fb_r = (1.0 - damp) * fb_r + damp * last_fb[1]
            last_fb[0] = filtered_fb_l
            last_fb[1] = filtered_fb_r

            # Grava no buffer a entrada combinada com o feedback
            buf[w_pos, 0] = in_stereo[i, 0] + filtered_fb_l
            buf[w_pos, 1] = in_stereo[i, 1] + filtered_fb_r

            w_pos = (w_pos + 1) % self.max_frames

        self.write_pos = w_pos
        self._last_feedback_sample = last_fb

        # Mistura Dry / Wet
        dry_gain = 1.0 - (self.dry_wet * 0.4)
        wet_gain = self.dry_wet
        mixed = dry_gain * in_stereo + wet_gain * out_wet

        if audio.ndim == 1:
            return np.mean(mixed, axis=1)
        return mixed
