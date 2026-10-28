"""
Ring buffer limitado e thread-safe para roteamento de áudio.
Permite desacoplar a captura do microfone das saídas independentes (Cabo Virtual e Monitores).
"""

import numpy as np
import threading

class AudioRingBuffer:
    def __init__(self, capacity: int = 65536, channels: int = 2):
        self.capacity = capacity
        self.channels = channels
        self.buffer = np.zeros((capacity, channels), dtype=np.float32)
        self.write_pos = 0
        self.read_pos = 0
        self._available = 0
        self.overrun_frames = 0
        self.underrun_frames = 0
        self._output_primed = False
        self._output_phase = 0.0
        self._last_output = np.zeros(channels, dtype=np.float32)
        self.lock = threading.Lock()

    def write(self, data: np.ndarray) -> int:
        """
        Escreve um bloco de áudio no buffer circular.
        data deve ter shape (frames, channels) ou (frames,).
        """
        if data.ndim == 1:
            if self.channels == 2:
                data = np.column_stack((data, data))
            else:
                data = data[:, np.newaxis]
        elif data.ndim == 2 and data.shape[1] == 1 and self.channels == 2:
            data = np.repeat(data, 2, axis=1)

        frames_to_write = data.shape[0]
        original_frames = frames_to_write
        if frames_to_write == 0:
            return 0

        with self.lock:
            dropped = max(0, self._available + frames_to_write - self.capacity)
            self.overrun_frames += dropped
            if frames_to_write >= self.capacity:
                data = data[-self.capacity:]
                frames_to_write = self.capacity
                self.read_pos = self.write_pos
                self._available = 0
            elif dropped:
                self.read_pos = (self.read_pos + dropped) % self.capacity
                self._available -= dropped
            # Escreve com wrap-around se necessário
            end_pos = self.write_pos + frames_to_write
            if end_pos <= self.capacity:
                self.buffer[self.write_pos:end_pos] = data
            else:
                first_part = self.capacity - self.write_pos
                second_part = frames_to_write - first_part
                self.buffer[self.write_pos:self.capacity] = data[:first_part]
                self.buffer[0:second_part] = data[first_part:]

            self.write_pos = (self.write_pos + frames_to_write) % self.capacity
            self._available += frames_to_write
        return original_frames

    def read(self, frames_to_read: int) -> np.ndarray:
        """
        Lê um bloco de frames do buffer. Se não houver dados suficientes,
        preenche a diferença com silêncio (zeros).
        """
        out = np.zeros((frames_to_read, self.channels), dtype=np.float32)
        if frames_to_read == 0:
            return out

        with self.lock:
            # Calcula quantos frames estão disponíveis
            available = self._available
            frames = min(frames_to_read, available)

            if frames > 0:
                end_pos = self.read_pos + frames
                if end_pos <= self.capacity:
                    out[:frames] = self.buffer[self.read_pos:end_pos]
                else:
                    first_part = self.capacity - self.read_pos
                    second_part = frames - first_part
                    out[:first_part] = self.buffer[self.read_pos:self.capacity]
                    out[first_part:frames] = self.buffer[0:second_part]

                self.read_pos = (self.read_pos + frames) % self.capacity
                self._available -= frames
            self.underrun_frames += frames_to_read - frames

        return out

    def available_read(self) -> int:
        with self.lock:
            return self._available

    def read_for_output(self, frames_to_read: int, target_frames: int) -> np.ndarray:
        """Read a continuous stream with a small prebuffer and clock-drift correction.

        Each physical/virtual device has its own clock. A gradual change of read
        rate keeps its queue near the target instead of periodically dropping an
        entire block or playing silence. This is a bounded linear resampler, not
        a replacement for a proper hardware synchronized stream.
        """
        out = np.zeros((frames_to_read, self.channels), dtype=np.float32)
        if frames_to_read <= 0:
            return out
        with self.lock:
            target = max(frames_to_read + 2, min(target_frames, self.capacity - 1))
            newly_primed = False
            if not self._output_primed:
                if self._available < target:
                    return out
                self._output_primed = True
                newly_primed = True

            # Bound pitch variation while absorbing small hardware clock drift.
            error = (self._available - target) / max(target, 1)
            rate = 1.0 + float(np.clip(error * 0.02, -0.003, 0.003))
            positions = self._output_phase + np.arange(frames_to_read) * rate
            indices = positions.astype(np.int64)
            # Linear interpolation needs the frame following the last position.
            readable = int(np.searchsorted(indices, self._available - 1, side="left"))
            count = min(frames_to_read, readable)
            if count:
                offsets = indices[:count]
                fraction = (positions[:count] - offsets).astype(np.float32)[:, None]
                a = self.buffer[(self.read_pos + offsets) % self.capacity]
                b = self.buffer[(self.read_pos + offsets + 1) % self.capacity]
                out[:count] = a + (b - a) * fraction
                advance = self._output_phase + count * rate
                consumed = int(advance)
                self._output_phase = advance - consumed
                self.read_pos = (self.read_pos + consumed) % self.capacity
                self._available -= consumed

            if newly_primed and count:
                fade = min(count, 64)
                out[:fade] *= np.linspace(0.0, 1.0, fade, dtype=np.float32)[:, None]

            if count < frames_to_read:
                # Fade to silence on a genuine underrun, then prebuffer again.
                self.underrun_frames += frames_to_read - count
                fade = min(count, 64)
                if fade:
                    out[count - fade:count] *= np.linspace(1.0, 0.0, fade, dtype=np.float32)[:, None]
                else:
                    fade = min(frames_to_read, 64)
                    out[:fade] = self._last_output * np.linspace(1.0, 0.0, fade, dtype=np.float32)[:, None]
                self.read_pos = self.write_pos
                self._available = 0
                self._output_phase = 0.0
                self._output_primed = False
            self._last_output = out[-1].copy()
        return out

    def clear(self):
        with self.lock:
            self.write_pos = 0
            self.read_pos = 0
            self._available = 0
            self.overrun_frames = self.underrun_frames = 0
            self._output_primed = False
            self._output_phase = 0.0
            self._last_output.fill(0)
            self.buffer.fill(0)
