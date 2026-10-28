"""Regression coverage for output startup, underruns, and clock drift."""
from types import SimpleNamespace

import numpy as np
import pytest

from app.audio.engine import AudioEngine
from app.audio.ring_buffer import AudioRingBuffer


@pytest.mark.parametrize("block", [128, 256, 512, 1024])
def test_output_prebuffers_then_plays_without_initial_underrun(block):
    buffer = AudioRingBuffer(capacity=max(4096, block * 6), channels=2)
    source = np.ones((block, 2), dtype=np.float32) * 0.25
    for _ in range(2):
        buffer.write(source)
        assert not np.any(buffer.read_for_output(block, block * 3))
    buffer.write(source)
    first = buffer.read_for_output(block, block * 3)
    assert first[0, 0] == 0
    np.testing.assert_allclose(first[-1], [0.25, 0.25], atol=1e-5)
    assert buffer.underrun_frames == 0
    buffer.write(source)
    np.testing.assert_allclose(buffer.read_for_output(block, block * 3), 0.25, atol=1e-5)


@pytest.mark.parametrize("direction", [-1, 1])
def test_independent_clocks_do_not_accumulate_dropouts(direction):
    block = 256
    buffer = AudioRingBuffer(capacity=2048, channels=2)
    sample_index = 0
    started = False
    previous = 0.0
    maximum_jump = 0.0
    # 1 sample per eight blocks is roughly 488 ppm of clock mismatch.
    for iteration in range(5000):
        count = block + (direction if iteration % 8 == 0 else 0)
        time = np.arange(sample_index, sample_index + count) / 48000
        sample_index += count
        audio = (0.4 * np.sin(2 * np.pi * 440 * time)).astype(np.float32)
        buffer.write(audio)
        out = buffer.read_for_output(block, block * 3)[:, 0]
        if buffer._output_primed:
            if started:
                maximum_jump = max(maximum_jump, abs(float(out[0]) - previous))
            started = True
            previous = float(out[-1])
    assert started
    assert buffer.underrun_frames == 0
    assert buffer.overrun_frames == 0
    assert maximum_jump < 0.08


def test_real_underrun_fades_then_rebuffers():
    block = 256
    buffer = AudioRingBuffer(capacity=2048, channels=2)
    buffer.write(np.ones((block * 3, 2), dtype=np.float32))
    buffer.read_for_output(block, block * 3)
    buffer.read_for_output(block, block * 3)
    buffer.read_for_output(block, block * 3)
    faded = buffer.read_for_output(block, block * 3)
    assert faded[-1, 0] == 0.0
    assert buffer.underrun_frames > 0
    assert not buffer._output_primed
    assert not np.any(buffer.read_for_output(block, block * 3))
    buffer.write(np.ones((block * 3, 2), dtype=np.float32))
    resumed = buffer.read_for_output(block, block * 3)
    assert resumed[0, 0] == 0
    assert resumed[-1, 0] == pytest.approx(1.0)


def test_portaudio_flags_are_recorded(monkeypatch):
    engine = AudioEngine()
    monkeypatch.setattr(engine, "_process_input", lambda *args: None)
    engine._input_callback(np.zeros((512, 1), dtype=np.float32), 512, None,
                           SimpleNamespace(input_overflow=True))
    out = np.zeros((512, 2), dtype=np.float32)
    engine._mon1_callback(out, 512, None, SimpleNamespace(output_underflow=True))
    assert engine.input_overflows == 1
    assert engine.output_underflows["mon1"] == 1
    assert engine.output_underflows["virtual"] == 0
    diagnostics = engine.get_diagnostics()
    assert diagnostics["input_overflows"] == 1
    assert diagnostics["outputs"]["mon1"]["device_underflows"] == 1


def test_live_engine_avoids_processing_inactive_outputs(monkeypatch):
    engine = AudioEngine()
    engine.is_running = True
    engine._stream_mon1 = object()
    monkeypatch.setattr(engine.fx_chain, "process", lambda x: np.full((len(x), 2), 0.25, dtype=np.float32))
    monkeypatch.setattr(engine.stem_player, "get_next_block", lambda n: np.zeros((n, 2), dtype=np.float32))
    engine._process_input(np.zeros((512, 1), dtype=np.float32), 512)
    assert engine.buf_mon1.available_read() == 512
    assert engine.buf_virtual.available_read() == 0
    assert engine.buf_mon2.available_read() == 0
