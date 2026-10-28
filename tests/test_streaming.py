import numpy as np
import pytest
from app.audio.dsp.autotune import AutoTune
from app.audio.dsp.pitch_shift import StreamingPitchShifter
from app.audio.dsp.chain import VocalFXChain
from app.audio.dsp.limiter import LimiterAndMeter
from app.audio.ring_buffer import AudioRingBuffer


@pytest.mark.parametrize("channels", [1, 2])
@pytest.mark.parametrize("block", [128, 256, 512])
def test_microphone_callback_shape(channels, block):
    chain = VocalFXChain()
    chain.delay.enabled = chain.reverb.enabled = True
    audio = np.full((block, channels), 0.1, dtype=np.float32)
    out = chain.process(audio)
    assert out.shape == (block, 2)
    assert np.isfinite(out).all()


@pytest.mark.parametrize("rate,frequency,block", [(48000, 220, 256), (44100, 220, 128),
                                                 (48000, 280, 512), (48000, 100, 256)])
def test_autotune_changes_continuous_audio_to_target_note(rate, frequency, block):
    t = np.arange(2 * rate) / rate
    audio = (0.5 * np.sin(2 * np.pi * frequency * t)).astype(np.float32)
    tune = AutoTune(rate)
    output = np.concatenate([tune.process(audio[i:i + block]) for i in range(0, len(audio), block)])
    steady = output[rate:]
    spectrum = np.abs(np.fft.rfft(steady * np.hanning(len(steady))))
    dominant = np.fft.rfftfreq(len(steady), 1 / rate)[np.argmax(spectrum)]
    assert dominant == pytest.approx(tune.snap_to_scale(frequency), abs=1.0)
    assert np.sqrt(np.mean(steady ** 2)) > 0.1


def test_pitch_shift_is_independent_of_callback_boundaries():
    audio = np.random.default_rng(7).normal(0, 0.1, (8192, 2)).astype(np.float32)
    outputs = []
    for block in (128, 256, 512):
        shifter = StreamingPitchShifter()
        outputs.append(np.concatenate([shifter.process(audio[i:i + block], 1.059)
                                       for i in range(0, len(audio), block)]))
    np.testing.assert_allclose(outputs[0], outputs[1], atol=1e-6)
    np.testing.assert_allclose(outputs[0], outputs[2], atol=1e-6)


@pytest.mark.parametrize("frequency", [100, 220, 440])
def test_autotune_vibrato_has_no_callback_boundary_clicks(frequency):
    rate, block = 48000, 256
    t = np.arange(2 * rate) / rate
    # ±2 Hz vibrato crosses the period-count threshold repeatedly; an abrupt
    # grain-window resize used to produce loud discontinuities at block edges.
    audio = (0.3 * np.sin(2 * np.pi *
             (frequency * t + (2 / 5) * np.sin(2 * np.pi * 5 * t)))).astype(np.float32)
    tune = AutoTune(rate)
    tune.warm_up()
    out = np.concatenate([tune.process(audio[i:i + block])
                          for i in range(0, len(audio), block)])
    edges = np.abs(np.diff(out))[np.arange(block - 1, len(out) - 1, block)]
    assert np.max(edges) < 2 * 0.3 * 2 * np.pi * frequency / rate + 0.015


def test_autotune_zero_amount_is_exact_bypass():
    tune = AutoTune()
    tune.amount = 0
    audio = np.random.default_rng(1).normal(size=(512, 1)).astype(np.float32)
    np.testing.assert_array_equal(tune.process(audio), audio)


def test_rate_change_preserves_effect_settings_and_rebuilds_delay():
    chain = VocalFXChain()
    chain.reverb.set_params(enabled=True, room_size=0.9, dry_wet=0.8)
    chain.delay.set_params(enabled=True, delay_time_ms=900)
    before = chain.get_state()
    chain.set_sample_rate(44100)
    assert chain.get_state() == before
    assert chain.delay.max_frames == 88200


def test_limiter_preserves_quiet_signal_and_reports_overload():
    limiter = LimiterAndMeter()
    audio = np.full((512, 2), 0.1, dtype=np.float32)
    np.testing.assert_allclose(limiter.process(audio), audio)
    assert np.max(limiter.process(audio * 20)) <= 10 ** (-0.3 / 20) + 1e-6
    assert limiter.clipped


def test_full_ring_buffer_is_readable():
    buffer = AudioRingBuffer(capacity=512)
    audio = np.arange(512, dtype=np.float32)
    buffer.write(audio)
    assert buffer.available_read() == 512
    np.testing.assert_array_equal(buffer.read(512)[:, 0], audio)


@pytest.mark.parametrize("chunks", [[400, 200], [1200], [300, 300, 300]])
def test_ring_overflow_retains_newest_frames_in_order(chunks):
    buffer = AudioRingBuffer(capacity=512)
    total = sum(chunks)
    audio = np.arange(total, dtype=np.float32)
    offset = 0
    for size in chunks:
        buffer.write(audio[offset:offset + size])
        offset += size
    assert buffer.available_read() == 512
    assert buffer.overrun_frames == total - 512
    np.testing.assert_array_equal(buffer.read(512)[:, 0], audio[-512:])
