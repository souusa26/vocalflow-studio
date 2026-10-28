"""Tema visual escuro para uso em estúdio."""

DARK_STUDIO_QSS = """
QMainWindow, QDialog { background: #10131b; color: #edf1fa; font-family: "Segoe UI", Arial; font-size: 13px; }
QWidget { background-color: transparent; color: #edf1fa; }
QWidget#central { background-color: #10131b; }
QLabel#brand { color: #f5f7ff; font-size: 22px; font-weight: 700; }
QLabel#brandAccent { color: #8eafff; font-size: 12px; font-weight: 700; letter-spacing: 2px; }
QLabel#subtitle, QLabel#sectionHint { color: #a7b1c6; font-size: 12px; }
QLabel#pageTitle { color: #f5f7ff; font-size: 19px; font-weight: 700; }
QLabel#pageSubtitle, QLabel#mutedText, QLabel#sectionIntro { color: #a7b1c6; font-size: 12px; }
QLabel#sectionTitle { color: #bfcfff; font-size: 13px; font-weight: 700; }
QTabWidget::pane { border: 1px solid #2a3244; border-radius: 10px; background: #161b26; top: -1px; }
QTabBar::tab { color: #aeb9cb; background: #1a2030; padding: 11px 25px; margin-right: 5px; border: 1px solid #2b3447; border-top-left-radius: 8px; border-top-right-radius: 8px; font-weight: 600; }
QTabBar::tab:selected { background: #252e43; color: #eef3ff; border-bottom: 3px solid #8ca6ff; }
QTabBar::tab:hover:!selected { background: #252d3c; color: #ffffff; }
QGroupBox { background-color: #1d2432; border: 1px solid #313c50; border-radius: 10px; margin-top: 14px; padding-top: 19px; color: #bfcfff; font-weight: 700; }
QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; left: 12px; padding: 0 6px; background-color: #1d2432; }
QPushButton { background: #303a4e; color: #f6f8ff; border: 1px solid #43516c; border-radius: 7px; padding: 7px 13px; font-weight: 600; }
QPushButton:hover { background: #3c4a64; border-color: #8ca6ff; }
QPushButton:pressed { background: #263249; }
QPushButton:disabled { background: #202633; color: #738095; border-color: #30394a; }
QPushButton#btn_primary, QPushButton#btn_live_off { background: #9ab0ff; color: #101628; border: 1px solid #abc1ff; font-weight: 700; }
QPushButton#btn_primary:hover, QPushButton#btn_live_off:hover { background: #b7c7ff; }
QPushButton#btn_live_on { background: #45d6ae; color: #10251f; border: 1px solid #63e9c2; font-weight: 700; }
QSlider::groove:horizontal { height: 5px; background: #394355; border-radius: 2px; }
QSlider::sub-page:horizontal { background: #93aaff; border-radius: 2px; }
QSlider::handle:horizontal { background: #f6f8ff; border: 2px solid #93aaff; width: 14px; margin: -6px 0; border-radius: 8px; }
QSlider::handle:horizontal:hover { background: #b5c3ff; }
QComboBox, QLineEdit, QTextEdit, QPlainTextEdit { background-color: #131a27; border: 1px solid #3b485f; border-radius: 7px; padding: 7px 10px; color: #f2f5ff; selection-background-color: #596fbe; }
QComboBox:hover, QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus { border: 1px solid #93aaff; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView { background: #20293a; border: 1px solid #495671; selection-background-color: #596fbe; color: #ffffff; }
QCheckBox { spacing: 8px; color: #edf1fa; }
QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px; border: 1px solid #73809a; background: #141b28; }
QCheckBox::indicator:checked { background: #93aaff; border-color: #b5c3ff; }
QScrollBar:vertical { background: #171d29; width: 10px; border-radius: 5px; }
QScrollBar::handle:vertical { background: #526079; min-height: 28px; border-radius: 5px; }
QScrollBar::handle:vertical:hover { background: #93aaff; }
QProgressBar { background: #131a27; border: 1px solid #3b485f; border-radius: 6px; text-align: center; color: #f7f9ff; }
QProgressBar::chunk { background: #8ca6ff; border-radius: 5px; }
QListWidget { background: #131a27; border: 1px solid #3b485f; border-radius: 7px; padding: 4px; }
QListWidget::item { padding: 9px 10px; border-radius: 5px; color: #edf1fa; }
QListWidget::item:selected { background: #3a4b74; color: #ffffff; }
QListWidget::item:hover:!selected { background: #29344a; }
QStatusBar { color: #aeb9cb; background-color: #10131b; }
"""
