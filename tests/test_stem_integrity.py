"""Realistic regression checks for transport and native stem reconstruction."""
import numpy as np
import pytest
import soundfile as sf

from app.stems.player import StemPlayer
from app.stems.separator import SeparationEngine


@pytest.mark.parametrize("frames", [96, 1024, 16384])
def test_spectral_stems_reconstruct_original_and_preserve_length(tmp_path, frames):
    sr = 48000
    t = np.arange(frames) / sr
    left = 0.3 * np.sin(2 * np.pi * 440 * t) + 0.1 * np.sin(2 * np.pi * 90 * t)
    right = 0.2 * np.sin(2 * np.pi * 440 * t) - 0.1 * np.sin(2 * np.pi * 90 * t)
    source = np.column_stack([left, right]).astype(np.float32)
    path = tmp_path / f"source_{frames}.wav"
    sf.write(path, source, sr, subtype="FLOAT")
    result = SeparationEngine().separate(path)
    tracks = {key: sf.read(value, dtype="float32", always_2d=True)[0] for key, value in result.items()}
    assert all(track.shape == source.shape for track in tracks.values())
    np.testing.assert_allclose(tracks["vocals"] + tracks["instrumental"], source, atol=1e-5)
    np.testing.assert_allclose(tracks["drums"] + tracks["bass"] + tracks["other"], tracks["instrumental"], atol=1e-5)


def test_transport_restarts_after_reaching_end(tmp_path):
    sr = 48000
    audio = np.ones((300, 2), dtype=np.float32) * 0.1
    path = tmp_path / "sample.wav"
    sf.write(path, audio, sr, subtype="FLOAT")
    player = StemPlayer(sr)
    player.load_stems({"vocals": path})
    player.play()
    np.testing.assert_allclose(player.get_next_block(300), audio)
    assert not player.is_playing
    player.play()
    np.testing.assert_allclose(player.get_next_block(100), audio[:100])
    assert player.get_position_seconds() == pytest.approx(100 / sr)
