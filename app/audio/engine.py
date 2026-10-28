"""
Motor Principal de Áudio em Tempo Real (Audio Engine).
Conecta o microfone de entrada à cadeia DSP, ao reprodutor de stems e distribui para:
1. Microfone Virtual (Discord / OBS).
2. Monitor 1 (ex: Fone de Ouvido).
3. Monitor 2 (ex: Caixas de Som / Retorno com aviso de microfonia).
"""

from typing import Optional, Dict, Callable
import numpy as np
import sounddevice as sd

from app.audio.ring_buffer import AudioRingBuffer
from app.audio.dsp.chain import VocalFXChain
from app.audio.dsp.limiter import LimiterAndMeter
from app.stems.player import StemPlayer

class AudioEngine:
    def __init__(self, sample_rate: int = 48000, block_size: int = 256):
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.is_running = False
        self.last_error = None

        # DSP e Reprodutor de Stems
        self.fx_chain = VocalFXChain(sample_rate)
        self.stem_player = StemPlayer(sample_rate)

        # Buffers independentes e limitados para cada saída
        self.buf_virtual = AudioRingBuffer(capacity=32768, channels=2)
        self.buf_mon1 = AudioRingBuffer(capacity=32768, channels=2)
        self.buf_mon2 = AudioRingBuffer(capacity=32768, channels=2)

        self.output_limiters = {name: LimiterAndMeter(sample_rate)
                                for name in ("virtual", "mon1", "mon2")}

        # Identificadores de dispositivos selecionados
        self.input_device_id: Optional[int] = None
        self.virtual_device_id: Optional[int] = None
        self.monitor1_device_id: Optional[int] = None
        self.monitor2_device_id: Optional[int] = None

        # Controles de Monitoramento
        self.monitor1_enabled = True
        self.monitor2_enabled = False
        self.monitor1_volume = 1.0
        self.monitor2_volume = 1.0

        # Streams PortAudio / SoundDevice
        self._stream_input: Optional[sd.InputStream] = None
        self._stream_virtual: Optional[sd.OutputStream] = None
        self._stream_mon1: Optional[sd.OutputStream] = None
        self._stream_mon2: Optional[sd.OutputStream] = None

        # Callbacks de notificação de status e erros
        self.on_error: Optional[Callable[[str], None]] = None
        self.on_device_state_changed: Optional[Callable[[], None]] = None

    def start(self):
        """Open all selected destinations or roll back the whole start operation."""
        if self.is_running:
            return
        self.last_error = None
        self.buf_virtual.clear()
        self.buf_mon1.clear()
        self.buf_mon2.clear()
        self.output_limiters = {name: LimiterAndMeter(self.sample_rate)
                                for name in ("virtual", "mon1", "mon2")}
        try:
            destinations = [
                ("_stream_virtual", self.virtual_device_id, self._virtual_callback),
                ("_stream_mon1", self.monitor1_device_id if self.monitor1_enabled else None, self._mon1_callback),
                ("_stream_mon2", self.monitor2_device_id if self.monitor2_enabled else None, self._mon2_callback),
            ]
            if not any(device is not None for _, device, _ in destinations):
                raise ValueError("Selecione uma saída virtual ou um monitor de áudio.")
            self.fx_chain.autotune.warm_up()
            self._stream_input = sd.InputStream(
                device=self.input_device_id, channels=1, samplerate=self.sample_rate,
                blocksize=self.block_size, callback=self._input_callback, dtype="float32")
            for attribute, device, callback in destinations:
                if device is not None:
                    stream = sd.OutputStream(device=device, channels=2,
                        samplerate=self.sample_rate, blocksize=self.block_size,
                        callback=callback, dtype="float32")
                    setattr(self, attribute, stream)
                    stream.start()
            self.is_running = True
            self._stream_input.start()
        except Exception as exc:
            self.stop()
            self.last_error = f"Erro ao iniciar áudio: {exc}"
            if self.on_error:
                self.on_error(self.last_error)
            raise RuntimeError(self.last_error) from exc

    def configure(self, sample_rate=None, block_size=None):
        """Stop callbacks before rebuilding rate-dependent effects and stems."""
        rate = self.sample_rate if sample_rate is None else int(sample_rate)
        size = self.block_size if block_size is None else int(block_size)
        if rate not in (44100, 48000) or size not in (128, 256, 512, 1024):
            raise ValueError("Configuração de áudio não suportada.")
        if (rate, size) == (self.sample_rate, self.block_size):
            return
        running = self.is_running
        self.stop()
        try:
            if rate != self.sample_rate:
                self.fx_chain.set_sample_rate(rate)
                self.stem_player.set_sample_rate(rate)
            self.sample_rate, self.block_size = rate, size
            if running:
                self.start()
        except Exception as exc:
            self.last_error = f"Falha ao reconfigurar áudio: {exc}"
            raise RuntimeError(self.last_error) from exc

    def stop(self):
        """Para todos os fluxos de áudio e limpa recursos."""
        self.is_running = False

        for s in [self._stream_input, self._stream_virtual, self._stream_mon1, self._stream_mon2]:
            if s is not None:
                try:
                    s.stop()
                except Exception:
                    pass
                finally:
                    try:
                        s.close()
                    except Exception:
                        pass

        self._stream_input = None
        self._stream_virtual = None
        self._stream_mon1 = None
        self._stream_mon2 = None

        self.buf_virtual.clear()
        self.buf_mon1.clear()
        self.buf_mon2.clear()

    def _input_callback(self, indata, frames, time_info, status):
        try:
            self._process_input(indata, frames)
        except Exception as exc:
            # The UI timer reports this on the Qt thread and releases the streams.
            self.last_error = f"Falha no processamento de áudio: {exc}"
            self.is_running = False
            raise sd.CallbackAbort from exc

    def _process_input(self, indata, frames):
        processed = self.fx_chain.process(indata)
        if processed.ndim == 1:
            processed = np.column_stack((processed, processed))
        backing = self.stem_player.get_next_block(frames)
        virtual = processed + backing if self.stem_player.send_to_virtual_mic else processed
        self.buf_virtual.write(self.output_limiters["virtual"].process(virtual))
        monitor = processed + backing if self.stem_player.send_to_monitors else processed
        if self.monitor1_enabled:
            self.buf_mon1.write(self.output_limiters["mon1"].process(monitor * self.monitor1_volume))
        if self.monitor2_enabled:
            self.buf_mon2.write(self.output_limiters["mon2"].process(monitor * self.monitor2_volume))

    def _virtual_callback(self, outdata, frames, time_info, status):
        chunk = self.buf_virtual.read(frames)
        outdata[:] = chunk

    def _mon1_callback(self, outdata, frames, time_info, status):
        chunk = self.buf_mon1.read(frames)
        outdata[:] = chunk

    def _mon2_callback(self, outdata, frames, time_info, status):
        chunk = self.buf_mon2.read(frames)
        outdata[:] = chunk

    def set_monitor1(self, enabled: bool, volume: Optional[float] = None, device_id: Optional[int] = None):
        restart = self.monitor1_enabled != enabled or (device_id is not None and device_id != self.monitor1_device_id)
        self.monitor1_enabled = enabled
        if volume is not None:
            self.monitor1_volume = max(0.0, min(1.5, float(volume)))
        if device_id is not None:
            self.monitor1_device_id = device_id
        # Reinicia stream se estiver rodando
        if self.is_running and restart:
            try:
                self._restart_monitor1_stream()
            except RuntimeError:
                return False
        return True

    def set_monitor2(self, enabled: bool, volume: Optional[float] = None, device_id: Optional[int] = None):
        restart = self.monitor2_enabled != enabled or (device_id is not None and device_id != self.monitor2_device_id)
        self.monitor2_enabled = enabled
        if volume is not None:
            self.monitor2_volume = max(0.0, min(1.5, float(volume)))
        if device_id is not None:
            self.monitor2_device_id = device_id
        if self.is_running and restart:
            try:
                self._restart_monitor2_stream()
            except RuntimeError:
                return False
        return True

    def _restart_monitor1_stream(self):
        # Restart the whole group so failures cannot leave the UI claiming a healthy stream.
        self.stop()
        self.start()

    def _restart_monitor2_stream(self):
        # Restart the whole group so failures cannot leave the UI claiming a healthy stream.
        self.stop()
        self.start()
