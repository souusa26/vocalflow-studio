"""Delay and reverb tails must survive different audio callback boundaries."""
import numpy as np
import pytest

from app.audio.dsp.delay import Delay
from app.audio.dsp.reverb import Reverb


@pytest.mark.parametrize("effect", [Delay, Reverb])
@pytest.mark.parametrize("channels", [1, 2])
def test_effect_output_does_not_depend_on_callback_boundaries(effect, channels):
    signal = np.random.default_rng(413).normal(0, 0.2, (8192, channels)).astype(np.float32)
    if channels == 1:
        signal = signal[:, 0]
    whole, streaming = effect(), effect()
    whole.set_params(enabled=True)
    streaming.set_params(enabled=True)
    # Warm-up must never consume samples or disturb filter memory.
    streaming.warm_up()
    reference = whole.process(signal)
    output = np.concatenate([streaming.process(signal[i:i + 257])
                             for i in range(0, len(signal), 257)])
    np.testing.assert_allclose(output, reference, rtol=1e-5, atol=1e-6)


@pytest.mark.parametrize("effect", [Delay, Reverb])
def test_reverb_and_delay_continue_echo_tail_after_input_goes_silent(effect):
    processor = effect(sample_rate=48000)
    processor.set_params(enabled=True, dry_wet=0.5)
    processor.warm_up()
    impulse = np.zeros((20000, 2), dtype=np.float32)
    impulse[0] = 0.8
    output = np.concatenate([processor.process(impulse[i:i + 256])
                             for i in range(0, len(impulse), 256)])
    assert np.isfinite(output).all()
    assert np.max(np.abs(output[500:])) > 0.001
