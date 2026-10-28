"""
Folha de Estilos QSS (Tema Dark Studio / DAW Moderna) para o VocalFlow Studio.
Estilo com contraste de precisão, indicadores visuais neon e ergonomia de estúdio.
"""

DARK_STUDIO_QSS = """
QMainWindow, QDialog {
    background-color: #121316;
    color: #e0e0e0;
    font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
    font-size: 13px;
}

QWidget {
    background-color: #121316;
    color: #e0e0e0;
}

/* Abas Principais */
QTabWidget::pane {
    border: 1px solid #282a30;
    background-color: #18191d;
    border-radius: 6px;
    top: -1px;
}

QTabBar::tab {
    background: #1c1d22;
    color: #9e9e9e;
    padding: 10px 22px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: bold;
    border: 1px solid #25262c;
    border-bottom: none;
}

QTabBar::tab:selected {
    background: #252730;
    color: #00e5ff;
    border-bottom: 2px solid #00e5ff;
}

QTabBar::tab:hover:!selected {
    background: #22242b;
    color: #ffffff;
}

/* Caixas de Grupo (Cards de Efeitos e Seções) */
QGroupBox {
    background-color: #1a1b20;
    border: 1px solid #2d2f38;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 18px;
    font-weight: bold;
    color: #00e5ff;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    background-color: #1a1b20;
}

/* Botões */
QPushButton {
    background-color: #262832;
    color: #ffffff;
    border: 1px solid #3d404f;
    border-radius: 5px;
    padding: 7px 14px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #323542;
    border-color: #00e5ff;
}

QPushButton:pressed {
    background-color: #1b1c24;
}

QPushButton:disabled {
    background-color: #18191d;
    color: #555866;
    border-color: #222329;
}

/* Botão de Destaque / Ação Primária */
QPushButton#btn_primary {
    background-color: #00b0ff;
    color: #000000;
    border: none;
}

QPushButton#btn_primary:hover {
    background-color: #40c4ff;
}

/* Botão Ao Vivo (Gravação/DSP Ativo) */
QPushButton#btn_live_on {
    background-color: #00e676;
    color: #000000;
    font-weight: bold;
    border: 1px solid #00c853;
}

QPushButton#btn_live_off {
    background-color: #2b2d38;
    color: #e0e0e0;
    border: 1px solid #424656;
}

/* Sliders (Faders) */
QSlider::groove:horizontal {
    height: 6px;
    background: #252732;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #00e5ff;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #ffffff;
    border: 2px solid #00e5ff;
    width: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 7px;
}

QSlider::handle:horizontal:hover {
    background: #00e5ff;
}

/* Caixas de Seleção (Combobox) */
QComboBox {
    background-color: #22242d;
    border: 1px solid #363946;
    border-radius: 5px;
    padding: 5px 10px;
    color: #ffffff;
}

QComboBox:hover {
    border-color: #00e5ff;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox QAbstractItemView {
    background-color: #1c1d24;
    border: 1px solid #3d404f;
    selection-background-color: #00b0ff;
    selection-color: #000000;
    color: #ffffff;
}

/* Campos de Texto */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #18191f;
    border: 1px solid #2e313d;
    border-radius: 5px;
    padding: 6px 10px;
    color: #f0f0f0;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #00e5ff;
}

/* Checkboxes */
QCheckBox {
    spacing: 8px;
    color: #e0e0e0;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 1px solid #444759;
    background-color: #1c1d24;
}

QCheckBox::indicator:checked {
    background-color: #00e5ff;
    border-color: #00b0ff;
}

/* Barras de Rolagem */
QScrollBar:vertical {
    border: none;
    background: #14151a;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background: #333644;
    min-height: 25px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #00e5ff;
}

/* Barras de Progresso */
QProgressBar {
    background-color: #1c1d24;
    border: 1px solid #333645;
    border-radius: 5px;
    text-align: center;
    color: #ffffff;
    font-weight: bold;
}

QProgressBar::chunk {
    background-color: #00e5ff;
    border-radius: 4px;
}

/* Listas */
QListWidget {
    background-color: #18191f;
    border: 1px solid #2e313d;
    border-radius: 6px;
    padding: 4px;
}

QListWidget::item {
    padding: 8px 10px;
    border-radius: 4px;
    color: #e0e0e0;
}

QListWidget::item:selected {
    background-color: #2b2e3b;
    color: #00e5ff;
    font-weight: bold;
}

QListWidget::item:hover:!selected {
    background-color: #20222a;
}
"""
