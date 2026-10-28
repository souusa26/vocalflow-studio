from unittest.mock import Mock
import numpy as np
import pytest
import sounddevice as sd
from app.audio.engine import AudioEngine


@pytest.fixture
def streams(monkeypatch):
    opened = []
    def create(**kwargs):
        stream = Mock(**kwargs)
        opened.append(stream)
        return stream
    monkeypatch.setattr(sd, "InputStream", create)
    monkeypatch.setattr(sd, "OutputStream", create)
    return opened


def test_output_failure_rolls_back_input_and_notifies_user(streams, monkeypatch):
    engine = AudioEngine()
    engine.virtual_device_id = 1
    engine.monitor1_enabled = False
    errors = []
    engine.on_error = errors.append
    monkeypatch.setattr(sd, "OutputStream", Mock(side_effect=RuntimeError("unplugged")))
    with pytest.raises(RuntimeError, match="unplugged"):
        engine.start()
    assert not engine.is_running
    assert errors and "unplugged" in errors[0]
    streams[0].close.assert_called_once()
    assert engine._stream_input is None


def test_start_requires_a_destination():
    with pytest.raises(RuntimeError, match="Selecione"):
        AudioEngine().start()


def test_live_reconfigure_reopens_streams_with_new_format(streams):
    engine = AudioEngine()
    engine.virtual_device_id = 1
    engine.start()
    initial = list(streams)
    engine.configure(sample_rate=44100, block_size=512)
    assert engine.is_running
    assert (engine.sample_rate, engine.block_size) == (44100, 512)
    assert engine._stream_input.samplerate == 44100
    assert engine._stream_input.blocksize == 512
    assert engine.buf_virtual.capacity == 2048
    for old in initial:
        old.close.assert_called_once()
    engine.stop()


def test_output_buffers_bound_audio_backlog_for_large_blocks():
    engine = AudioEngine(block_size=1024)
    assert engine.buf_virtual.capacity == 4096
    engine.configure(block_size=256)
    assert engine.buf_virtual.capacity == 2048


def test_restart_after_callback_abort_closes_old_streams(streams, monkeypatch):
    engine = AudioEngine()
    engine.virtual_device_id = 1
    engine.start()
    old_streams = list(streams)
    monkeypatch.setattr(engine.fx_chain, "process", Mock(side_effect=ValueError("DSP failed")))
    with pytest.raises(sd.CallbackAbort):
        engine._input_callback(np.zeros((256, 1)), 256, None, None)
    engine.start()
    assert engine.is_running
    for old in old_streams:
        old.close.assert_called_once()
    engine.stop()


def test_monitor_volume_does_not_restart_devices(streams):
    engine = AudioEngine()
    engine.monitor1_device_id = 1
    engine.start()
    engine.set_monitor1(True, volume=0.5)
    assert len(streams) == 2
    engine.stop()


def test_final_mix_and_monitor_gain_are_limited(monkeypatch):
    engine = AudioEngine()
    engine.monitor2_enabled = True
    engine.monitor1_volume = engine.monitor2_volume = 1.5
    engine.stem_player.send_to_virtual_mic = True
    monkeypatch.setattr(engine.fx_chain, "process", lambda audio: np.full((len(audio), 2), 0.8, dtype=np.float32))
    monkeypatch.setattr(engine.stem_player, "get_next_block", lambda count: np.full((count, 2), 0.8, dtype=np.float32))
    engine._input_callback(np.zeros((256, 1), dtype=np.float32), 256, None, None)
    for buffer in (engine.buf_virtual, engine.buf_mon1, engine.buf_mon2):
        out = buffer.read(256)
        assert np.max(np.abs(out)) <= 10 ** (-0.3 / 20) + 1e-6
        assert np.max(out) > 0.9


def test_microphone_callback_runs_complete_default_chain():
    engine = AudioEngine()
    audio = np.zeros((256, 1), dtype=np.float32)
    engine._input_callback(audio, 256, None, None)
    assert engine.buf_virtual.read(256).shape == (256, 2)
    assert engine.last_error is None


def test_processing_failure_stops_callback_and_records_error(monkeypatch):
    engine = AudioEngine()
    engine.is_running = True
    monkeypatch.setattr(engine.fx_chain, "process", Mock(side_effect=ValueError("DSP failed")))
    with pytest.raises(sd.CallbackAbort):
        engine._input_callback(np.zeros((256, 1)), 256, None, None)
    assert not engine.is_running
    assert "DSP failed" in engine.last_error
