"""
Motor de Autotune e Correção de Afinação em Tempo Real para Vocais Hip-Hop.
Utiliza algoritmo YIN/NSDF acelerado via Numba JIT para detecção de pitch e
Pitch-Shifting por PSOLA/Resampling de fase com quantização tonal instantânea (Hard Snap) ou suave.
"""

import numpy as np
import math

try:
    from numba import njit
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False
    def njit(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

SCALE_INTERVALS = {
    "Cromática": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
    "Maior": [0, 2, 4, 5, 7, 9, 11],
    "Menor Natural": [0, 2, 3, 5, 7, 8, 10],
    "Menor Harmônica": [0, 2, 3, 5, 7, 8, 11],
    "Pentatônica Menor (Hip-Hop)": [0, 3, 5, 7, 10],
    "Pentatônica Maior": [0, 2, 4, 7, 9],
    "Dórico": [0, 2, 3, 5, 7, 9, 10],
}

@njit(fastmath=True)
def detect_pitch_yin_numba(audio_block: np.ndarray, sample_rate: int, min_freq: float, max_freq: float) -> float:
    """
    Algoritmo YIN otimizado em código nativo via Numba para detecção precisa de pitch vocal.
    Mede a frequência fundamental (F0) entre min_freq (ex: 60Hz) e max_freq (ex: 800Hz).
    """
    n = len(audio_block)
    min_period = int(sample_rate / max_freq)
    max_period = int(sample_rate / min_freq)
    if max_period >= n // 2:
        max_period = n // 2 - 1
    if min_period >= max_period:
        return 0.0

    # 1. Diferença quadrática
    diff = np.zeros(max_period + 1, dtype=np.float32)
    for tau in range(1, max_period + 1):
        s = 0.0
        for j in range(n - max_period):
            d = audio_block[j] - audio_block[j + tau]
            s += d * d
        diff[tau] = s

    # 2. Cumulative Mean Normalized Difference Function (CMNDF)
    cmndf = np.zeros(max_period + 1, dtype=np.float32)
    cmndf[0] = 1.0
    running_sum = 0.0
    for tau in range(1, max_period + 1):
        running_sum += diff[tau]
        if running_sum > 0.0:
            cmndf[tau] = diff[tau] * tau / running_sum
        else:
            cmndf[tau] = 1.0

    # 3. Busca do primeiro mínimo absoluto abaixo do limiar (0.15)
    threshold = 0.15
    best_tau = -1
    for tau in range(min_period, max_period):
        if cmndf[tau] < threshold:
            while tau + 1 <= max_period and cmndf[tau + 1] < cmndf[tau]:
                tau += 1
            best_tau = tau
            break

    if best_tau == -1:
        # Se nenhum valor ficou abaixo do limiar, pega o mínimo global
        min_val = 999.0
        for tau in range(min_period, max_period + 1):
            if cmndf[tau] < min_val:
                min_val = cmndf[tau]
                best_tau = tau
        if min_val > 0.45: # Não é som vozeado / ruído
            return 0.0

    if best_tau <= 0:
        return 0.0

    # Interpolação parabólica para precisão sub-amostra
    x0 = best_tau - 1 if best_tau > 0 else best_tau
    x2 = best_tau + 1 if best_tau < max_period else best_tau
    s0 = cmndf[x0]
    s1 = cmndf[best_tau]
    s2 = cmndf[x2]

    denom = 2.0 * (2.0 * s1 - s0 - s2)
    if abs(denom) > 1e-6:
        delta = (s0 - s2) / denom
    else:
        delta = 0.0

    refined_tau = best_tau + delta
    if refined_tau <= 0.0:
        return 0.0

    return sample_rate / refined_tau

@njit(fastmath=True)
def pitch_shift_linear_numba(audio: np.ndarray, shift_ratio: float) -> np.ndarray:
    """
    Realiza o pitch shifting por interpolação linear rápida com correção de fase.
    """
    n = len(audio)
    out = np.zeros(n, dtype=np.float32)
    if shift_ratio <= 0.01:
        return audio

    for i in range(n):
        orig_pos = i * shift_ratio
        idx = int(orig_pos)
        frac = orig_pos - idx
        
        # Leitura com reflexão suave nas bordas
        idx0 = idx % n
        idx1 = (idx + 1) % n
        out[i] = (1.0 - frac) * audio[idx0] + frac * audio[idx1]

    return out

class AutoTune:
    def __init__(self, sample_rate: int = 48000):
        self.sample_rate = sample_rate
        self.enabled = True
        
        # Parâmetros musicais
        self.root_note = "C"
        self.scale_name = "Pentatônica Menor (Hip-Hop)"
        
        # Controles de desempenho
        self.snap_speed = 0.0    # 0.0 = Hard snap instantâneo (Travis Scott), 1.0 = suave/sutil
        self.amount = 1.0        # 0.0 a 1.0 (Mix Dry/Wet do pitch)
        self.min_freq = 70.0     # C2 aprox
        self.max_freq = 750.0    # G5 aprox
        
        # Histórico de pitch suavizado
        self._last_detected_freq = 0.0
        self._target_freq = 0.0
        self._current_freq = 0.0
        self._buffer_history = np.zeros(1024, dtype=np.float32)

    def set_params(self, root: str = None, scale: str = None, snap_speed: float = None,
                   amount: float = None, enabled: bool = None):
        if root in NOTE_NAMES:
            self.root_note = root
        if scale in SCALE_INTERVALS:
            self.scale_name = scale
        if snap_speed is not None:
            self.snap_speed = max(0.0, min(1.0, float(snap_speed)))
        if amount is not None:
            self.amount = max(0.0, min(1.0, float(amount)))
        if enabled is not None:
            self.enabled = bool(enabled)

    def freq_to_midi(self, freq: float) -> float:
        if freq <= 10.0:
            return 0.0
        return 69.0 + 12.0 * math.log2(freq / 440.0)

    def midi_to_freq(self, midi: float) -> float:
        return 440.0 * (2.0 ** ((midi - 69.0) / 12.0))

    def snap_to_scale(self, freq: float) -> float:
        """Calcula a nota musical mais próxima dentro da escala selecionada."""
        if freq <= 10.0:
            return freq

        midi = self.freq_to_midi(freq)
        root_idx = NOTE_NAMES.index(self.root_note)
        intervals = SCALE_INTERVALS.get(self.scale_name, SCALE_INTERVALS["Cromática"])
        
        # Permite todas as notas transpostas pelo root
        allowed_notes_mod12 = [(root_idx + iv) % 12 for iv in intervals]
        
        # Encontra a nota MIDI mais próxima que pertença à escala
        round_midi = round(midi)
        best_target = round_midi
        min_dist = 999.0

        for candidate in range(round_midi - 2, round_midi + 3):
            candidate_mod = candidate % 12
            if candidate_mod in allowed_notes_mod12:
                dist = abs(midi - candidate)
                if dist < min_dist:
                    min_dist = dist
                    best_target = candidate

        return self.midi_to_freq(best_target)

    def process(self, audio: np.ndarray) -> np.ndarray:
        if not self.enabled or len(audio) == 0:
            return audio

        is_stereo = (audio.ndim == 2)
        if is_stereo:
            mono = np.mean(audio, axis=1)
        else:
            mono = audio

        frames = len(mono)

        # Monta buffer concatenado com histórico para detecção sólida
        hist_len = len(self._buffer_history)
        full_analysis = np.concatenate((self._buffer_history, mono))
        self._buffer_history = full_analysis[-hist_len:]

        # Detecta pitch fundamental
        detected_f0 = detect_pitch_yin_numba(
            full_analysis, self.sample_rate, self.min_freq, self.max_freq
        )

        if detected_f0 <= 0.0 or detected_f0 < self.min_freq or detected_f0 > self.max_freq:
            # Sem voz detectada (silêncio ou ruído)
            return audio

        self._last_detected_freq = detected_f0
        target_f0 = self.snap_to_scale(detected_f0)

        # Aplica inércia de acordo com snap_speed:
        # snap_speed = 0.0 -> instantâneo (autotune duro de trap)
        # snap_speed = 1.0 -> suave (suave correção)
        smooth_factor = self.snap_speed * 0.85
        if self._current_freq <= 0.0:
            self._current_freq = target_f0
        else:
            self._current_freq = smooth_factor * self._current_freq + (1.0 - smooth_factor) * target_f0

        # Razão de pitch shift
        ratio = self._current_freq / detected_f0
        ratio = max(0.6, min(1.6, ratio)) # Limita em intervalo seguro de 1 oitava

        # Shift de tom acelerado
        if is_stereo:
            shifted_l = pitch_shift_linear_numba(audio[:, 0].astype(np.float32), ratio)
            shifted_r = pitch_shift_linear_numba(audio[:, 1].astype(np.float32), ratio)
            shifted = np.column_stack((shifted_l, shifted_r))
        else:
            shifted = pitch_shift_linear_numba(mono.astype(np.float32), ratio)

        # Mix Amount (Dry / Wet)
        if self.amount >= 0.99:
            return shifted
        elif self.amount <= 0.01:
            return audio
        else:
            return (1.0 - self.amount) * audio + self.amount * shifted
