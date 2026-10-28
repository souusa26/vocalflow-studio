"""
Widget de Canal de Stem (Stem Strip Widget).
Representa uma faixa isolada no Stem Player com controles de Mute, Solo, Volume e status.
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QSlider
from PyQt6.QtCore import Qt, pyqtSignal

class StemStripWidget(QWidget):
    mute_toggled = pyqtSignal(str, bool)   # stem_name, mute_state
    solo_toggled = pyqtSignal(str, bool)   # stem_name, solo_state
    volume_changed = pyqtSignal(str, float)# stem_name, volume

    def __init__(self, stem_name: str, display_title: str, icon_symbol: str = "🎵", parent=None):
        super().__init__(parent)
        self.stem_name = stem_name
        self.display_title = display_title

        self.setStyleSheet("""
            QWidget {
                background-color: #1f2129;
                border: 1px solid #2e313d;
                border-radius: 6px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        # 1. Título e Ícone da Faixa
        lbl_icon = QLabel(icon_symbol)
        lbl_icon.setStyleSheet("font-size: 18px; border: none; background: transparent;")
        lbl_icon.setFixedWidth(28)
        layout.addWidget(lbl_icon)

        self.lbl_title = QLabel(display_title)
        self.lbl_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #ffffff; border: none; background: transparent;")
        self.lbl_title.setFixedWidth(130)
        layout.addWidget(self.lbl_title)

        # 2. Botão Mute (M)
        self.btn_mute = QPushButton("M")
        self.btn_mute.setCheckable(True)
        self.btn_mute.setFixedSize(32, 28)
        self.btn_mute.setStyleSheet("""
            QPushButton {
                background-color: #2b2d38;
                color: #bdbdbd;
                font-weight: bold;
                border: 1px solid #444759;
                border-radius: 4px;
            }
            QPushButton:checked {
                background-color: #ff9100;
                color: #000000;
                border-color: #ff6d00;
            }
        """)
        self.btn_mute.toggled.connect(self._on_mute)
        layout.addWidget(self.btn_mute)

        # 3. Botão Solo (S)
        self.btn_solo = QPushButton("S")
        self.btn_solo.setCheckable(True)
        self.btn_solo.setFixedSize(32, 28)
        self.btn_solo.setStyleSheet("""
            QPushButton {
                background-color: #2b2d38;
                color: #bdbdbd;
                font-weight: bold;
                border: 1px solid #444759;
                border-radius: 4px;
            }
            QPushButton:checked {
                background-color: #00e5ff;
                color: #000000;
                border-color: #00b0ff;
            }
        """)
        self.btn_solo.toggled.connect(self._on_solo)
        layout.addWidget(self.btn_solo)

        # 4. Slider de Volume
        self.slider_vol = QSlider(Qt.Orientation.Horizontal)
        self.slider_vol.setRange(0, 150)
        self.slider_vol.setValue(100)
        self.slider_vol.valueChanged.connect(self._on_volume)
        layout.addWidget(self.slider_vol)

        # 5. Label de Leitura de Volume (dB)
        self.lbl_vol_db = QLabel("0.0 dB")
        self.lbl_vol_db.setFixedWidth(55)
        self.lbl_vol_db.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_vol_db.setStyleSheet("font-size: 11px; color: #9e9e9e; border: none; background: transparent;")
        layout.addWidget(self.lbl_vol_db)

    def _on_mute(self, checked: bool):
        self.mute_toggled.emit(self.stem_name, checked)

    def _on_solo(self, checked: bool):
        self.solo_toggled.emit(self.stem_name, checked)

    def _on_volume(self, val: int):
        linear = val / 100.0
        if linear <= 0.001:
            self.lbl_vol_db.setText("-∞ dB")
        else:
            db = 20.0 * (val / 100.0 - 1.0) * 1.5
            self.lbl_vol_db.setText(f"{db:+.1f} dB")
        self.volume_changed.emit(self.stem_name, linear)

    def set_muted(self, muted: bool):
        self.btn_mute.setChecked(muted)

    def set_soloed(self, soloed: bool):
        self.btn_solo.setChecked(soloed)

    def set_volume_val(self, val: float):
        self.slider_vol.setValue(int(val * 100))
