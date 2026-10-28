"""
Cadeia de Processamento de Efeitos Vocais (FX Rack).
Gerencia a sequência completa de processamento:
Input Gain -> Noise Gate -> AutoTune -> EQ -> Compressor -> Delay -> Reverb -> Limiter -> Output Gain.
"""

import numpy as np
from typing import Dict, Any

from app.audio.dsp.noise_gate import NoiseGate
from app.audio.dsp.autotune import AutoTune
from app.audio.dsp.eq import Equalizer
from app.audio.dsp.compressor import Compressor
from app.audio.dsp.delay import Delay
from app.audio.dsp.reverb import Reverb
from app.audio.dsp.limiter import LimiterAndMeter

class VocalFXChain:
    def __init__(self, sample_rate: int = 48000):
        self.sample_rate = sample_rate
        self.input_gain = 1.0
        self.output_gain = 1.0

        # Módulos DSP
        self.gate = NoiseGate(sample_rate)
        self.autotune = AutoTune(sample_rate)
        self.eq = Equalizer(sample_rate)
        self.compressor = Compressor(sample_rate)
        self.delay = Delay(sample_rate)
        self.reverb = Reverb(sample_rate)
        self.limiter = LimiterAndMeter(sample_rate)

    def set_sample_rate(self, sample_rate: int):
        state = self.get_state()
        self.__init__(sample_rate)
        self.load_state(state)

    def process(self, audio: np.ndarray) -> np.ndarray:
        """Executa a passagem completa pelo rack de efeitos."""
        if len(audio) == 0:
            return audio

        # PortAudio mono input is (frames, 1); spatial effects need two channels.
        if audio.ndim == 2 and audio.shape[1] == 1:
            audio = np.repeat(audio, 2, axis=1)

        # 1. Ganho de Entrada
        x = audio * self.input_gain

        # 2. Gate de Ruído
        x = self.gate.process(x)

        # 3. Correção de Afinação / Autotune
        x = self.autotune.process(x)

        # 4. Equalizador Paramétrico + High Pass
        x = self.eq.process(x)

        # 5. Compressor Dinâmico
        x = self.compressor.process(x)

        # 6. Delay / Eco
        x = self.delay.process(x)

        # 7. Reverb Estéreo
        x = self.reverb.process(x)

        # 8. Ganho Master e Limiter
        x = x * self.output_gain
        out = self.limiter.process(x)

        return out

    def get_state(self) -> Dict[str, Any]:
        """Exporta o estado de todos os efeitos para salvamento de presets."""
        return {
            "input_gain": self.input_gain,
            "output_gain": self.output_gain,
            "gate": {
                "enabled": self.gate.enabled,
                "threshold_db": self.gate.threshold_db,
                "attack_ms": self.gate.attack_ms,
                "release_ms": self.gate.release_ms,
            },
            "autotune": {
                "enabled": self.autotune.enabled,
                "root_note": self.autotune.root_note,
                "scale_name": self.autotune.scale_name,
                "snap_speed": self.autotune.snap_speed,
                "amount": self.autotune.amount,
            },
            "eq": {
                "enabled": self.eq.enabled,
                "highpass_enabled": self.eq.highpass_enabled,
                "low_gain_db": self.eq.low_gain_db,
                "mid_gain_db": self.eq.mid_gain_db,
                "high_gain_db": self.eq.high_gain_db,
            },
            "compressor": {
                "enabled": self.compressor.enabled,
                "threshold_db": self.compressor.threshold_db,
                "ratio": self.compressor.ratio,
                "attack_ms": self.compressor.attack_ms,
                "release_ms": self.compressor.release_ms,
                "makeup_gain_db": self.compressor.makeup_gain_db,
            },
            "delay": {
                "enabled": self.delay.enabled,
                "delay_time_ms": self.delay.delay_time_ms,
                "feedback": self.delay.feedback,
                "damping": self.delay.damping,
                "dry_wet": self.delay.dry_wet,
            },
            "reverb": {
                "enabled": self.reverb.enabled,
                "room_size": self.reverb.room_size,
                "damping": self.reverb.damping,
                "dry_wet": self.reverb.dry_wet,
                "width": self.reverb.width,
            }
        }

    def load_state(self, state: Dict[str, Any]):
        """Aplica as configurações de um preset ao rack de efeitos."""
        if "input_gain" in state:
            self.input_gain = float(state["input_gain"])
        if "output_gain" in state:
            self.output_gain = float(state["output_gain"])

        if "gate" in state:
            g = state["gate"]
            self.gate.set_params(
                threshold_db=g.get("threshold_db"),
                attack_ms=g.get("attack_ms"),
                release_ms=g.get("release_ms"),
                enabled=g.get("enabled")
            )

        if "autotune" in state:
            a = state["autotune"]
            self.autotune.set_params(
                root=a.get("root_note"),
                scale=a.get("scale_name"),
                snap_speed=a.get("snap_speed"),
                amount=a.get("amount"),
                enabled=a.get("enabled")
            )

        if "eq" in state:
            e = state["eq"]
            self.eq.set_params(
                highpass_enabled=e.get("highpass_enabled"),
                low_db=e.get("low_gain_db"),
                mid_db=e.get("mid_gain_db"),
                high_db=e.get("high_gain_db"),
                enabled=e.get("enabled")
            )

        if "compressor" in state:
            c = state["compressor"]
            self.compressor.set_params(
                threshold_db=c.get("threshold_db"),
                ratio=c.get("ratio"),
                attack_ms=c.get("attack_ms"),
                release_ms=c.get("release_ms"),
                makeup_gain_db=c.get("makeup_gain_db"),
                enabled=c.get("enabled")
            )

        if "delay" in state:
            d = state["delay"]
            self.delay.set_params(
                delay_time_ms=d.get("delay_time_ms"),
                feedback=d.get("feedback"),
                damping=d.get("damping"),
                dry_wet=d.get("dry_wet"),
                enabled=d.get("enabled")
            )

        if "reverb" in state:
            r = state["reverb"]
            self.reverb.set_params(
                room_size=r.get("room_size"),
                damping=r.get("damping"),
                dry_wet=r.get("dry_wet"),
                width=r.get("width"),
                enabled=r.get("enabled")
            )
