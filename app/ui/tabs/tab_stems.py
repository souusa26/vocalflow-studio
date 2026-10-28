"""
Aba de Separação de Músicas e Reprodutor de Stems (Tab Stems & Backing Track).
Permite separar músicas locais (Voz, Instrumental, Bateria, Baixo), mixar pistas,
cantar por cima com monitoramento e roteamento seletivo para Discord/OBS.
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QProgressBar, QFileDialog, QMessageBox, QGroupBox, QSlider, QCheckBox,
    QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer

from app.audio.engine import AudioEngine
from app.stems.separator import SeparationEngine
from app.stems.player import StemPlayer
from app.stems.exporter import StemExporter
from app.ui.widgets.stem_strip import StemStripWidget

class SeparationWorker(QThread):
    progress_changed = pyqtSignal(int, str)
    finished_success = pyqtSignal(dict)
    finished_error = pyqtSignal(str)

    def __init__(self, file_path: Path, use_ai: bool):
        super().__init__()
        self.file_path = file_path
        self.use_ai = use_ai
        self.engine = SeparationEngine()

    def run(self):
        try:
            stems = self.engine.separate(
                self.file_path,
                use_ai_model=self.use_ai,
                progress_cb=self._on_progress
            )
            self.finished_success.emit(stems)
        except InterruptedError:
            self.finished_error.emit("Separação cancelada pelo usuário.")
        except Exception as e:
            self.finished_error.emit(f"Falha durante a separação: {str(e)}")

    def _on_progress(self, percent: int, msg: str):
        self.progress_changed.emit(percent, msg)

    def cancel(self):
        self.engine.cancel()

class TabStems(QWidget):
    def __init__(self, audio_engine: AudioEngine, parent=None):
        super().__init__(parent)
        self.engine = audio_engine
        self.player = audio_engine.stem_player
        self.worker: Optional[SeparationWorker] = None
        self.current_stems = {}

        self._init_ui()

        # Timer para atualizar a barra de tempo da reprodução (15 FPS)
        self.timeline_timer = QTimer(self)
        self.timeline_timer.setInterval(66)
        self.timeline_timer.timeout.connect(self._update_timeline)
        self.timeline_timer.start()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        # -------------------------------------------------------------
        # 1. SEÇÃO DE IMPORTAÇÃO E SEPARAÇÃO DE FONTES
        # -------------------------------------------------------------
        sep_group = QGroupBox("Importar e Separar Música em Faixas (Stem Separator)")
        sep_layout = QVBoxLayout(sep_group)
        sep_layout.setContentsMargins(14, 14, 14, 14)
        sep_layout.setSpacing(10)

        top_row = QHBoxLayout()
        self.btn_select_file = QPushButton("📁 Escolher Música (MP3, WAV, FLAC, OGG)...")
        self.btn_select_file.setFixedHeight(36)
        self.btn_select_file.clicked.connect(self._select_audio_file)
        top_row.addWidget(self.btn_select_file)

        self.lbl_selected_file = QLabel("Nenhum arquivo carregado")
        self.lbl_selected_file.setStyleSheet("color: #9e9e9e; font-style: italic;")
        top_row.addWidget(self.lbl_selected_file, stretch=1)

        self.chk_use_ai = QCheckBox("Usar Modelo Neural Demucs (4 Stems IA)")
        self.chk_use_ai.setToolTip("Processamento neural de estúdio. Requer PyTorch instalado.")
        top_row.addWidget(self.chk_use_ai)

        self.btn_start_sep = QPushButton("⚡ Iniciar Separação")
        self.btn_start_sep.setObjectName("btn_primary")
        self.btn_start_sep.setFixedHeight(36)
        self.btn_start_sep.setEnabled(False)
        self.btn_start_sep.clicked.connect(self._start_separation)
        top_row.addWidget(self.btn_start_sep)

        self.btn_cancel_sep = QPushButton("✖ Cancelar")
        self.btn_cancel_sep.setFixedHeight(36)
        self.btn_cancel_sep.setEnabled(False)
        self.btn_cancel_sep.clicked.connect(self._cancel_separation)
        top_row.addWidget(self.btn_cancel_sep)

        sep_layout.addLayout(top_row)

        # Barra de Progresso
        prog_row = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        prog_row.addWidget(self.progress_bar)

        self.lbl_progress_status = QLabel("Pronto.")
        self.lbl_progress_status.setStyleSheet("color: #00e5ff; font-size: 11px;")
        prog_row.addWidget(self.lbl_progress_status)
        sep_layout.addLayout(prog_row)

        layout.addWidget(sep_group)

        # -------------------------------------------------------------
        # 2. SEÇÃO STEM PLAYER & REPRODUÇÃO MULTI-FAIXA
        # -------------------------------------------------------------
        player_group = QGroupBox("Reprodutor de Stems & Base para Canto (Backing Track)")
        player_layout = QVBoxLayout(player_group)
        player_layout.setContentsMargins(14, 14, 14, 14)
        player_layout.setSpacing(10)

        # Linha de Transporte (Play, Pause, Stop, Timeline, Roteamento)
        trans_layout = QHBoxLayout()

        self.btn_play = QPushButton("▶ Reproduzir")
        self.btn_play.setFixedSize(110, 36)
        self.btn_play.clicked.connect(self._play_stems)
        trans_layout.addWidget(self.btn_play)

        self.btn_pause = QPushButton("⏸ Pausar")
        self.btn_pause.setFixedSize(90, 36)
        self.btn_pause.clicked.connect(self.player.pause)
        trans_layout.addWidget(self.btn_pause)

        self.btn_stop = QPushButton("⏹ Parar")
        self.btn_stop.setFixedSize(80, 36)
        self.btn_stop.clicked.connect(self._stop_stems)
        trans_layout.addWidget(self.btn_stop)

        self.chk_loop = QCheckBox("🔁 Loop")
        self.chk_loop.toggled.connect(lambda v: setattr(self.player, "loop", v))
        trans_layout.addWidget(self.chk_loop)

        # Timeline Slider
        self.slider_time = QSlider(Qt.Orientation.Horizontal)
        self.slider_time.setRange(0, 1000)
        self.slider_time.sliderMoved.connect(self._on_seek)
        trans_layout.addWidget(self.slider_time, stretch=1)

        self.lbl_time = QLabel("00:00 / 00:00")
        self.lbl_time.setFixedWidth(90)
        self.lbl_time.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_time.setStyleSheet("font-family: monospace; font-size: 12px; color: #00e5ff;")
        trans_layout.addWidget(self.lbl_time)

        player_layout.addLayout(trans_layout)

        # Linha de Regras de Roteamento de Áudio
        route_layout = QHBoxLayout()
        self.chk_route_monitors = QCheckBox("🔊 Ouvir instrumental nos Monitores (Fones/Caixas)")
        self.chk_route_monitors.setChecked(True)
        self.chk_route_monitors.toggled.connect(lambda v: setattr(self.player, "send_to_monitors", v))
        route_layout.addWidget(self.chk_route_monitors)

        self.chk_route_virtual = QCheckBox("🎙️ Enviar instrumental junto ao Microfone Virtual (Discord / OBS)")
        self.chk_route_virtual.setChecked(False) # Padrão desligado para proteção
        self.chk_route_virtual.setToolTip(
            "CUIDADO: Se ativado, a música será transmitida para quem está ouvindo você no Discord/OBS. "
            "Por padrão permanece desativado para transmitir apenas sua voz ao vivo."
        )
        self.chk_route_virtual.toggled.connect(lambda v: setattr(self.player, "send_to_virtual_mic", v))
        route_layout.addWidget(self.chk_route_virtual)
        route_layout.addStretch()

        player_layout.addLayout(route_layout)

        # Scroll com Faixas de Stems
        scroll_stems = QScrollArea()
        scroll_stems.setWidgetResizable(True)
        scroll_stems.setFrameShape(QFrame.Shape.NoFrame)

        stems_widget = QWidget()
        self.stems_vbox = QVBoxLayout(stems_widget)
        self.stems_vbox.setSpacing(6)
        self.stems_vbox.setContentsMargins(0, 4, 0, 4)

        # Cria os canais de stems
        self.stem_strips = {}
        stem_defs = [
            ("instrumental", "Instrumental Completo", "🎹"),
            ("vocals", "Voz Principal (Acapella)", "🎤"),
            ("drums", "Bateria & Percussão", "🥁"),
            ("bass", "Baixo & Sub-Grave", "🎸"),
            ("other", "Outros Sintetizadores", "🎼"),
        ]

        for s_name, s_title, s_icon in stem_defs:
            strip = StemStripWidget(s_name, s_title, s_icon)
            strip.mute_toggled.connect(self.player.set_stem_mute)
            strip.solo_toggled.connect(self.player.set_stem_solo)
            strip.volume_changed.connect(self.player.set_stem_volume)
            self.stem_strips[s_name] = strip
            self.stems_vbox.addWidget(strip)

        scroll_stems.setWidget(stems_widget)
        player_layout.addWidget(scroll_stems)

        # Botões de Exportação
        export_row = QHBoxLayout()
        btn_exp_inst = QPushButton("💾 Exportar Instrumental")
        btn_exp_inst.clicked.connect(lambda: self._export_single_stem("instrumental", "instrumental.wav"))
        export_row.addWidget(btn_exp_inst)

        btn_exp_voc = QPushButton("💾 Exportar Voz (Acapella)")
        btn_exp_voc.clicked.connect(lambda: self._export_single_stem("vocals", "acapella.wav"))
        export_row.addWidget(btn_exp_voc)

        btn_exp_mix = QPushButton("💾 Exportar Mixagem Atual")
        btn_exp_mix.clicked.connect(self._export_custom_mix)
        export_row.addWidget(btn_exp_mix)

        player_layout.addLayout(export_row)
        layout.addWidget(player_group)

    # -------------------------------------------------------------
    # OPERAÇÕES DE ARQUIVO E SEPARAÇÃO
    # -------------------------------------------------------------
    def _select_audio_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecionar Arquivo de Música", "",
            "Áudios Suportados (*.mp3 *.wav *.flac *.ogg *.m4a);;Todos os Arquivos (*.*)"
        )
        if path:
            self.selected_file_path = Path(path)
            self.lbl_selected_file.setText(self.selected_file_path.name)
            self.lbl_selected_file.setStyleSheet("color: #ffffff; font-weight: bold;")
            self.btn_start_sep.setEnabled(True)

    def _start_separation(self):
        if not hasattr(self, "selected_file_path") or not self.selected_file_path.exists():
            return

        use_ai = self.chk_use_ai.isChecked()
        self.btn_start_sep.setEnabled(False)
        self.btn_cancel_sep.setEnabled(True)
        self.btn_select_file.setEnabled(False)

        self.worker = SeparationWorker(self.selected_file_path, use_ai)
        self.worker.progress_changed.connect(self._on_worker_progress)
        self.worker.finished_success.connect(self._on_worker_success)
        self.worker.finished_error.connect(self._on_worker_error)
        self.worker.start()

    def _cancel_separation(self):
        if self.worker:
            self.worker.cancel()
            self.btn_cancel_sep.setEnabled(False)

    def _on_worker_progress(self, percent: int, msg: str):
        self.progress_bar.setValue(percent)
        self.lbl_progress_status.setText(msg)

    def _on_worker_success(self, stems: dict):
        self.current_stems = stems
        self.player.load_stems(stems)
        self.progress_bar.setValue(100)
        self.lbl_progress_status.setText("Faixas separadas prontas no mixer!")
        self.btn_start_sep.setEnabled(True)
        self.btn_cancel_sep.setEnabled(False)
        self.btn_select_file.setEnabled(True)
        QMessageBox.information(self, "Separação Concluída", "Faixas de stems geradas e carregadas no reprodutor com sucesso!")

    def _on_worker_error(self, err_msg: str):
        self.btn_start_sep.setEnabled(True)
        self.btn_cancel_sep.setEnabled(False)
        self.btn_select_file.setEnabled(True)
        self.lbl_progress_status.setText("Erro.")
        QMessageBox.warning(self, "Separação", err_msg)

    # -------------------------------------------------------------
    # CONTROLES DE REPRODUÇÃO E TIMELINE
    # -------------------------------------------------------------
    def _play_stems(self):
        if not self.player.tracks:
            QMessageBox.information(self, "Aviso", "Separe ou carregue uma música primeiro.")
            return
        self.player.play()

    def _stop_stems(self):
        self.player.stop()
        self.slider_time.setValue(0)

    def _on_seek(self, slider_val: int):
        dur = self.player.get_duration_seconds()
        if dur > 0:
            target_sec = (slider_val / 1000.0) * dur
            self.player.seek_seconds(target_sec)

    def _update_timeline(self):
        dur = self.player.get_duration_seconds()
        pos = self.player.get_position_seconds()

        if dur > 0:
            ratio = int((pos / dur) * 1000.0)
            if not self.slider_time.isSliderDown():
                self.slider_time.setValue(ratio)

            pos_m, pos_s = divmod(int(pos), 60)
            dur_m, dur_s = divmod(int(dur), 60)
            self.lbl_time.setText(f"{pos_m:02d}:{pos_s:02d} / {dur_m:02d}:{dur_s:02d}")
        else:
            self.lbl_time.setText("00:00 / 00:00")

    # -------------------------------------------------------------
    # EXPORTAÇÃO DE STEMS
    # -------------------------------------------------------------
    def _export_single_stem(self, stem_name: str, default_filename: str):
        if stem_name not in self.player.tracks:
            QMessageBox.warning(self, "Aviso", f"A faixa '{stem_name}' ainda não está disponível.")
            return
        path, _ = QFileDialog.getSaveFileName(self, f"Exportar {stem_name}", default_filename, "Áudio WAV (*.wav)")
        if path:
            if StemExporter.export_stem(self.player, stem_name, Path(path)):
                QMessageBox.information(self, "Exportado", f"Arquivo exportado com sucesso para:\n{path}")

    def _export_custom_mix(self):
        if not self.player.tracks:
            QMessageBox.warning(self, "Aviso", "Nenhuma faixa carregada para exportar.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Exportar Mixagem Atual", "mix_final.wav", "Áudio WAV (*.wav)")
        if path:
            if StemExporter.export_custom_mix(self.player, Path(path)):
                QMessageBox.information(self, "Exportado", f"Mixagem exportada com sucesso para:\n{path}")
