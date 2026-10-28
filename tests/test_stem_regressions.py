import numpy as np
import pytest
import soundfile as sf
from app.stems.player import StemPlayer
from app.stems.exporter import StemExporter


def song(tmp_path, rate=44100, amplitude=0.2, name="song"):
    path = tmp_path / (name + ".wav")
    t = np.arange(rate) / rate
    sf.write(path, amplitude * np.sin(2 * np.pi * 440 * t), rate, subtype="FLOAT")
    return path


@pytest.mark.parametrize("source,target", [(44100, 48000), (48000, 44100)])
def test_resampling_preserves_duration_pitch_and_export_rate(tmp_path, source, target):
    player = StemPlayer(target)
    player.load_stems({"instrumental": song(tmp_path, source)})
    assert player.get_duration_seconds() == pytest.approx(1.0, abs=1 / target)
    player.play()
    audio = player.get_next_block(target)
    peak = np.fft.rfftfreq(target, 1 / target)[np.argmax(np.abs(np.fft.rfft(audio[:, 0])))]
    assert peak == pytest.approx(440, abs=1)
    output = tmp_path / "export.wav"
    assert StemExporter.export_custom_mix(player, output)
    assert sf.info(output).samplerate == target
    assert sf.info(output).duration == pytest.approx(1.0)


def test_instrumental_and_components_do_not_double_default_mix(tmp_path):
    paths = {name: song(tmp_path, 48000, amplitude, name) for name, amplitude in
             [("instrumental", 0.3), ("vocals", 0), ("drums", 0.1), ("bass", 0.1), ("other", 0.1)]}
    player = StemPlayer()
    player.load_stems(paths)
    assert player.tracks["instrumental"].mute
    player.play()
    out = player.get_next_block(48000)
    assert np.max(out) == pytest.approx(0.3, abs=0.001)
    player.set_stem_mute("drums", True)
    player.set_stem_solo("bass", True)
    player.stop()
    player.play()
    assert np.max(player.get_next_block(512)) == pytest.approx(0.1, abs=0.001)


def test_live_rate_change_preserves_position_and_track_controls(tmp_path):
    player = StemPlayer()
    player.load_stems({"vocals": song(tmp_path)})
    player.seek_seconds(0.5)
    player.set_stem_volume("vocals", 0.25)
    player.set_stem_solo("vocals", True)
    player.set_sample_rate(44100)
    assert player.get_position_seconds() == pytest.approx(0.5)
    assert player.get_duration_seconds() == pytest.approx(1.0)
    assert player.tracks["vocals"].volume == 0.25
    assert player.tracks["vocals"].solo


def test_loop_fills_callback_without_silent_tail(tmp_path):
    path = tmp_path / "tiny.wav"
    sf.write(path, np.ones((100, 2), dtype=np.float32) * 0.1, 48000, subtype="FLOAT")
    player = StemPlayer()
    player.load_stems({"vocals": path})
    player.loop = True
    player.play()
    np.testing.assert_allclose(player.get_next_block(256), 0.1)
    assert player.playhead_frame == 56
