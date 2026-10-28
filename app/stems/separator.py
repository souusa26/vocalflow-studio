"""
Motor de Separação de Músicas e Extração de Stems (Voz, Bateria, Baixo e Instrumental).
Processamento 100% local e offline com arquitetura dupla:
1. Motor Nativo Espectral Rápido (Zero Download, processa em segundos com NumPy/SciPy).
2. Motor de IA Neural Demucs (Meta AI, modelo htdemucs de 4 faixas de alta fidelidade).
"""

import os
import sys
import time
import shutil
from pathlib import Path
from typing import Dict, Optional, Callable
import numpy as np
import scipy.signal
import scipy.ndimage
import soundfile as sf

from app.config import get_stems_dir, get_models_dir

DEMUCS_MODEL_NAME = "htdemucs"
DEMUCS_APPROX_SIZE_MB = 80

class SeparationEngine:
    def __init__(self):
        self.is_cancelled = False

    def cancel(self):
        """Sinaliza para cancelar o processamento imediatamente."""
        self.is_cancelled = True

    def is_demucs_available(self) -> bool:
        """Verifica se a biblioteca Demucs e PyTorch estão instaladas no ambiente."""
        if getattr(sys, "frozen", False):
            return False
        try:
            import demucs
            import torch
            return True
        except ImportError:
            return False

    def separate(
        self,
        audio_file_path: Path,
        use_ai_model: bool = False,
        progress_cb: Optional[Callable[[int, str], None]] = None
    ) -> Dict[str, Path]:
        """
        Separa o arquivo de áudio nas faixas correspondentes:
        'vocals', 'instrumental', 'drums', 'bass', 'other'.
        Retorna dicionário com os caminhos dos arquivos WAV gerados.
        """
        self.is_cancelled = False
        audio_path = Path(audio_file_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Arquivo de áudio não encontrado: {audio_path}")

        song_slug = "".join(c for c in audio_path.stem if c.isalnum() or c in ("-", "_")).strip() or "track"
        output_folder = get_stems_dir() / song_slug
        output_folder.mkdir(parents=True, exist_ok=True)

        if use_ai_model and self.is_demucs_available():
            return self._separate_demucs(audio_path, output_folder, progress_cb)
        else:
            return self._separate_native_spectral(audio_path, output_folder, progress_cb)

    def _separate_native_spectral(
        self,
        audio_path: Path,
        output_folder: Path,
        progress_cb: Optional[Callable[[int, str], None]]
    ) -> Dict[str, Path]:
        """
        Motor espectral nativo via STFT e Decomposição Harmônica-Percussiva (HPSS)
        com cancelamento de centro estéreo.
        Funciona instantaneamente em qualquer máquina sem downloads pesados.
        """
        if progress_cb:
            progress_cb(5, "Carregando arquivo de áudio...")

        data, sr = sf.read(str(audio_path), dtype="float32")
        if self.is_cancelled:
            raise InterruptedError("Operação cancelada pelo usuário.")

        # Garante estéreo
        if data.ndim == 1:
            data = np.column_stack((data, data))
        elif data.shape[1] > 2:
            data = data[:, :2]

        total_samples = len(data)

        if progress_cb:
            progress_cb(15, "Analisando espectrograma e frequências...")

        # STFT em blocos
        n_fft = 2048
        hop_length = 512

        _, _, Zxx_left = scipy.signal.stft(data[:, 0], fs=sr, nperseg=n_fft, noverlap=n_fft - hop_length)
        _, _, Zxx_right = scipy.signal.stft(data[:, 1], fs=sr, nperseg=n_fft, noverlap=n_fft - hop_length)

        if self.is_cancelled:
            raise InterruptedError("Operação cancelada pelo usuário.")

        if progress_cb:
            progress_cb(35, "Separando componentes estéreo e vocais centrais...")

        # 1. Extração do canal central (Vocal principal costuma estar mixado no centro)
        mag_l = np.abs(Zxx_left)
        mag_r = np.abs(Zxx_right)
        phase_l = np.angle(Zxx_left)
        phase_r = np.angle(Zxx_right)

        # Máscara de correlação central
        min_mag = np.minimum(mag_l, mag_r)
        max_mag = np.maximum(mag_l, mag_r) + 1e-6
        center_mask = min_mag / max_mag

        # Filtro de frequências típico da voz humana (150 Hz a 6 kHz)
        freqs = scipy.signal.stft(data[:n_fft, 0], fs=sr, nperseg=n_fft)[0]
        vocal_freq_mask = ((freqs >= 150) & (freqs <= 6500))[:, np.newaxis]
        
        vocal_mask = (center_mask ** 1.8) * vocal_freq_mask

        # Espectrograma dos Vocais
        vocal_stft_l = Zxx_left * vocal_mask
        vocal_stft_r = Zxx_right * vocal_mask

        # Espectrograma do Instrumental (mix original menos o centro vocal)
        inst_mask = np.clip(1.0 - (vocal_mask * 0.95), 0.05, 1.0)
        inst_stft_l = Zxx_left * inst_mask
        inst_stft_r = Zxx_right * inst_mask

        if self.is_cancelled:
            raise InterruptedError("Operação cancelada pelo usuário.")

        if progress_cb:
            progress_cb(55, "Decompondo Bateria (Percussão) e Baixo (Sub-graves)...")

        # 2. Decomposição de Baixo (< 200 Hz do instrumental)
        bass_freq_mask = (freqs <= 220)[:, np.newaxis]
        bass_stft_l = inst_stft_l * bass_freq_mask
        bass_stft_r = inst_stft_r * bass_freq_mask

        # 3. Componente de Bateria / Percussão (Transitórios rápidos no restante do instrumental)
        inst_mid_high = inst_stft_l * (~bass_freq_mask)
        # Filtro de mediana ao longo do tempo captura transitórios de bateria
        mag_mid = np.abs(inst_mid_high)
        percussive_weight = np.clip(mag_mid / (scipy.ndimage.median_filter(mag_mid, size=(1, 15)) + 1e-5), 0.0, 2.0)
        drum_mask = (percussive_weight > 1.25).astype(np.float32)

        drum_stft_l = inst_mid_high * drum_mask
        drum_stft_r = (inst_stft_r * (~bass_freq_mask)) * drum_mask

        # 4. Outros instrumentos (sintetizadores, guitarras, teclados, pads)
        other_stft_l = inst_stft_l - bass_stft_l - (drum_stft_l * 0.7)
        other_stft_r = inst_stft_r - bass_stft_r - (drum_stft_r * 0.7)

        if self.is_cancelled:
            raise InterruptedError("Operação cancelada pelo usuário.")

        if progress_cb:
            progress_cb(75, "Reconstruindo faixas de áudio no domínio do tempo...")

        # Reconstrução via ISTFT
        n_overlap = n_fft - hop_length
        _, voc_l = scipy.signal.istft(vocal_stft_l, fs=sr, nperseg=n_fft, noverlap=n_overlap)
        _, voc_r = scipy.signal.istft(vocal_stft_r, fs=sr, nperseg=n_fft, noverlap=n_overlap)
        vocals = np.column_stack((voc_l[:total_samples], voc_r[:total_samples]))

        _, ins_l = scipy.signal.istft(inst_stft_l, fs=sr, nperseg=n_fft, noverlap=n_overlap)
        _, ins_r = scipy.signal.istft(inst_stft_r, fs=sr, nperseg=n_fft, noverlap=n_overlap)
        instrumental = np.column_stack((ins_l[:total_samples], ins_r[:total_samples]))

        _, drm_l = scipy.signal.istft(drum_stft_l, fs=sr, nperseg=n_fft, noverlap=n_overlap)
        _, drm_r = scipy.signal.istft(drum_stft_r, fs=sr, nperseg=n_fft, noverlap=n_overlap)
        drums = np.column_stack((drm_l[:total_samples], drm_r[:total_samples]))

        _, bas_l = scipy.signal.istft(bass_stft_l, fs=sr, nperseg=n_fft, noverlap=n_overlap)
        _, bas_r = scipy.signal.istft(bass_stft_r, fs=sr, nperseg=n_fft, noverlap=n_overlap)
        bass = np.column_stack((bas_l[:total_samples], bas_r[:total_samples]))

        _, oth_l = scipy.signal.istft(other_stft_l, fs=sr, nperseg=n_fft, noverlap=n_overlap)
        _, oth_r = scipy.signal.istft(other_stft_r, fs=sr, nperseg=n_fft, noverlap=n_overlap)
        other = np.column_stack((oth_l[:total_samples], oth_r[:total_samples]))

        if self.is_cancelled:
            raise InterruptedError("Operação cancelada pelo usuário.")

        if progress_cb:
            progress_cb(90, "Salvando arquivos WAV de alta fidelidade...")

        paths = {
            "vocals": output_folder / "vocals.wav",
            "instrumental": output_folder / "instrumental.wav",
            "drums": output_folder / "drums.wav",
            "bass": output_folder / "bass.wav",
            "other": output_folder / "other.wav",
        }

        sf.write(str(paths["vocals"]), vocals, sr)
        sf.write(str(paths["instrumental"]), instrumental, sr)
        sf.write(str(paths["drums"]), drums, sr)
        sf.write(str(paths["bass"]), bass, sr)
        sf.write(str(paths["other"]), other, sr)

        if progress_cb:
            progress_cb(100, "Separação de Stems concluída com sucesso!")

        return paths

    def _separate_demucs(
        self,
        audio_path: Path,
        output_folder: Path,
        progress_cb: Optional[Callable[[int, str], None]]
    ) -> Dict[str, Path]:
        """
        Execução do modelo Demucs com divisão em 4 stems independentes.
        """
        if progress_cb:
            progress_cb(10, "Inicializando motor neural Demucs...")

        try:
            import torch
            import demucs.separate
            
            # Demucs CLI em subprocess ou API
            cmd = [
                sys.executable, "-m", "demucs.separate",
                "-n", DEMUCS_MODEL_NAME,
                "-o", str(output_folder.parent),
                str(audio_path)
            ]
            
            if progress_cb:
                progress_cb(30, "Processando tensores neurais (separação profunda)...")

            import subprocess
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)
            
            while proc.poll() is None:
                if self.is_cancelled:
                    proc.kill()
                    proc.wait()
                    raise InterruptedError("Operação cancelada pelo usuário.")
                time.sleep(0.5)

            if proc.returncode != 0:
                raise RuntimeError(f"Demucs encerrou com código {proc.returncode}.")

            # Localiza os stems gerados
            demucs_stem_dir = output_folder.parent / DEMUCS_MODEL_NAME / audio_path.stem
            paths = {
                "vocals": demucs_stem_dir / "vocals.wav",
                "drums": demucs_stem_dir / "drums.wav",
                "bass": demucs_stem_dir / "bass.wav",
                "other": demucs_stem_dir / "other.wav",
            }
            
            # Gera também o instrumental combinado
            inst_path = demucs_stem_dir / "instrumental.wav"
            if not inst_path.exists() and paths["drums"].exists():
                d, sr = sf.read(str(paths["drums"]))
                b, _ = sf.read(str(paths["bass"]))
                o, _ = sf.read(str(paths["other"]))
                inst = d + b + o
                sf.write(str(inst_path), inst, sr)
            paths["instrumental"] = inst_path

            if progress_cb:
                progress_cb(100, "Separação neural Demucs concluída!")
            return paths

        except InterruptedError:
            raise
        except Exception as e:
            if progress_cb:
                progress_cb(20, "Modelo neural Demucs não disponível. Usando motor nativo espectral...")
            return self._separate_native_spectral(audio_path, output_folder, progress_cb)
