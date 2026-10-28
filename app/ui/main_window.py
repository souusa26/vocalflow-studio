"""
Janela Principal da Aplicação (MainWindow).
Reúne as 4 áreas principais do VocalFlow Studio em uma interface moderna e coesa.
"""

from PyQt6.QtWidgets import QMainWindow, QTabWidget, QVBoxLayout, QWidget, QLabel, QHBoxLayout, QStatusBar, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from app.config import APP_TITLE, APP_VERSION
from app.audio.engine import AudioEngine
from app.presets.manager import PresetManager
from app.lyrics.manager import LyricsManager

from app.ui.tabs.tab_vocal import TabVocal
from app.ui.tabs.tab_stems import TabStems
from app.ui.tabs.tab_lyrics import TabLyrics
from app.ui.tabs.tab_settings import TabSettings

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_TITLE} (v{APP_VERSION})")
        self.resize(1100, 750)
        self.setMinimumSize(950, 640)

        # Inicializa gerenciadores e motor de áudio
        self.engine = AudioEngine()
        self.preset_mgr = PresetManager()
        self.lyrics_mgr = LyricsManager()

        self._init_ui()

    def _init_ui(self):
        central_widget = QWidget()
        central_widget.setObjectName("central")
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 16, 20, 10)
        main_layout.setSpacing(12)

        header = QHBoxLayout()
        brand_stack = QVBoxLayout()
        brand_stack.setSpacing(0)
        brand = QLabel("VocalFlow Studio")
        brand.setObjectName("brand")
        subtitle = QLabel("Sua voz, do seu jeito.")
        subtitle.setObjectName("subtitle")
        brand_stack.addWidget(brand)
        brand_stack.addWidget(subtitle)
        header.addLayout(brand_stack)
        header.addStretch()
        brand_accent = QLabel("SEU ESTÚDIO VOCAL")
        brand_accent.setObjectName("brandAccent")
        header.addWidget(brand_accent)
        main_layout.addLayout(header)

        # Abas de Navegação Principal
        self.tabs = QTabWidget()
        
        self.tab_vocal = TabVocal(self.engine, self.preset_mgr)
        self.tab_stems = TabStems(self.engine)
        self.tab_lyrics = TabLyrics(self.lyrics_mgr)
        self.tab_settings = TabSettings(self.engine)

        self.tabs.addTab(self.tab_vocal, "🎙  Voz e efeitos")
        self.tabs.addTab(self.tab_stems, "♪  Música e faixas")
        self.tabs.addTab(self.tab_lyrics, "✎  Letras")
        self.tabs.addTab(self.tab_settings, "⚙  Configurações")

        main_layout.addWidget(self.tabs)

        # Barra de Status Inferior
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Pronto para começar • Escolha seus dispositivos na aba Voz e efeitos")

    def closeEvent(self, event):
        """Para o motor de áudio e threads ao fechar a janela."""
        if not self.tab_lyrics.flush_pending_save():
            QMessageBox.warning(self, "Letra não salva",
                "Não foi possível salvar a letra. A janela permanecerá aberta para preservar seu texto.")
            event.ignore()
            return
        if hasattr(self, "engine"):
            self.engine.stop()
        worker = self.tab_stems.worker
        if worker and worker.isRunning():
            if not getattr(self, "_waiting_for_worker", False):
                self._waiting_for_worker = True
                worker.finished.connect(self.close)
            worker.cancel()
            event.ignore()
            return
        event.accept()
