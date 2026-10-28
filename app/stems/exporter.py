"""
Exportador de Stems e Mixagens Customizadas.
Exporta faixas isoladas (Acapella, Instrumental, Bateria, etc.) ou o mix atual do usuário.
"""

from pathlib import Path
from typing import Dict, Optional
import numpy as np
import soundfile as sf
from app.stems.player import StemPlayer

class StemExporter:
    @staticmethod
    def export_stem(player: StemPlayer, stem_name: str, target_path: Path) -> bool:
        """Exporta uma única faixa de stem para WAV."""
        with player.lock:
            if stem_name not in player.tracks:
                return False
            track = player.tracks[stem_name]
            data = track.data
            sr = track.sample_rate

        try:
            target_path = Path(target_path)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            sf.write(str(target_path), data, sr)
            return True
        except Exception as e:
            print(f"[Exporter] Falha ao exportar {stem_name}: {e}")
            return False

    @staticmethod
    def export_custom_mix(player: StemPlayer, target_path: Path) -> bool:
        """Exporta o mix atual (com os volumes, mutes e solos ativos) do início ao fim."""
        with player.lock:
            if not player.tracks:
                return False
            
            total_len = player.total_frames
            sr = player.target_sample_rate
            mixed = np.zeros((total_len, 2), dtype=np.float32)

            any_solo = any(t.solo for t in player.tracks.values())

            for stem_name, track in player.tracks.items():
                if any_solo and not track.solo:
                    continue
                if track.mute or track.volume <= 0.001:
                    continue
                t_len = len(track.data)
                mixed[:t_len] += track.data[:total_len] * track.volume

        # Limiter suave para evitar clipping na exportação
        peak = np.max(np.abs(mixed))
        if peak > 0.99:
            mixed = mixed * (0.98 / peak)

        try:
            target_path = Path(target_path)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            sf.write(str(target_path), mixed, sr)
            return True
        except Exception as e:
            print(f"[Exporter] Falha ao exportar mix: {e}")
            return False
