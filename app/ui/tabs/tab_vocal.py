"""
Aba Principal de Processamento Vocal e Rack de Efeitos (Tab Vocal).
Gerencia seleção de microfone, cabo virtual (Discord/OBS), até 2 monitores físicos,
alerta de microfonia, controles de volume, medidores VU e o rack completo de efeitos.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QComboBox, QSlider, QCheckBox, QGroupBox, QScrollArea, QFrame,
    QMessageBox, QInputDialog, QFileDialog
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor

from app.audio.engine import AudioEngine
from app.audio.devices import get_audio_devices, find_virtual_cable_output, is_speaker_name
from app.audio.dsp.autotune import NOTE_NAMES, SCALE_INTERVALS
from app.presets.manager import PresetManager
from app.ui.widgets.vu_meter import VUMeter

class TabVocal(QWidget):
    def __init__(self, audio_engine: AudioEngine, preset_manager: PresetManager, parent=None):
        super().__init__(parent)
        self.engine = audio_engine
        self.preset_mgr = preset_manager
        self._reported_error = None
        self._displayed_running = None

        self._init_ui()
        self._refresh_devices()
        self._refresh_presets_combo()

        # Timer de atualização visual dos medidores VU (30 FPS)
        self.meter_timer = QTimer(self)
        self.meter_timer.setInterval(33)
        self.meter_timer.timeout.connect(self._update_meters)
        self.meter_timer.start()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(12)

        # -------------------------------------------------------------
        # 1. BARRA SUPERIOR: MASTER ON/OFF + DISPOSITIVOS E MONITORAMENTO
        # -------------------------------------------------------------
        top_group = QGroupBox("Dispositivos de Áudio e Roteamento")
        top_layout = QGridLayout(top_group)
        top_layout.setContentsMargins(14, 14, 14, 14)
        top_layout.setHorizontalSpacing(14)
        top_layout.setVerticalSpacing(8)

        # Microfone de Entrada
        top_layout.addWidget(QLabel("🎤 Microfone de Entrada:"), 0, 0)
        self.combo_input = QComboBox()
        self.combo_input.currentIndexChanged.connect(self._on_input_device_changed)
        top_layout.addWidget(self.combo_input, 0, 1)

        # Cabo Virtual (Discord / OBS)
        top_layout.addWidget(QLabel("🌐 Saída Virtual (Discord / OBS):"), 1, 0)
        self.combo_virtual = QComboBox()
        self.combo_virtual.currentIndexChanged.connect(self._on_virtual_device_changed)
        top_layout.addWidget(self.combo_virtual, 1, 1)

        # Monitor 1 (ex: Fones de Ouvido)
        mon1_header = QHBoxLayout()
        self.chk_mon1 = QCheckBox("🎧 Monitor 1 (Fone):")
        self.chk_mon1.setChecked(True)
        self.chk_mon1.toggled.connect(self._on_mon1_toggled)
        mon1_header.addWidget(self.chk_mon1)
        top_layout.addLayout(mon1_header, 0, 2)

        self.combo_mon1 = QComboBox()
        self.combo_mon1.currentIndexChanged.connect(self._on_mon1_device_changed)
        top_layout.addWidget(self.combo_mon1, 0, 3)

        self.slider_mon1_vol = QSlider(Qt.Orientation.Horizontal)
        self.slider_mon1_vol.setRange(0, 150)
        self.slider_mon1_vol.setValue(100)
        self.slider_mon1_vol.valueChanged.connect(lambda v: self.engine.set_monitor1(self.chk_mon1.isChecked(), volume=v/100.0))
        top_layout.addWidget(self.slider_mon1_vol, 0, 4)

        # Monitor 2 (ex: Caixas de Som)
        mon2_header = QHBoxLayout()
        self.chk_mon2 = QCheckBox("🔊 Monitor 2 (Caixa):")
        self.chk_mon2.setChecked(False)
        self.chk_mon2.toggled.connect(self._on_mon2_toggled)
        mon2_header.addWidget(self.chk_mon2)
        top_layout.addLayout(mon2_header, 1, 2)

        self.combo_mon2 = QComboBox()
        self.combo_mon2.currentIndexChanged.connect(self._on_mon2_device_changed)
        top_layout.addWidget(self.combo_mon2, 1, 3)

        self.slider_mon2_vol = QSlider(Qt.Orientation.Horizontal)
        self.slider_mon2_vol.setRange(0, 150)
        self.slider_mon2_vol.setValue(100)
        self.slider_mon2_vol.valueChanged.connect(lambda v: self.engine.set_monitor2(self.chk_mon2.isChecked(), volume=v/100.0))
        top_layout.addWidget(self.slider_mon2_vol, 1, 4)

        # Botão Atualizar Dispositivos
        btn_refresh_devs = QPushButton("🔄 Atualizar")
        btn_refresh_devs.clicked.connect(self._refresh_devices)
        top_layout.addWidget(btn_refresh_devs, 0, 5, 2, 1)

        main_layout.addWidget(top_group)

        # ALERTA DE MICROFONIA (Banner ocultável)
        self.lbl_feedback_warning = QLabel(
            "⚠️ ATENÇÃO: Monitor 2 está conectado a uma Caixa de Som! "
            "Para evitar microfonia aguda (feedback loop), afaste o microfone da caixa ou use fones de ouvido."
        )
        self.lbl_feedback_warning.setStyleSheet("""
            background-color: #3e2723;
            color: #ffcc80;
            border: 1px solid #ff9800;
            border-radius: 6px;
            padding: 8px 12px;
            font-weight: bold;
            font-size: 12px;
        """)
        self.lbl_feedback_warning.setVisible(False)
        main_layout.addWidget(self.lbl_feedback_warning)

        # -------------------------------------------------------------
        # 2. BARRA DE CONTROLE MASTER E PRESETS
        # -------------------------------------------------------------
        mid_layout = QHBoxLayout()

        # Botão Master Ligar/Desligar Voz
        self.btn_live = QPushButton("🎙️ INICIAR PROCESSAMENTO (AO VIVO)")
        self.btn_live.setObjectName("btn_live_off")
        self.btn_live.setFixedHeight(44)
        self.btn_live.setFixedWidth(290)
        self.btn_live.clicked.connect(self._toggle_engine)
        mid_layout.addWidget(self.btn_live)

        # VU Meters Entrada e Saída
        meter_box = QGroupBox("Níveis de Áudio (VU)")
        meter_layout = QGridLayout(meter_box)
        meter_layout.setContentsMargins(10, 8, 10, 8)
        meter_layout.addWidget(QLabel("Entrada:"), 0, 0)
        self.meter_in = VUMeter(is_horizontal=True)
        meter_layout.addWidget(self.meter_in, 0, 1)

        meter_layout.addWidget(QLabel("Saída:"), 1, 0)
        self.meter_out = VUMeter(is_horizontal=True)
        meter_layout.addWidget(self.meter_out, 1, 1)
        mid_layout.addWidget(meter_box)

        # Seção Presets
        preset_box = QGroupBox("Presets Vocais")
        preset_layout = QHBoxLayout(preset_box)
        preset_layout.setContentsMargins(10, 8, 10, 8)

        self.combo_presets = QComboBox()
        self.combo_presets.setMinimumWidth(180)
        self.combo_presets.currentIndexChanged.connect(self._on_preset_selected)
        preset_layout.addWidget(self.combo_presets)

        btn_save_preset = QPushButton("💾 Salvar")
        btn_save_preset.clicked.connect(self._save_new_preset)
        preset_layout.addWidget(btn_save_preset)

        btn_del_preset = QPushButton("🗑️ Excluir")
        btn_del_preset.clicked.connect(self._delete_preset)
        preset_layout.addWidget(btn_del_preset)

        btn_export_preset = QPushButton("📤 Exportar")
        btn_export_preset.clicked.connect(self._export_preset)
        preset_layout.addWidget(btn_export_preset)

        mid_layout.addWidget(preset_box)
        main_layout.addLayout(mid_layout)

        # -------------------------------------------------------------
        # 3. RACK DE EFEITOS (SCROLL ÁREA COM TODOS OS CARDS DE EFEITOS)
        # -------------------------------------------------------------
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        rack_content = QWidget()
        rack_layout = QVBoxLayout(rack_content)
        rack_layout.setSpacing(10)
        rack_layout.setContentsMargins(4, 4, 4, 4)

        # Card 1: NOISE GATE
        rack_layout.addWidget(self._build_gate_card())

        # Card 2: AUTOTUNE / PITCH CORRECTION
        rack_layout.addWidget(self._build_autotune_card())

        # Card 3: EQUALIZADOR PARAMÉTRICO
        rack_layout.addWidget(self._build_eq_card())

        # Card 4: COMPRESSOR DE ESTÚDIO
        rack_layout.addWidget(self._build_compressor_card())

        # Card 5: DELAY / ECO
        rack_layout.addWidget(self._build_delay_card())

        # Card 6: REVERB ESTÉREO
        rack_layout.addWidget(self._build_reverb_card())

        scroll.setWidget(rack_content)
        main_layout.addWidget(scroll)

    # -------------------------------------------------------------
    # CONSTRUÇÃO DOS CARDS DO RACK DE EFEITOS
    # -------------------------------------------------------------
    def _build_gate_card(self) -> QGroupBox:
        box = QGroupBox("1. Noise Gate (Redução de Ruído & Respirações)")
        layout = QGridLayout(box)

        self.chk_gate = QCheckBox("Ativado")
        self.chk_gate.setChecked(self.engine.fx_chain.gate.enabled)
        self.chk_gate.toggled.connect(lambda v: self.engine.fx_chain.gate.set_params(enabled=v))
        layout.addWidget(self.chk_gate, 0, 0)

        layout.addWidget(QLabel("Limiar (Threshold):"), 0, 1)
        self.slider_gate_thresh = QSlider(Qt.Orientation.Horizontal)
        self.slider_gate_thresh.setRange(-70, -10)
        self.slider_gate_thresh.setValue(int(self.engine.fx_chain.gate.threshold_db))
        self.lbl_gate_thresh = QLabel(f"{self.engine.fx_chain.gate.threshold_db:.0f} dB")
        self.slider_gate_thresh.valueChanged.connect(self._on_gate_thresh_changed)
        layout.addWidget(self.slider_gate_thresh, 0, 2)
        layout.addWidget(self.lbl_gate_thresh, 0, 3)

        layout.addWidget(QLabel("Release:"), 0, 4)
        self.slider_gate_rel = QSlider(Qt.Orientation.Horizontal)
        self.slider_gate_rel.setRange(10, 300)
        self.slider_gate_rel.setValue(int(self.engine.fx_chain.gate.release_ms))
        self.lbl_gate_rel = QLabel(f"{self.engine.fx_chain.gate.release_ms:.0f} ms")
        self.slider_gate_rel.valueChanged.connect(lambda v: (
            self.engine.fx_chain.gate.set_params(release_ms=v),
            self.lbl_gate_rel.setText(f"{v} ms")
        ))
        layout.addWidget(self.slider_gate_rel, 0, 5)
        layout.addWidget(self.lbl_gate_rel, 0, 6)
        return box

    def _on_gate_thresh_changed(self, val: int):
        self.engine.fx_chain.gate.set_params(threshold_db=val)
        self.lbl_gate_thresh.setText(f"{val} dB")

    def _build_autotune_card(self) -> QGroupBox:
        box = QGroupBox("2. Autotune / Correção de Afinação (Motor YIN + Numba JIT)")
        layout = QGridLayout(box)

        self.chk_tune = QCheckBox("Ativado")
        self.chk_tune.setChecked(self.engine.fx_chain.autotune.enabled)
        self.chk_tune.toggled.connect(lambda v: self.engine.fx_chain.autotune.set_params(enabled=v))
        layout.addWidget(self.chk_tune, 0, 0)

        # Tom Base (Key)
        layout.addWidget(QLabel("Tom Base:"), 0, 1)
        self.combo_tune_root = QComboBox()
        self.combo_tune_root.addItems(NOTE_NAMES)
        self.combo_tune_root.setCurrentText(self.engine.fx_chain.autotune.root_note)
        self.combo_tune_root.currentTextChanged.connect(lambda r: self.engine.fx_chain.autotune.set_params(root=r))
        layout.addWidget(self.combo_tune_root, 0, 2)

        # Escala
        layout.addWidget(QLabel("Escala Musical:"), 0, 3)
        self.combo_tune_scale = QComboBox()
        self.combo_tune_scale.addItems(list(SCALE_INTERVALS.keys()))
        self.combo_tune_scale.setCurrentText(self.engine.fx_chain.autotune.scale_name)
        self.combo_tune_scale.currentTextChanged.connect(lambda s: self.engine.fx_chain.autotune.set_params(scale=s))
        layout.addWidget(self.combo_tune_scale, 0, 4)

        # Velocidade do Snap (Hard snap de Trap vs Suave)
        layout.addWidget(QLabel("Velocidade (Snap):"), 1, 1)
        self.slider_tune_speed = QSlider(Qt.Orientation.Horizontal)
        self.slider_tune_speed.setRange(0, 100)
        self.slider_tune_speed.setValue(int(self.engine.fx_chain.autotune.snap_speed * 100))
        self.lbl_tune_speed = QLabel("Hard Snap (Trap)")
        self.slider_tune_speed.valueChanged.connect(self._on_tune_speed_changed)
        layout.addWidget(self.slider_tune_speed, 1, 2)
        layout.addWidget(self.lbl_tune_speed, 1, 3)

        # Quantidade (Dry/Wet)
        layout.addWidget(QLabel("Intensidade (Dry/Wet):"), 1, 4)
        self.slider_tune_amount = QSlider(Qt.Orientation.Horizontal)
        self.slider_tune_amount.setRange(0, 100)
        self.slider_tune_amount.setValue(int(self.engine.fx_chain.autotune.amount * 100))
        self.lbl_tune_amount = QLabel(f"{int(self.engine.fx_chain.autotune.amount * 100)}%")
        self.slider_tune_amount.valueChanged.connect(lambda v: (
            self.engine.fx_chain.autotune.set_params(amount=v/100.0),
            self.lbl_tune_amount.setText(f"{v}%")
        ))
        layout.addWidget(self.slider_tune_amount, 1, 5)
        layout.addWidget(self.lbl_tune_amount, 1, 6)
        return box

    def _on_tune_speed_changed(self, val: int):
        speed_ratio = val / 100.0
        self.engine.fx_chain.autotune.set_params(snap_speed=speed_ratio)
        if val <= 10:
            self.lbl_tune_speed.setText("Hard Snap (Travis Style)")
        elif val >= 75:
            self.lbl_tune_speed.setText("Suave / Natural")
        else:
            self.lbl_tune_speed.setText(f"Intermediário ({val}%)")

    def _build_eq_card(self) -> QGroupBox:
        box = QGroupBox("3. Equalizador Paramétrico de 3 Bandas + High-Pass")
        layout = QGridLayout(box)

        self.chk_eq = QCheckBox("Ativado")
        self.chk_eq.setChecked(self.engine.fx_chain.eq.enabled)
        self.chk_eq.toggled.connect(lambda v: self.engine.fx_chain.eq.set_params(enabled=v))
        layout.addWidget(self.chk_eq, 0, 0)

        self.chk_eq_hp = QCheckBox("High-Pass (< 80Hz)")
        self.chk_eq_hp.setChecked(self.engine.fx_chain.eq.highpass_enabled)
        self.chk_eq_hp.toggled.connect(lambda v: self.engine.fx_chain.eq.set_params(highpass_enabled=v))
        layout.addWidget(self.chk_eq_hp, 0, 1)

        # Graves (Low)
        layout.addWidget(QLabel("Graves (120Hz):"), 0, 2)
        self.slider_eq_low = QSlider(Qt.Orientation.Horizontal)
        self.slider_eq_low.setRange(-12, 12)
        self.slider_eq_low.setValue(int(self.engine.fx_chain.eq.low_gain_db))
        self.lbl_eq_low = QLabel(f"{self.engine.fx_chain.eq.low_gain_db:+.1f} dB")
        self.slider_eq_low.valueChanged.connect(lambda v: (
            self.engine.fx_chain.eq.set_params(low_db=v),
            self.lbl_eq_low.setText(f"{v:+.1f} dB")
        ))
        layout.addWidget(self.slider_eq_low, 0, 3)
        layout.addWidget(self.lbl_eq_low, 0, 4)

        # Médios (Mid)
        layout.addWidget(QLabel("Médios (2.5kHz):"), 1, 0)
        self.slider_eq_mid = QSlider(Qt.Orientation.Horizontal)
        self.slider_eq_mid.setRange(-12, 12)
        self.slider_eq_mid.setValue(int(self.engine.fx_chain.eq.mid_gain_db))
        self.lbl_eq_mid = QLabel(f"{self.engine.fx_chain.eq.mid_gain_db:+.1f} dB")
        self.slider_eq_mid.valueChanged.connect(lambda v: (
            self.engine.fx_chain.eq.set_params(mid_db=v),
            self.lbl_eq_mid.setText(f"{v:+.1f} dB")
        ))
        layout.addWidget(self.slider_eq_mid, 1, 1)
        layout.addWidget(self.lbl_eq_mid, 1, 2)

        # Agudos (High)
        layout.addWidget(QLabel("Brilho (9kHz):"), 1, 3)
        self.slider_eq_high = QSlider(Qt.Orientation.Horizontal)
        self.slider_eq_high.setRange(-12, 12)
        self.slider_eq_high.setValue(int(self.engine.fx_chain.eq.high_gain_db))
        self.lbl_eq_high = QLabel(f"{self.engine.fx_chain.eq.high_gain_db:+.1f} dB")
        self.slider_eq_high.valueChanged.connect(lambda v: (
            self.engine.fx_chain.eq.set_params(high_db=v),
            self.lbl_eq_high.setText(f"{v:+.1f} dB")
        ))
        layout.addWidget(self.slider_eq_high, 1, 4)
        layout.addWidget(self.lbl_eq_high, 1, 5)
        return box

    def _build_compressor_card(self) -> QGroupBox:
        box = QGroupBox("4. Compressor Dinâmico (Consistência & Punch Vocal)")
        layout = QGridLayout(box)

        self.chk_comp = QCheckBox("Ativado")
        self.chk_comp.setChecked(self.engine.fx_chain.compressor.enabled)
        self.chk_comp.toggled.connect(lambda v: self.engine.fx_chain.compressor.set_params(enabled=v))
        layout.addWidget(self.chk_comp, 0, 0)

        # Threshold
        layout.addWidget(QLabel("Limiar (Threshold):"), 0, 1)
        self.slider_comp_thresh = QSlider(Qt.Orientation.Horizontal)
        self.slider_comp_thresh.setRange(-40, 0)
        self.slider_comp_thresh.setValue(int(self.engine.fx_chain.compressor.threshold_db))
        self.lbl_comp_thresh = QLabel(f"{self.engine.fx_chain.compressor.threshold_db:.0f} dB")
        self.slider_comp_thresh.valueChanged.connect(lambda v: (
            self.engine.fx_chain.compressor.set_params(threshold_db=v),
            self.lbl_comp_thresh.setText(f"{v} dB")
        ))
        layout.addWidget(self.slider_comp_thresh, 0, 2)
        layout.addWidget(self.lbl_comp_thresh, 0, 3)

        # Ratio
        layout.addWidget(QLabel("Taxa (Ratio):"), 0, 4)
        self.slider_comp_ratio = QSlider(Qt.Orientation.Horizontal)
        self.slider_comp_ratio.setRange(1, 12)
        self.slider_comp_ratio.setValue(int(self.engine.fx_chain.compressor.ratio))
        self.lbl_comp_ratio = QLabel(f"{self.engine.fx_chain.compressor.ratio:.0f}:1")
        self.slider_comp_ratio.valueChanged.connect(lambda v: (
            self.engine.fx_chain.compressor.set_params(ratio=v),
            self.lbl_comp_ratio.setText(f"{v}:1")
        ))
        layout.addWidget(self.slider_comp_ratio, 0, 5)
        layout.addWidget(self.lbl_comp_ratio, 0, 6)

        # Makeup Gain
        layout.addWidget(QLabel("Ganho (Makeup):"), 1, 1)
        self.slider_comp_makeup = QSlider(Qt.Orientation.Horizontal)
        self.slider_comp_makeup.setRange(0, 14)
        self.slider_comp_makeup.setValue(int(self.engine.fx_chain.compressor.makeup_gain_db))
        self.lbl_comp_makeup = QLabel(f"{self.engine.fx_chain.compressor.makeup_gain_db:+.1f} dB")
        self.slider_comp_makeup.valueChanged.connect(lambda v: (
            self.engine.fx_chain.compressor.set_params(makeup_gain_db=v),
            self.lbl_comp_makeup.setText(f"{v:+.1f} dB")
        ))
        layout.addWidget(self.slider_comp_makeup, 1, 2)
        layout.addWidget(self.lbl_comp_makeup, 1, 3)
        return box

    def _build_delay_card(self) -> QGroupBox:
        box = QGroupBox("5. Eco / Delay Estéreo")
        layout = QGridLayout(box)

        self.chk_delay = QCheckBox("Ativado")
        self.chk_delay.setChecked(self.engine.fx_chain.delay.enabled)
        self.chk_delay.toggled.connect(lambda v: self.engine.fx_chain.delay.set_params(enabled=v))
        layout.addWidget(self.chk_delay, 0, 0)

        # Tempo (ms)
        layout.addWidget(QLabel("Tempo (ms):"), 0, 1)
        self.slider_delay_time = QSlider(Qt.Orientation.Horizontal)
        self.slider_delay_time.setRange(50, 800)
        self.slider_delay_time.setValue(int(self.engine.fx_chain.delay.delay_time_ms))
        self.lbl_delay_time = QLabel(f"{self.engine.fx_chain.delay.delay_time_ms:.0f} ms")
        self.slider_delay_time.valueChanged.connect(lambda v: (
            self.engine.fx_chain.delay.set_params(delay_time_ms=v),
            self.lbl_delay_time.setText(f"{v} ms")
        ))
        layout.addWidget(self.slider_delay_time, 0, 2)
        layout.addWidget(self.lbl_delay_time, 0, 3)

        # Feedback
        layout.addWidget(QLabel("Repetições (Feedback):"), 0, 4)
        self.slider_delay_fb = QSlider(Qt.Orientation.Horizontal)
        self.slider_delay_fb.setRange(0, 80)
        self.slider_delay_fb.setValue(int(self.engine.fx_chain.delay.feedback * 100))
        self.lbl_delay_fb = QLabel(f"{int(self.engine.fx_chain.delay.feedback * 100)}%")
        self.slider_delay_fb.valueChanged.connect(lambda v: (
            self.engine.fx_chain.delay.set_params(feedback=v/100.0),
            self.lbl_delay_fb.setText(f"{v}%")
        ))
        layout.addWidget(self.slider_delay_fb, 0, 5)
        layout.addWidget(self.lbl_delay_fb, 0, 6)

        # Mix Dry/Wet
        layout.addWidget(QLabel("Intensidade (Mix):"), 1, 1)
        self.slider_delay_mix = QSlider(Qt.Orientation.Horizontal)
        self.slider_delay_mix.setRange(0, 100)
        self.slider_delay_mix.setValue(int(self.engine.fx_chain.delay.dry_wet * 100))
        self.lbl_delay_mix = QLabel(f"{int(self.engine.fx_chain.delay.dry_wet * 100)}%")
        self.slider_delay_mix.valueChanged.connect(lambda v: (
            self.engine.fx_chain.delay.set_params(dry_wet=v/100.0),
            self.lbl_delay_mix.setText(f"{v}%")
        ))
        layout.addWidget(self.slider_delay_mix, 1, 2)
        layout.addWidget(self.lbl_delay_mix, 1, 3)
        return box

    def _build_reverb_card(self) -> QGroupBox:
        box = QGroupBox("6. Reverb Estéreo (Ambiência de Estúdio / Espaço Trap)")
        layout = QGridLayout(box)

        self.chk_reverb = QCheckBox("Ativado")
        self.chk_reverb.setChecked(self.engine.fx_chain.reverb.enabled)
        self.chk_reverb.toggled.connect(lambda v: self.engine.fx_chain.reverb.set_params(enabled=v))
        layout.addWidget(self.chk_reverb, 0, 0)

        # Tamanho da Sala (Decay)
        layout.addWidget(QLabel("Tamanho (Decay):"), 0, 1)
        self.slider_rev_size = QSlider(Qt.Orientation.Horizontal)
        self.slider_rev_size.setRange(10, 95)
        self.slider_rev_size.setValue(int(self.engine.fx_chain.reverb.room_size * 100))
        self.lbl_rev_size = QLabel(f"{int(self.engine.fx_chain.reverb.room_size * 100)}%")
        self.slider_rev_size.valueChanged.connect(lambda v: (
            self.engine.fx_chain.reverb.set_params(room_size=v/100.0),
            self.lbl_rev_size.setText(f"{v}%")
        ))
        layout.addWidget(self.slider_rev_size, 0, 2)
        layout.addWidget(self.lbl_rev_size, 0, 3)

        # Mix Dry/Wet
        layout.addWidget(QLabel("Intensidade (Mix):"), 0, 4)
        self.slider_rev_mix = QSlider(Qt.Orientation.Horizontal)
        self.slider_rev_mix.setRange(0, 100)
        self.slider_rev_mix.setValue(int(self.engine.fx_chain.reverb.dry_wet * 100))
        self.lbl_rev_mix = QLabel(f"{int(self.engine.fx_chain.reverb.dry_wet * 100)}%")
        self.slider_rev_mix.valueChanged.connect(lambda v: (
            self.engine.fx_chain.reverb.set_params(dry_wet=v/100.0),
            self.lbl_rev_mix.setText(f"{v}%")
        ))
        layout.addWidget(self.slider_rev_mix, 0, 5)
        layout.addWidget(self.lbl_rev_mix, 0, 6)
        return box

    # -------------------------------------------------------------
    # GERENCIAMENTO DE DISPOSITIVOS E ENGINE
    # -------------------------------------------------------------
    def _refresh_devices(self):
        inputs, outputs = get_audio_devices()

        self.combo_input.blockSignals(True)
        self.combo_virtual.blockSignals(True)
        self.combo_mon1.blockSignals(True)
        self.combo_mon2.blockSignals(True)

        self.combo_input.clear()
        for dev in inputs:
            self.combo_input.addItem(f"{dev['name']} ({dev['hostapi']})", dev["id"])

        self.combo_virtual.clear()
        for dev in outputs:
            prefix = "🌐 " if dev["is_virtual"] else ""
            self.combo_virtual.addItem(f"{prefix}{dev['name']} ({dev['hostapi']})", dev["id"])

        self.combo_mon1.clear()
        self.combo_mon2.clear()
        for dev in outputs:
            self.combo_mon1.addItem(f"{dev['name']} ({dev['hostapi']})", dev["id"])
            self.combo_mon2.addItem(f"{dev['name']} ({dev['hostapi']})", dev["id"])

        # Auto-seleciona cabo virtual se encontrado
        vc = find_virtual_cable_output()
        if vc is not None:
            idx = self.combo_virtual.findData(vc["id"])
            if idx >= 0:
                self.combo_virtual.setCurrentIndex(idx)
                self.engine.virtual_device_id = vc["id"]

        if self.combo_input.count() > 0:
            self.engine.input_device_id = self.combo_input.currentData()
        if self.combo_mon1.count() > 0:
            self.engine.monitor1_device_id = self.combo_mon1.currentData()
        if self.combo_mon2.count() > 0:
            self.engine.monitor2_device_id = self.combo_mon2.currentData()

        self.combo_input.blockSignals(False)
        self.combo_virtual.blockSignals(False)
        self.combo_mon1.blockSignals(False)
        self.combo_mon2.blockSignals(False)

        self._check_speaker_feedback_risk()

    def _on_input_device_changed(self, idx: int):
        dev_id = self.combo_input.itemData(idx)
        self.engine.input_device_id = dev_id
        if self.engine.is_running:
            self._restart_engine()

    def _on_virtual_device_changed(self, idx: int):
        dev_id = self.combo_virtual.itemData(idx)
        self.engine.virtual_device_id = dev_id
        if self.engine.is_running:
            self._restart_engine()

    def _on_mon1_device_changed(self, idx: int):
        dev_id = self.combo_mon1.itemData(idx)
        self.engine.set_monitor1(self.chk_mon1.isChecked(), device_id=dev_id)
        self._check_speaker_feedback_risk()

    def _on_mon2_device_changed(self, idx: int):
        dev_id = self.combo_mon2.itemData(idx)
        self.engine.set_monitor2(self.chk_mon2.isChecked(), device_id=dev_id)
        self._check_speaker_feedback_risk()

    def _on_mon1_toggled(self, checked: bool):
        self.engine.set_monitor1(checked)
        self._check_speaker_feedback_risk()

    def _on_mon2_toggled(self, checked: bool):
        self.engine.set_monitor2(checked)
        self._check_speaker_feedback_risk()

    def _check_speaker_feedback_risk(self):
        """Exibe o aviso de microfonia se alguma saída ativa parecer ser caixa de som."""
        risk = False
        if self.chk_mon2.isChecked() and self.combo_mon2.currentText():
            if is_speaker_name(self.combo_mon2.currentText()):
                risk = True
        if self.chk_mon1.isChecked() and self.combo_mon1.currentText():
            if is_speaker_name(self.combo_mon1.currentText()):
                risk = True
        self.lbl_feedback_warning.setVisible(risk)

    def _toggle_engine(self):
        if self.engine.is_running:
            self.engine.stop()
            self.btn_live.setText("🎙️ INICIAR PROCESSAMENTO (AO VIVO)")
            self.btn_live.setObjectName("btn_live_off")
            self.btn_live.setStyleSheet("")
        else:
            try:
                self.engine.start()
                self.btn_live.setText("🔴 AO VIVO - TRANSMITINDO PROCESSADO")
                self.btn_live.setObjectName("btn_live_on")
                self.btn_live.setStyleSheet("""
                    QPushButton {
                        background-color: #00e676;
                        color: #000000;
                        font-weight: bold;
                        border: 2px solid #00c853;
                    }
                """)
            except Exception as e:
                self._reported_error = self.engine.last_error
                QMessageBox.critical(self, "Falha de Áudio", f"Não foi possível iniciar o fluxo de áudio:\n{e}")

    def _restart_engine(self):
        if self.engine.is_running:
            self.engine.stop()
            try:
                self.engine.start()
            except Exception as e:
                print(f"[TabVocal] Erro ao reiniciar motor: {e}")

    def _update_meters(self):
        running = self.engine.is_running
        if running != self._displayed_running:
            self._displayed_running = running
            self.btn_live.setText("🔴 AO VIVO - TRANSMITINDO PROCESSADO" if running
                                  else "🎙️ INICIAR PROCESSAMENTO (AO VIVO)")
            self.btn_live.setStyleSheet("background-color: #00e676; color: #000000;" if running else "")
        if not running and self.engine.last_error and self.engine.last_error != self._reported_error:
            self._reported_error = self.engine.last_error
            self.engine.stop()
            QMessageBox.warning(self, "Falha de áudio", self._reported_error)
        if self.engine.is_running:
            p_in = self.engine.fx_chain.limiter.input_peak_db
            r_in = self.engine.fx_chain.limiter.input_rms_db
            destination = "virtual" if self.engine.virtual_device_id is not None else (
                "mon1" if self.engine.monitor1_enabled else "mon2")
            meter = self.engine.output_limiters[destination]
            p_out = meter.output_peak_db
            r_out = meter.output_rms_db
            clip = meter.clipped

            self.meter_in.set_levels(p_in, r_in, False)
            self.meter_out.set_levels(p_out, r_out, clip)
        else:
            self.meter_in.set_levels(-60.0, -60.0, False)
            self.meter_out.set_levels(-60.0, -60.0, False)

    # -------------------------------------------------------------
    # GERENCIAMENTO DE PRESETS
    # -------------------------------------------------------------
    def _refresh_presets_combo(self):
        self.combo_presets.blockSignals(True)
        self.combo_presets.clear()
        names = self.preset_mgr.list_presets()
        self.combo_presets.addItems(names)
        self.combo_presets.blockSignals(False)

    def _on_preset_selected(self, idx: int):
        name = self.combo_presets.currentText()
        if not name:
            return
        state = self.preset_mgr.load_preset(name)
        if state:
            self.engine.fx_chain.load_state(state)
            self._sync_ui_with_dsp_state()

    def _sync_ui_with_dsp_state(self):
        chain = self.engine.fx_chain
        # Gate
        self.chk_gate.setChecked(chain.gate.enabled)
        self.slider_gate_thresh.setValue(int(chain.gate.threshold_db))
        self.slider_gate_rel.setValue(int(chain.gate.release_ms))

        # Tune
        self.chk_tune.setChecked(chain.autotune.enabled)
        self.combo_tune_root.setCurrentText(chain.autotune.root_note)
        self.combo_tune_scale.setCurrentText(chain.autotune.scale_name)
        self.slider_tune_speed.setValue(int(chain.autotune.snap_speed * 100))
        self.slider_tune_amount.setValue(int(chain.autotune.amount * 100))

        # EQ
        self.chk_eq.setChecked(chain.eq.enabled)
        self.chk_eq_hp.setChecked(chain.eq.highpass_enabled)
        self.slider_eq_low.setValue(int(chain.eq.low_gain_db))
        self.slider_eq_mid.setValue(int(chain.eq.mid_gain_db))
        self.slider_eq_high.setValue(int(chain.eq.high_gain_db))

        # Comp
        self.chk_comp.setChecked(chain.compressor.enabled)
        self.slider_comp_thresh.setValue(int(chain.compressor.threshold_db))
        self.slider_comp_ratio.setValue(int(chain.compressor.ratio))
        self.slider_comp_makeup.setValue(int(chain.compressor.makeup_gain_db))

        # Delay
        self.chk_delay.setChecked(chain.delay.enabled)
        self.slider_delay_time.setValue(int(chain.delay.delay_time_ms))
        self.slider_delay_fb.setValue(int(chain.delay.feedback * 100))
        self.slider_delay_mix.setValue(int(chain.delay.dry_wet * 100))

        # Reverb
        self.chk_reverb.setChecked(chain.reverb.enabled)
        self.slider_rev_size.setValue(int(chain.reverb.room_size * 100))
        self.slider_rev_mix.setValue(int(chain.reverb.dry_wet * 100))

    def _save_new_preset(self):
        name, ok = QInputDialog.getText(self, "Salvar Preset", "Digite o nome para o novo preset vocal:")
        if ok and name.strip():
            state = self.engine.fx_chain.get_state()
            self.preset_mgr.save_preset(name.strip(), state)
            self._refresh_presets_combo()
            self.combo_presets.setCurrentText(name.strip())
            QMessageBox.information(self, "Preset Salvo", f"Preset '{name.strip()}' salvo com sucesso!")

    def _delete_preset(self):
        name = self.combo_presets.currentText()
        if not name:
            return
        confirm = QMessageBox.question(
            self, "Confirmar Exclusão",
            f"Deseja realmente excluir o preset '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            ok = self.preset_mgr.delete_preset(name)
            if ok:
                self._refresh_presets_combo()
                QMessageBox.information(self, "Excluído", f"Preset '{name}' foi excluído.")
            else:
                QMessageBox.warning(self, "Não Permitido", "Presets originais de fábrica não podem ser excluídos.")

    def _export_preset(self):
        name = self.combo_presets.currentText()
        if not name:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Exportar Preset JSON", f"{name}.json", "Arquivos JSON (*.json)")
        if path:
            from pathlib import Path
            if self.preset_mgr.export_preset(name, Path(path)):
                QMessageBox.information(self, "Exportado", f"Preset exportado com sucesso para:\n{path}")
