"""
Testes unitários automatizados para o motor DSP e algoritmos de processamento de áudio.
"""

import pytest
import numpy as np
from app.audio.dsp.noise_gate import NoiseGate
from app.audio.dsp.autotune import AutoTune, NOTE_NAMES, SCALE_INTERVALS
from app.audio.dsp.eq import Equalizer
from app.audio.dsp.compressor import Compressor
from app.audio.dsp.delay import Delay
from app.audio.dsp.reverb import Reverb
from app.audio.dsp.limiter import LimiterAndMeter
from app.audio.dsp.chain import VocalFXChain

def generate_sine_wave(freq: float, duration_sec: float, sample_rate: int = 48000) -> np.ndarray:
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    return 0.5 * np.sin(2.0 * np.pi * freq * t).astype(np.float32)

def test_noise_gate_attenuation():
    gate = NoiseGate(sample_rate=48000)
    gate.set_params(threshold_db=-30.0, reduction_db=-60.0, enabled=True)
    
    # Sinal muito baixo (abaixo de -30dB, ex: amplitude 0.001 = aprox -60dB)
    quiet_signal = np.full(1000, 0.001, dtype=np.float32)
    processed = gate.process(quiet_signal)
    
    # O sinal processado deve ser substancialmente menor que a entrada
    assert np.max(np.abs(processed)) < np.max(np.abs(quiet_signal))

def test_autotune_quantization():
    tune = AutoTune(sample_rate=48000)
    tune.set_params(root="C", scale="Pentatônica Menor (Hip-Hop)", snap_speed=0.0, amount=1.0)
    
    # Frequência de 440 Hz (Nota A4)
    # Na escala C Pentatônica Menor: C, Eb, F, G, Bb (MIDI: 60, 63, 65, 67, 70)
    # A4 (MIDI 69) deve quantizar para Bb4 (MIDI 70) ou G4 (MIDI 67)
    target = tune.snap_to_scale(440.0)
    midi_target = round(tune.freq_to_midi(target))
    assert midi_target in [67, 70]

def test_autotune_processing():
    tune = AutoTune(sample_rate=48000)
    tune.set_params(root="C", scale="Maior", snap_speed=0.0, amount=1.0)
    audio = generate_sine_wave(220.0, 0.1, 48000)
    out = tune.process(audio)
    assert len(out) == len(audio)
    assert not np.isnan(out).any()

def test_equalizer_frequency_response():
    eq = Equalizer(sample_rate=48000)
    # Corte agressivo de agudos e boost de graves
    eq.set_params(low_db=6.0, mid_db=0.0, high_db=-12.0, highpass_enabled=False, enabled=True)
    
    low_sine = generate_sine_wave(120.0, 0.1, 48000)
    high_sine = generate_sine_wave(10000.0, 0.1, 48000)
    
    out_low = eq.process(low_sine)[-1000:]
    out_high = eq.process(high_sine)[-1000:]
    
    # O ganho de baixa em regime estacionário deve ser substancialmente maior que o de alta
    assert np.max(np.abs(out_low)) > np.max(np.abs(out_high)) * 2.0

def test_compressor_dynamics():
    comp = Compressor(sample_rate=48000)
    comp.set_params(threshold_db=-20.0, ratio=8.0, makeup_gain_db=0.0, enabled=True)
    
    # Sinal alto com pico de 0.9 (aprox -1 dBFS)
    loud_sine = generate_sine_wave(440.0, 0.1, 48000) * 1.8
    out = comp.process(loud_sine)
    
    # A amplitude máxima após a compressão deve ser reduzida
    assert np.max(np.abs(out)) < np.max(np.abs(loud_sine))
    assert comp.get_gain_reduction_db() > 0.0

def test_delay_repetitions():
    delay = Delay(sample_rate=48000)
    delay.set_params(delay_time_ms=50.0, feedback=0.5, dry_wet=0.5, enabled=True)
    
    # Pulso curto seguido de silêncio
    impulse = np.zeros(4800, dtype=np.float32)
    impulse[0] = 1.0
    out = delay.process(impulse)
    
    delay_sample_idx = int(48000 * 0.05)
    # Deve existir repetição em torno da amostra de atraso
    assert np.max(np.abs(out[delay_sample_idx - 5:delay_sample_idx + 5])) > 0.1

def test_reverb_diffusion():
    rev = Reverb(sample_rate=48000)
    rev.set_params(room_size=0.7, damping=0.2, dry_wet=0.4, enabled=True)
    
    impulse = np.zeros(2000, dtype=np.float32)
    impulse[0] = 0.8
    out = rev.process(impulse)
    
    # A energia do reverb deve se dispersar ao longo do tempo
    assert np.sum(np.abs(out[500:])) > 0.01

def test_limiter_brickwall():
    limiter = LimiterAndMeter(sample_rate=48000)
    # Sinal com volume extremo (estouro de +12 dB)
    extreme_signal = np.full(512, 4.0, dtype=np.float32)
    out = limiter.process(extreme_signal)
    
    # O teto do limiter (-0.3dBFS aprox 0.96) deve ser respeitado
    assert np.max(np.abs(out)) <= 1.0

def test_vocal_chain_pipeline():
    chain = VocalFXChain(sample_rate=48000)
    sine = generate_sine_wave(440.0, 0.05, 48000)
    processed = chain.process(sine)
    assert len(processed) == len(sine)
    assert not np.isnan(processed).any()
    
    # Exporta e carrega estado
    state = chain.get_state()
    assert "autotune" in state
    assert "compressor" in state
    chain.load_state(state)
