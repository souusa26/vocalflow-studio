"""The hot-path kernels must preserve sample state across audio callbacks."""
import numpy as np
import pytest
from app.audio.dsp.chain import VocalFXChain
from app.audio.dsp.noise_gate import NoiseGate
from app.audio.dsp.compressor import Compressor
from app.audio.dsp.limiter import LimiterAndMeter


@pytest.mark.parametrize("effect_class", [NoiseGate, Compressor, LimiterAndMeter])
@pytest.mark.parametrize("channels", [1, 2])
def test_effect_output_is_invariant_to_callback_block_size(effect_class, channels):
    rng = np.random.default_rng(19)
    audio = rng.normal(0, 0.4, (3000, channels)).astype(np.float32)
    audio[800:1200] = 0
    if channels == 1:
        audio = audio[:, 0]
    whole = effect_class().process(audio)
    streaming = effect_class()
    blocks = np.concatenate([streaming.process(audio[start:start+127])
                             for start in range(0, len(audio), 127)])
    np.testing.assert_allclose(blocks, whole, atol=1e-6, rtol=1e-6)


def test_chain_warmup_does_not_change_effect_state_or_results():
    warmed = VocalFXChain()
    reference = VocalFXChain()
    for chain in (warmed, reference):
        chain.delay.enabled = True
        chain.reverb.enabled = True
    warmed.warm_up()
    assert warmed.get_state() == reference.get_state()
    audio = np.random.default_rng(31).normal(0, 0.1, (2048, 2)).astype(np.float32)
    np.testing.assert_allclose(warmed.process(audio), reference.process(audio),
                               atol=1e-6, rtol=1e-6)
