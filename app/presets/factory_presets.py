"""
Presets de Fábrica Integrados do VocalFlow Studio.
Configurações afinadas para vozes de Hip-Hop, Trap, R&B e Gravação de Estúdio.
"""

FACTORY_PRESETS = {
    "Voz Limpa (Studio Vocal)": {
        "description": "Vocal natural com alta clareza, corte de ruídos graves e compressão transparente.",
        "input_gain": 1.0,
        "output_gain": 1.0,
        "gate": {"enabled": True, "threshold_db": -50.0, "attack_ms": 2.0, "release_ms": 80.0},
        "autotune": {"enabled": False, "root_note": "C", "scale_name": "Cromática", "snap_speed": 0.5, "amount": 0.0},
        "eq": {"enabled": True, "highpass_enabled": True, "low_gain_db": -1.0, "mid_gain_db": 1.5, "high_gain_db": 2.5},
        "compressor": {"enabled": True, "threshold_db": -16.0, "ratio": 3.0, "attack_ms": 20.0, "release_ms": 100.0, "makeup_gain_db": 3.0},
        "delay": {"enabled": False, "delay_time_ms": 250.0, "feedback": 0.3, "damping": 0.4, "dry_wet": 0.15},
        "reverb": {"enabled": True, "room_size": 0.4, "damping": 0.3, "dry_wet": 0.15, "width": 1.0}
    },

    "Rap Suave (Warm Rap)": {
        "description": "Som encorpado e aveludado para versos de rap melódico ou boombap.",
        "input_gain": 1.0,
        "output_gain": 1.0,
        "gate": {"enabled": True, "threshold_db": -45.0, "attack_ms": 1.5, "release_ms": 70.0},
        "autotune": {"enabled": True, "root_note": "A", "scale_name": "Menor Natural", "snap_speed": 0.4, "amount": 0.45},
        "eq": {"enabled": True, "highpass_enabled": True, "low_gain_db": 2.0, "mid_gain_db": 2.0, "high_gain_db": 1.5},
        "compressor": {"enabled": True, "threshold_db": -18.0, "ratio": 4.0, "attack_ms": 12.0, "release_ms": 90.0, "makeup_gain_db": 4.5},
        "delay": {"enabled": True, "delay_time_ms": 200.0, "feedback": 0.25, "damping": 0.5, "dry_wet": 0.18},
        "reverb": {"enabled": True, "room_size": 0.5, "damping": 0.4, "dry_wet": 0.20, "width": 0.8}
    },

    "Trap Autotune (Travis Style)": {
        "description": "Autotune agressivo com snap instantâneo, presença agudo cortante e ambiência moderna de Trap.",
        "input_gain": 1.05,
        "output_gain": 1.0,
        "gate": {"enabled": True, "threshold_db": -40.0, "attack_ms": 1.0, "release_ms": 60.0},
        "autotune": {"enabled": True, "root_note": "C", "scale_name": "Pentatônica Menor (Hip-Hop)", "snap_speed": 0.0, "amount": 1.0},
        "eq": {"enabled": True, "highpass_enabled": True, "low_gain_db": 0.0, "mid_gain_db": 3.0, "high_gain_db": 5.0},
        "compressor": {"enabled": True, "threshold_db": -22.0, "ratio": 6.0, "attack_ms": 5.0, "release_ms": 80.0, "makeup_gain_db": 6.0},
        "delay": {"enabled": True, "delay_time_ms": 320.0, "feedback": 0.45, "damping": 0.3, "dry_wet": 0.28},
        "reverb": {"enabled": True, "room_size": 0.75, "damping": 0.25, "dry_wet": 0.32, "width": 1.0}
    },

    "Efeito Rádio / Megafone": {
        "description": "Efeito telefônico filtrado ideal para intros, pontes ou segundos versos estilizados.",
        "input_gain": 1.1,
        "output_gain": 0.9,
        "gate": {"enabled": True, "threshold_db": -45.0, "attack_ms": 1.0, "release_ms": 50.0},
        "autotune": {"enabled": False, "root_note": "C", "scale_name": "Cromática", "snap_speed": 0.0, "amount": 0.0},
        "eq": {"enabled": True, "highpass_enabled": True, "low_gain_db": -12.0, "mid_gain_db": 7.0, "high_gain_db": -10.0},
        "compressor": {"enabled": True, "threshold_db": -24.0, "ratio": 10.0, "attack_ms": 2.0, "release_ms": 40.0, "makeup_gain_db": 8.0},
        "delay": {"enabled": True, "delay_time_ms": 120.0, "feedback": 0.35, "damping": 0.7, "dry_wet": 0.22},
        "reverb": {"enabled": True, "room_size": 0.3, "damping": 0.7, "dry_wet": 0.15, "width": 0.4}
    },

    "Espaço Trap (Deep Reverb)": {
        "description": "Voz imersiva e etérea com reverberação profunda e eco longo para refrões hipnotizantes.",
        "input_gain": 1.0,
        "output_gain": 0.95,
        "gate": {"enabled": True, "threshold_db": -42.0, "attack_ms": 1.0, "release_ms": 70.0},
        "autotune": {"enabled": True, "root_note": "D", "scale_name": "Menor Natural", "snap_speed": 0.05, "amount": 0.85},
        "eq": {"enabled": True, "highpass_enabled": True, "low_gain_db": -1.0, "mid_gain_db": 2.0, "high_gain_db": 4.0},
        "compressor": {"enabled": True, "threshold_db": -20.0, "ratio": 5.0, "attack_ms": 10.0, "release_ms": 90.0, "makeup_gain_db": 5.0},
        "delay": {"enabled": True, "delay_time_ms": 420.0, "feedback": 0.55, "damping": 0.25, "dry_wet": 0.35},
        "reverb": {"enabled": True, "room_size": 0.90, "damping": 0.20, "dry_wet": 0.45, "width": 1.0}
    }
}
