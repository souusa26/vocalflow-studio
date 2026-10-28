"""
Gerenciamento e Descoberta de Dispositivos de Áudio (WASAPI / PortAudio).
Detecção de Cabos Virtuais (VB-Audio Cable / VoiceMeeter) e classificação de periféricos.
"""

from typing import List, Dict, Optional, Tuple
import sounddevice as sd

VIRTUAL_CABLE_KEYWORDS = [
    "cable input", "cable output", "vb-audio", "voicemeeter",
    "virtual audio", "virtual cable", "stereo mix", "mixagem estéreo"
]

SPEAKER_KEYWORDS = [
    "alto-falante", "speakers", "caixa de som", "realtek audio",
    "loudspeaker", "built-in output"
]

def get_audio_devices() -> Tuple[List[Dict], List[Dict]]:
    """
    Lista todos os dispositivos de entrada e saída disponíveis no sistema.
    Retorna (inputs, outputs).
    """
    inputs = []
    outputs = []
    
    try:
        devices = sd.query_devices()
        hostapis = sd.query_hostapis()
    except Exception as e:
        print(f"[Devices] Falha ao consultar sounddevice: {e}")
        return [], []

    for idx, dev in enumerate(devices):
        hostapi_name = hostapis[dev["hostapi"]]["name"] if dev["hostapi"] < len(hostapis) else "Unknown"
        name = dev["name"]
        
        info = {
            "id": idx,
            "name": name,
            "hostapi": hostapi_name,
            "max_input_channels": dev["max_input_channels"],
            "max_output_channels": dev["max_output_channels"],
            "default_samplerate": dev["default_samplerate"],
            "is_virtual": is_virtual_cable_name(name),
            "is_speaker": is_speaker_name(name),
        }

        if dev["max_input_channels"] > 0:
            inputs.append(info)
        if dev["max_output_channels"] > 0:
            outputs.append(info)

    return inputs, outputs

def is_virtual_cable_name(name: str) -> bool:
    """Verifica se o nome do dispositivo corresponde a um cabo de áudio virtual."""
    name_lower = name.lower()
    return any(keyword in name_lower for keyword in VIRTUAL_CABLE_KEYWORDS)

def is_speaker_name(name: str) -> bool:
    """Verifica se o dispositivo parece ser uma caixa de som (para alerta de microfonia)."""
    name_lower = name.lower()
    return any(keyword in name_lower for keyword in SPEAKER_KEYWORDS)

def find_virtual_cable_output() -> Optional[Dict]:
    """
    Localiza automaticamente a melhor saída para o cabo virtual
    (Ex: 'CABLE Input (VB-Audio Virtual Cable)' no Windows).
    """
    _, outputs = get_audio_devices()
    for dev in outputs:
        name_lower = dev["name"].lower()
        if "cable input" in name_lower or ("vb-audio" in name_lower and "cable" in name_lower):
            return dev
    for dev in outputs:
        if dev["is_virtual"]:
            return dev
    return None

def find_default_input() -> Optional[Dict]:
    """Retorna o microfone padrão do sistema."""
    try:
        default_idx = sd.default.device[0]
        if default_idx is not None and default_idx >= 0:
            dev = sd.query_devices(default_idx)
            return {"id": default_idx, "name": dev["name"], "max_input_channels": dev["max_input_channels"]}
    except Exception:
        pass
    inputs, _ = get_audio_devices()
    return inputs[0] if inputs else None

def find_default_output() -> Optional[Dict]:
    """Retorna a saída padrão física do sistema."""
    try:
        default_idx = sd.default.device[1]
        if default_idx is not None and default_idx >= 0:
            dev = sd.query_devices(default_idx)
            return {"id": default_idx, "name": dev["name"], "max_output_channels": dev["max_output_channels"]}
    except Exception:
        pass
    _, outputs = get_audio_devices()
    return outputs[0] if outputs else None
