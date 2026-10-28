"""
Widget de Medidor de Nível de Áudio (VU Meter em Tempo Real).
Exibe Peak, RMS, escala em dBFS e LED indicador de clipagem (distorção).
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QLinearGradient
from PyQt6.QtCore import Qt, QRectF

class VUMeter(QWidget):
    def __init__(self, parent=None, is_horizontal: bool = True):
        super().__init__(parent)
        self.is_horizontal = is_horizontal
        self.peak_db = -60.0
        self.rms_db = -60.0
        self.is_clipped = False

        if is_horizontal:
            self.setFixedHeight(22)
            self.setMinimumWidth(120)
        else:
            self.setFixedWidth(24)
            self.setMinimumHeight(140)

    def set_levels(self, peak_db: float, rms_db: float, is_clipped: bool = False):
        self.peak_db = max(-60.0, min(3.0, float(peak_db)))
        self.rms_db = max(-60.0, min(3.0, float(rms_db)))
        self.is_clipped = bool(is_clipped)
        self.update()

    def _db_to_ratio(self, db: float) -> float:
        # Mapeia -60 dB a 0 dB para 0.0 a 1.0
        if db <= -60.0:
            return 0.0
        if db >= 0.0:
            return 1.0
        return (db + 60.0) / 60.0

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Fundo do medidor
        painter.fillRect(0, 0, w, h, QColor("#14151a"))

        # Borda sutil
        painter.setPen(QColor("#2d2f38"))
        painter.drawRect(0, 0, w - 1, h - 1)

        clip_box_size = 14
        bar_w = w - clip_box_size - 6 if self.is_horizontal else w - 4

        # Gradiente do medidor (Verde -> Amarelo -> Vermelho)
        grad = QLinearGradient(0, 0, bar_w if self.is_horizontal else 0, h if not self.is_horizontal else 0)
        grad.setColorAt(0.0, QColor("#00e676"))   # Verde suave
        grad.setColorAt(0.70, QColor("#ffeb3b"))  # Amarelo a -18dB
        grad.setColorAt(0.90, QColor("#ff9800"))  # Laranja a -6dB
        grad.setColorAt(1.0, QColor("#ff1744"))   # Vermelho em 0dB

        # Barra RMS
        rms_ratio = self._db_to_ratio(self.rms_db)
        if self.is_horizontal:
            rms_width = int(bar_w * rms_ratio)
            if rms_width > 0:
                painter.fillRect(2, 2, rms_width, h - 4, grad)

            # Indicador de Pico (Linha Branca)
            peak_ratio = self._db_to_ratio(self.peak_db)
            peak_x = int(bar_w * peak_ratio)
            if peak_x > 2:
                painter.setPen(QPen(QColor("#ffffff"), 2))
                painter.drawLine(peak_x, 2, peak_x, h - 3)

            # LED indicador de Clip
            clip_x = w - clip_box_size - 3
            clip_y = (h - clip_box_size) // 2
            clip_color = QColor("#ff1744") if (self.is_clipped or self.peak_db >= -0.1) else QColor("#3a151b")
            painter.setBrush(clip_color)
            painter.setPen(QPen(QColor("#ff5252") if self.is_clipped else QColor("#220b0e"), 1))
            painter.drawRoundedRect(clip_x, clip_y, clip_box_size, clip_box_size, 3, 3)

        else:
            # Vertical
            rms_height = int((h - 20) * rms_ratio)
            y_start = h - 2 - rms_height
            if rms_height > 0:
                painter.fillRect(2, y_start, w - 4, rms_height, grad)

            # LED Clip no topo
            clip_color = QColor("#ff1744") if (self.is_clipped or self.peak_db >= -0.1) else QColor("#3a151b")
            painter.setBrush(clip_color)
            painter.drawRoundedRect(3, 3, w - 6, 10, 2, 2)
