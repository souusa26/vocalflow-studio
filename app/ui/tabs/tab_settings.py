"""
Aba de Configurações de Latência, Buffer e Guia de Configuração do Microfone Virtual.
Explica a instalação do VB-Audio Virtual Cable, configuração no Discord/OBS e ajuste de buffer.
"""

import webbrowser
from html import escape
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QComboBox, QGroupBox, QTextBrowser, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt

from app.audio.engine import AudioEngine
from app.audio.devices import find_virtual_cable_output
from app.config import is_portable_mode, get_data_dir

VB_CABLE_OFFICIAL_URL = "https://vb-audio.com/Cable/"

class TabSettings(QWidget):
    def __init__(self, audio_engine: AudioEngine, parent=None):
        super().__init__(parent)
        self.engine = audio_engine
        self._init_ui()
        self._check_virtual_status()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        intro = QLabel("Ajuste o áudio e conecte sua voz ao Discord ou OBS.")
        intro.setObjectName("sectionIntro")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        # -------------------------------------------------------------
        # 1. LATÊNCIA E BUFFER DE ÁUDIO
        # -------------------------------------------------------------
        buffer_group = QGroupBox("Desempenho do áudio")
        buffer_layout = QGridLayout(buffer_group)
        buffer_layout.setContentsMargins(14, 14, 14, 14)
        buffer_layout.setHorizontalSpacing(16)
        buffer_layout.setVerticalSpacing(8)

        buffer_layout.addWidget(QLabel("Tamanho do buffer"), 0, 0)
        self.combo_buffer = QComboBox()
        self.combo_buffer.addItems(["128 amostras — menor atraso",
                                    "256 amostras — menor atraso",
                                    "512 amostras — recomendado",
                                    "1024 amostras — para computadores mais lentos"])
        self.combo_buffer.setCurrentIndex([128, 256, 512, 1024].index(self.engine.block_size))
        self.combo_buffer.setToolTip("Se ouvir falhas ou estalos, experimente aumentar o buffer.")
        self.combo_buffer.currentIndexChanged.connect(self._on_buffer_changed)
        buffer_layout.addWidget(self.combo_buffer, 0, 1)

        buffer_layout.addWidget(QLabel("Taxa de amostragem"), 1, 0)
        self.combo_sr = QComboBox()
        self.combo_sr.addItems(["48000 Hz (Padrão de Vídeo/Discord/OBS)", "44100 Hz (Padrão CD)"])
        self.combo_sr.setCurrentIndex([48000, 44100].index(self.engine.sample_rate))
        self.combo_sr.currentIndexChanged.connect(self._on_sr_changed)
        buffer_layout.addWidget(self.combo_sr, 1, 1)

        self.lbl_latency_info = QLabel("⏱️ Latência Teórica do Buffer: ~5.3 ms (excluindo conversão dos drivers)")
        self.lbl_latency_info.setObjectName("mutedText")
        self.lbl_latency_info.setWordWrap(True)
        buffer_layout.addWidget(self.lbl_latency_info, 2, 0, 1, 2)

        self._show_latency()
        layout.addWidget(buffer_group)

        # -------------------------------------------------------------
        # 2. STATUS DO CABO VIRTUAL E ASSISTENTE DE INSTALAÇÃO
        # -------------------------------------------------------------
        vc_group = QGroupBox("Conectar ao Discord ou OBS")
        vc_layout = QVBoxLayout(vc_group)
        vc_layout.setContentsMargins(14, 14, 14, 14)
        vc_layout.setSpacing(10)

        # Status do Driver
        status_row = QHBoxLayout()
        self.lbl_vc_status = QLabel("Verificando dispositivo virtual...")
        self.lbl_vc_status.setStyleSheet("font-size: 13px; font-weight: bold;")
        status_row.addWidget(self.lbl_vc_status, stretch=1)

        btn_download_vc = QPushButton("Baixar VB-Cable")
        btn_download_vc.setObjectName("btn_primary")
        btn_download_vc.clicked.connect(lambda: webbrowser.open(VB_CABLE_OFFICIAL_URL))
        status_row.addWidget(btn_download_vc)

        btn_recheck = QPushButton("Verificar novamente")
        btn_recheck.clicked.connect(self._check_virtual_status)
        status_row.addWidget(btn_recheck)

        vc_layout.addLayout(status_row)

        # Manual em HTML formatado com instruções claras
        self.browser_guide = QTextBrowser()
        self.browser_guide.setOpenExternalLinks(True)
        self.browser_guide.setStyleSheet("""
            QTextBrowser {
                background-color: #16171d;
                border: 1px solid #282a33;
                border-radius: 6px;
                padding: 12px;
                color: #e0e0e0;
                font-size: 12px;
                line-height: 1.5;
            }
        """)

        mode_str = "Modo Portátil Ativo (Sem instalação necessária)" if is_portable_mode() else "Modo Padrão Instalado"
        storage_path = escape(str(get_data_dir()))

        guide_html = f"""
        <h3 style="color: #aabaff; margin-top:0;">Sua voz com efeitos em outros aplicativos</h3>
        
        <p>O VB-Cable conecta a saída do VocalFlow à entrada de microfone do Discord ou OBS.</p>
        
        <p><b>Passo a passo:</b></p>
        <ul>
            <li><b>No VocalFlow Studio (Aba Voz):</b>
                <ul>
                    <li>Em <i>Microfone de Entrada</i>, escolha seu microfone físico real.</li>
                    <li>Em <i>Saída Virtual</i>, selecione <b>CABLE Input (VB-Audio Virtual Cable)</b>.</li>
                    <li>Em <i>Monitor 1</i>, selecione seu <b>Fone de Ouvido</b> para você se escutar ao vivo.</li>
                </ul>
            </li>
            <br>
            <li><b>No Discord:</b>
                <ul>
                    <li>Vá em <i>Configurações de Usuário ➔ Voz e Vídeo</i>.</li>
                    <li>Em <b>Dispositivo de Entrada</b>, selecione <b>CABLE Output (VB-Audio Virtual Cable)</b>.</li>
                    <li>Em <b>Dispositivo de Saída</b>, mantenha seu <b>Fone de Ouvido</b>.</li>
                    <li><i>Dica de Ouro:</i> Desative o 'Cancelamento de Ruído Krisp' do Discord para que seus efeitos de autotune e reverb não sejam cortados!</li>
                </ul>
            </li>
            <br>
            <li><b>No OBS Studio:</b>
                <ul>
                    <li>Vá em <i>Configurações ➔ Áudio ➔ Dispositivos Globais de Áudio</i>.</li>
                    <li>Em <b>Áudio do Mic/Auxiliar</b>, selecione <b>CABLE Output (VB-Audio Virtual Cable)</b>.</li>
                </ul>
            </li>
        </ul>

        <hr style="border: 1px solid #282a33;">
        <p><b>Informações do Sistema:</b><br>
        • Status da Aplicação: <span style="color:#00e676;">{mode_str}</span><br>
        • Diretório Local de Armazenamento: <code style="color:#ffb300;">{storage_path}</code><br>
        • Licença do VB-Audio Cable: Freeware/Donationware (gratuito para uso pessoal). Os drivers não são alterados silenciosamente.</p>
        """
        self.browser_guide.setHtml(guide_html)
        vc_layout.addWidget(self.browser_guide)

        layout.addWidget(vc_group)

    def _check_virtual_status(self):
        vc = find_virtual_cable_output()
        if vc is not None:
            self.lbl_vc_status.setText(f"✅ Dispositivo Virtual Detectado: {vc['name']}")
            self.lbl_vc_status.setStyleSheet("color: #00e676; font-size: 13px; font-weight: bold;")
        else:
            self.lbl_vc_status.setText("⚠️ Nenhum cabo virtual detectado no Windows.")
            self.lbl_vc_status.setStyleSheet("color: #ff9800; font-size: 13px; font-weight: bold;")

    def _show_latency(self):
        ms = self.engine.block_size / self.engine.sample_rate * 1000.0
        self.lbl_latency_info.setText(
            f"Cada buffer: {ms:.1f} ms. Uma fila adicional ajuda a evitar cortes; "
            "o atraso total também depende da afinação e dos dispositivos. "
            "Se ouvir estalos, aumente o tamanho do buffer.")

    def _on_buffer_changed(self, idx: int):
        try:
            self.engine.configure(block_size=[128, 256, 512, 1024][idx])
        except RuntimeError as exc:
            QMessageBox.warning(self, "Configuração de áudio", str(exc))
        self._show_latency()

    def _on_sr_changed(self, idx: int):
        try:
            self.engine.configure(sample_rate=[48000, 44100][idx])
        except RuntimeError as exc:
            QMessageBox.warning(self, "Configuração de áudio", str(exc))
        self._show_latency()
