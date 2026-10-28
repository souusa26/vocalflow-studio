"""Streaming granular pitch shift with two crossfaded delay heads.

Delay memory and read phase survive callback boundaries. The 40 ms grain
window adds algorithmic latency; this is not a formant-preserving PSOLA.
"""
import math
import numpy as np

try:
    from numba import njit
except ImportError:
    def njit(**kwargs):
        return lambda function: function


@njit(fastmath=True)
def _shift_block(audio, ratio, memory, write_pos, phase, window):
    out = np.zeros_like(audio)
    capacity = len(memory)
    for i in range(len(audio)):
        memory[write_pos] = audio[i]
        phase2 = (phase + 0.5) % 1.0
        weight = math.sin(math.pi * phase) ** 2
        for channel in range(audio.shape[1]):
            sample = 0.0
            for head in range(2):
                p = phase if head == 0 else phase2
                gain = weight if head == 0 else 1.0 - weight
                position = (write_pos - 2.0 - p * window) % capacity
                index = int(position)
                fraction = position - index
                value = ((1.0 - fraction) * memory[index, channel]
                         + fraction * memory[(index + 1) % capacity, channel])
                sample += gain * value
            out[i, channel] = sample
        phase = (phase + (1.0 - ratio) / window) % 1.0
        write_pos = (write_pos + 1) % capacity
    return out, write_pos, phase


class StreamingPitchShifter:
    def __init__(self, sample_rate=48000):
        self.window = max(64, int(sample_rate * 0.04))
        self.memory = np.zeros((self.window + 8, 2), dtype=np.float32)
        self.write_pos = 0
        self.phase = 0.25
        self.grain_window = float(self.window)

    def process(self, audio, ratio, period=None):
        audio = np.asarray(audio, dtype=np.float32)
        mono_vector = audio.ndim == 1
        channels = 1 if mono_vector else audio.shape[1]
        stereo = np.repeat(audio.reshape(-1, 1), 2, axis=1) if channels == 1 else audio
        if period is not None:
            # Align the heads to whole pitch periods to suppress modulation sidebands.
            periods = max(2, 2 * int(self.window / (2 * period)))
            self.grain_window = min(float(self.window), periods * period)
        out, self.write_pos, self.phase = _shift_block(
            stereo, ratio, self.memory, self.write_pos, self.phase, self.grain_window)
        return out[:, 0] if mono_vector else out[:, :channels]

    def warm_up(self):
        _shift_block(np.zeros((1, 2), dtype=np.float32), 1.0,
                     self.memory.copy(), 0, 0.25, self.grain_window)
