"""
Motor Principal de Áudio em Tempo Real (Audio Engine).
Conecta o microfone de entrada à cadeia DSP, ao reprodutor de stems e distribui para:
1. Microfone Virtual (Discord / OBS).
2. Monitor 1 (ex: Fone de Ouvido).
3. Monitor 2 (ex: Caixas de Som / Retorno com aviso de microfonia).
"""

import time
import threading
from typing import Optional, Dict, Callable
import numpy as np
import sounddevice as sd

from app.audio.ring_buffer import AudioRingBuffer
from app.audio.dsp.chain import VocalFXChain
from app.stems.player import StemPlayer

class AudioEngine:
    def __init__(self, sample_rate: int = 48000, block_size: int = 256):
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.is_running = False

        # DSP e Reprodutor de Stems
        self.fx_chain = VocalFXChain(sample_rate)
        self.stem_player = StemPlayer(sample_rate)

        # Ring Buffers para cada saída (Desacoplamento lock-free)
        self.buf_virtual = AudioRingBuffer(capacity=32768, channels=2)
        self.buf_mon1 = AudioRingBuffer(capacity=32768, channels=2)
        self.buf_mon2 = AudioRingBuffer(capacity=32768, channels=2)

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
        """Inicia os fluxos de áudio de entrada e saída."""
        if self.is_running:
            return

        self.buf_virtual.clear()
        self.buf_mon1.clear()
        self.buf_mon2.clear()

        try:
            # 1. Abre Stream de Entrada (Microfone)
            self._stream_input = sd.InputStream(
                device=self.input_device_id,
                channels=1,
                samplerate=self.sample_rate,
                blocksize=self.block_size,
                callback=self._input_callback,
                dtype="float32"
            )
            self._stream_input.start()

            # 2. Abre Stream do Cabo Virtual (Discord / OBS) se configurado
            if self.virtual_device_id is not None:
                try:
                    self._stream_virtual = sd.OutputStream(
                        device=self.virtual_device_id,
                        channels=2,
                        samplerate=self.sample_rate,
                        blocksize=self.block_size,
                        callback=self._virtual_callback,
                        dtype="float32"
                    )
                    self._stream_virtual.start()
                except Exception as e:
                    print(f"[AudioEngine] Aviso ao iniciar Cabo Virtual: {e}")

            # 3. Abre Stream do Monitor 1 (Fones) se ativado
            if self.monitor1_enabled and self.monitor1_device_id is not None:
                try:
                    self._stream_mon1 = sd.OutputStream(
                        device=self.monitor1_device_id,
                        channels=2,
                        samplerate=self.sample_rate,
                        blocksize=self.block_size,
                        callback=self._mon1_callback,
                        dtype="float32"
                    )
                    self._stream_mon1.start()
                except Exception as e:
                    print(f"[AudioEngine] Aviso ao iniciar Monitor 1: {e}")

            # 4. Abre Stream do Monitor 2 (Caixas) se ativado
            if self.monitor2_enabled and self.monitor2_device_id is not None:
                try:
                    self._stream_mon2 = sd.OutputStream(
                        device=self.monitor2_device_id,
                        channels=2,
                        samplerate=self.sample_rate,
                        blocksize=self.block_size,
                        callback=self._mon2_callback,
                        dtype="float32"
                    )
                    self._stream_mon2.start()
                except Exception as e:
                    print(f"[AudioEngine] Aviso ao iniciar Monitor 2: {e}")

            self.is_running = True

        except Exception as e:
            self.stop()
            err_msg = f"Erro ao iniciar áudio: {str(e)}"
            if self.on_error:
                self.on_error(err_msg)
            raise RuntimeError(err_msg)

    def stop(self):
        """Para todos os fluxos de áudio e limpa recursos."""
        self.is_running = False

        for s in [self._stream_input, self._stream_virtual, self._stream_mon1, self._stream_mon2]:
            if s is not None:
                try:
                    s.stop()
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
        """
        Callback central de captura de microfone:
        Aplica os efeitos DSP e distribui os blocos nos ring buffers correspondentes.
        """
        if status:
            pass  # Overflow / Underflow flag

        # Áudio do microfone mono -> estéreo
        raw_vocal = indata.copy()

        # 1. Processa pela cadeia de efeitos vocais
        processed_vocal = self.fx_chain.process(raw_vocal)

        # Garante estéreo
        if processed_vocal.ndim == 1:
            processed_vocal = np.column_stack((processed_vocal, processed_vocal))
        elif processed_vocal.ndim == 2 and processed_vocal.shape[1] == 1:
            processed_vocal = np.repeat(processed_vocal, 2, axis=1)

        # 2. Pega áudio do backing track (stems) sincronizado
        backing_block = self.stem_player.get_next_block(frames)

        # 3. Buffer do Microfone Virtual (Discord/OBS):
        # Envia a voz processada + instrumental SE a opção estiver explicitamente marcada
        if self.stem_player.send_to_virtual_mic:
            virtual_mix = processed_vocal + backing_block
        else:
            virtual_mix = processed_vocal

        self.buf_virtual.write(virtual_mix)

        # 4. Buffer de Monitor 1 (Fones de Ouvido):
        if self.monitor1_enabled:
            if self.stem_player.send_to_monitors:
                mon1_mix = (processed_vocal + backing_block) * self.monitor1_volume
            else:
                mon1_mix = processed_vocal * self.monitor1_volume
            self.buf_mon1.write(mon1_mix)

        # 5. Buffer de Monitor 2 (Caixas de Som):
        if self.monitor2_enabled:
            if self.stem_player.send_to_monitors:
                mon2_mix = (processed_vocal + backing_block) * self.monitor2_volume
            else:
                mon2_mix = processed_vocal * self.monitor2_volume
            self.buf_mon2.write(mon2_mix)

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
        self.monitor1_enabled = enabled
        if volume is not None:
            self.monitor1_volume = max(0.0, min(1.5, float(volume)))
        if device_id is not None:
            self.monitor1_device_id = device_id
        # Reinicia stream se estiver rodando
        if self.is_running:
            self._restart_monitor1_stream()

    def set_monitor2(self, enabled: bool, volume: Optional[float] = None, device_id: Optional[int] = None):
        self.monitor2_enabled = enabled
        if volume is not None:
            self.monitor2_volume = max(0.0, min(1.5, float(volume)))
        if device_id is not None:
            self.monitor2_device_id = device_id
        if self.is_running:
            self._restart_monitor2_stream()

    def _restart_monitor1_stream(self):
        if self._stream_mon1 is not None:
            try:
                self._stream_mon1.stop()
                self._stream_mon1.close()
            except Exception:
                pass
            self._stream_mon1 = None

        if self.monitor1_enabled and self.monitor1_device_id is not None:
            try:
                self._stream_mon1 = sd.OutputStream(
                    device=self.monitor1_device_id,
                    channels=2,
                    samplerate=self.sample_rate,
                    blocksize=self.block_size,
                    callback=self._mon1_callback,
                    dtype="float32"
                )
                self._stream_mon1.start()
            except Exception as e:
                print(f"[AudioEngine] Erro ao reabrir Monitor 1: {e}")

    def _restart_monitor2_stream(self):
        if self._stream_mon2 is not None:
            try:
                self._stream_mon2.stop()
                self._stream_mon2.close()
            except Exception:
                pass
            self._stream_mon2 = None

        if self.monitor2_enabled and self.monitor2_device_id is not None:
            try:
                self._stream_mon2 = sd.OutputStream(
                    device=self.monitor2_device_id,
                    channels=2,
                    samplerate=self.sample_rate,
                    blocksize=self.block_size,
                    callback=self._mon2_callback,
                    dtype="float32"
                )
                self._stream_mon2.start()
            except Exception as e:
                print(f"[AudioEngine] Erro ao reabrir Monitor 2: {e}")
