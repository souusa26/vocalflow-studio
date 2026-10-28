"""
Aba do Bloco de Notas para Letras e Rimas (Tab Lyrics).
Permite escrever, organizar, pesquisar letras com salvamento automático (autosave),
contadores de versos e palavras, e exportação direta para arquivos de texto.
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QListWidget, QListWidgetItem, QMessageBox,
    QFileDialog, QSplitter, QFrame
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from app.lyrics.manager import LyricsManager

class TabLyrics(QWidget):
    def __init__(self, lyrics_manager: LyricsManager, parent=None):
        super().__init__(parent)
        self.lyrics_mgr = lyrics_manager
        self.active_lyric_id = None
        self._is_loading = False

        self._dirty = False
        self.autosave_timer = QTimer(self)
        self.autosave_timer.setSingleShot(True)
        self.autosave_timer.setInterval(600)
        self.autosave_timer.timeout.connect(self._perform_autosave)
        self._init_ui()
        self._refresh_list()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # -------------------------------------------------------------
        # PAINEL LATERAL ESQUERDO: LISTA DE LETRAS E BUSCA
        # -------------------------------------------------------------
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(8)

        # Botão Nova Letra
        btn_new = QPushButton("✍️ + Nova Letra")
        btn_new.setObjectName("btn_primary")
        btn_new.setFixedHeight(36)
        btn_new.clicked.connect(self._create_new_lyric)
        left_layout.addWidget(btn_new)

        # Campo de Pesquisa
        self.edit_search = QLineEdit()
        self.edit_search.setPlaceholderText("🔍 Buscar letra por título...")
        self.edit_search.textChanged.connect(self._refresh_list)
        left_layout.addWidget(self.edit_search)

        # Lista de Letras
        self.list_lyrics = QListWidget()
        self.list_lyrics.itemSelectionChanged.connect(self._on_selection_changed)
        left_layout.addWidget(self.list_lyrics)

        left_panel.setMinimumWidth(240)
        splitter.addWidget(left_panel)

        # -------------------------------------------------------------
        # PAINEL PRINCIPAL DIREITO: EDITOR DE TEXTO E CONTROLES
        # -------------------------------------------------------------
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(10)

        # Cabeçalho: Título da Letra e Ações
        header_row = QHBoxLayout()
        self.edit_title = QLineEdit()
        self.edit_title.setPlaceholderText("Título da Letra...")
        self.edit_title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 8px;")
        self.edit_title.textChanged.connect(self._on_content_changed)
        header_row.addWidget(self.edit_title, stretch=1)

        btn_export = QPushButton("📤 Exportar (.txt)")
        btn_export.clicked.connect(self._export_txt)
        header_row.addWidget(btn_export)

        btn_delete = QPushButton("🗑️ Excluir")
        btn_delete.clicked.connect(self._delete_current_lyric)
        header_row.addWidget(btn_delete)

        right_layout.addLayout(header_row)

        # Área de Escrita de Letra
        self.text_editor = QTextEdit()
        font = QFont("Consolas", 12)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.text_editor.setFont(font)
        self.text_editor.setPlaceholderText("Escreva aqui suas barras, versos e rimas...\nO texto é salvo automaticamente.")
        self.text_editor.textChanged.connect(self._on_content_changed)
        right_layout.addWidget(self.text_editor)

        # Barra de Status Inferior: Autosave badge + contadores
        status_row = QHBoxLayout()

        self.lbl_autosave = QLabel("● Salvo")
        self.lbl_autosave.setStyleSheet("color: #00e676; font-weight: bold; font-size: 11px;")
        status_row.addWidget(self.lbl_autosave)

        status_row.addStretch()

        self.lbl_stats = QLabel("0 versos | 0 palavras")
        self.lbl_stats.setStyleSheet("color: #9e9e9e; font-size: 11px;")
        status_row.addWidget(self.lbl_stats)

        right_layout.addLayout(status_row)
        splitter.addWidget(right_panel)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter)

    # -------------------------------------------------------------
    # OPERAÇÕES DE LISTA E SELEÇÃO
    # -------------------------------------------------------------
    def _refresh_list(self):
        query = self.edit_search.text()
        lyrics = self.lyrics_mgr.list_lyrics(query)

        self.list_lyrics.blockSignals(True)
        self.list_lyrics.clear()

        for item in lyrics:
            list_item = QListWidgetItem(f"📝 {item['title']}")
            list_item.setData(Qt.ItemDataRole.UserRole, item["id"])
            self.list_lyrics.addItem(list_item)

        self.list_lyrics.blockSignals(False)

        # Se houver itens e nenhum ativo, seleciona o primeiro
        if self.list_lyrics.count() > 0 and self.active_lyric_id is None:
            self.list_lyrics.setCurrentRow(0)

    def _on_selection_changed(self):
        current_item = self.list_lyrics.currentItem()
        if not current_item:
            return

        lyric_id = current_item.data(Qt.ItemDataRole.UserRole)
        if lyric_id == self.active_lyric_id:
            return
        if lyric_id != self.active_lyric_id and not self.flush_pending_save():
            self.list_lyrics.blockSignals(True)
            for index in range(self.list_lyrics.count()):
                item = self.list_lyrics.item(index)
                if item.data(Qt.ItemDataRole.UserRole) == self.active_lyric_id:
                    self.list_lyrics.setCurrentItem(item)
                    break
            self.list_lyrics.blockSignals(False)
            return
        data = self.lyrics_mgr.get_lyric(lyric_id)
        if not data:
            return

        self._is_loading = True
        self.active_lyric_id = lyric_id
        self.edit_title.setText(data.get("title", ""))
        self.text_editor.setPlainText(data.get("content", ""))
        self.lbl_autosave.setText("● Salvo")
        self.lbl_autosave.setStyleSheet("color: #00e676; font-weight: bold; font-size: 11px;")
        self._update_stats()
        self._is_loading = False

    def _create_new_lyric(self):
        if not self.flush_pending_save():
            return
        try:
            data = self.lyrics_mgr.create_lyric("Nova Letra de Rap", "")
        except OSError as exc:
            QMessageBox.warning(self, "Letras", f"Não foi possível criar a letra: {exc}")
            return
        self._refresh_list()
        
        # Seleciona o novo item
        for i in range(self.list_lyrics.count()):
            item = self.list_lyrics.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == data["id"]:
                self.list_lyrics.setCurrentItem(item)
                break
        self.edit_title.setFocus()
        self.edit_title.selectAll()

    def _on_content_changed(self):
        if self._is_loading:
            return
        self._dirty = True
        self.lbl_autosave.setText("● Salvando...")
        self.lbl_autosave.setStyleSheet("color: #ffb300; font-weight: bold; font-size: 11px;")
        self._update_stats()
        self.autosave_timer.start()

    def flush_pending_save(self):
        self.autosave_timer.stop()
        return self._perform_autosave() if self._dirty else True

    def _perform_autosave(self):
        if not self.active_lyric_id:
            return True

        title = self.edit_title.text().strip() or "Sem Título"
        content = self.text_editor.toPlainText()

        if not self.lyrics_mgr.update_lyric(self.active_lyric_id, title=title, content=content):
            self.lbl_autosave.setText("● Falha ao salvar — mantenha esta letra aberta")
            self.lbl_autosave.setStyleSheet("color: #ff5252; font-weight: bold;")
            return False
        self._dirty = False
        self.lbl_autosave.setText("● Salvo")
        self.lbl_autosave.setStyleSheet("color: #00e676; font-weight: bold; font-size: 11px;")

        # Atualiza título na lista lateral
        current_item = self.list_lyrics.currentItem()
        if current_item and current_item.data(Qt.ItemDataRole.UserRole) == self.active_lyric_id:
            current_item.setText(f"📝 {title}")

        return True

    def _update_stats(self):
        text = self.text_editor.toPlainText()
        lines = [line for line in text.splitlines() if line.strip()]
        words = text.split()
        self.lbl_stats.setText(f"{len(lines)} versos | {len(words)} palavras")

    def _delete_current_lyric(self):
        if not self.active_lyric_id:
            return

        confirm = QMessageBox.question(
            self, "Confirmar Exclusão de Letra",
            f"Deseja realmente excluir a letra '{self.edit_title.text()}'?\nEsta ação não poderá ser desfeita.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            if not self.lyrics_mgr.delete_lyric(self.active_lyric_id):
                QMessageBox.warning(self, "Letras", "Não foi possível excluir a letra.")
                return
            self.autosave_timer.stop()
            self._dirty = False
            self.active_lyric_id = None
            self._refresh_list()
            if self.list_lyrics.count() == 0:
                self._is_loading = True
                self.edit_title.clear()
                self.text_editor.clear()
                self._is_loading = False

    def _export_txt(self):
        if not self.flush_pending_save():
            return
        if not self.active_lyric_id:
            return
        title = self.edit_title.text().strip() or "letra"
        safe_title = "".join(c for c in title if c.isalnum() or c in (" ", "-", "_")).strip()
        path, _ = QFileDialog.getSaveFileName(self, "Exportar Letra", f"{safe_title}.txt", "Arquivos de Texto (*.txt)")
        if path:
            if self.lyrics_mgr.export_lyric_txt(self.active_lyric_id, Path(path)):
                QMessageBox.information(self, "Exportado", f"Letra exportada com sucesso para:\n{path}")
