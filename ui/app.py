"""
ui/app.py — SnippetLauncher management GUI (PyQt6)
"""

from __future__ import annotations
import sys
import os
import re

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QSplitter,
    QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QLabel, QLineEdit, QPushButton, QPlainTextEdit,
    QTextBrowser,
    QDialog, QDialogButtonBox, QFormLayout, QComboBox,
    QMessageBox, QFrame, QToolBar, QStatusBar,
    QMenu,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QFont, QKeySequence

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from db.models import init_db, get_session
import db.repository as repo
from paste.paster import copy_to_clipboard


# ---------------------------------------------------------------------------
# Add / Edit Snippet Dialog
# ---------------------------------------------------------------------------

class SnippetDialog(QDialog):
    def __init__(self, parent, session, snippet=None):
        super().__init__(parent)
        self.session = session
        self.snippet = snippet
        self.setWindowTitle("Edit Snippet" if snippet else "Add Snippet")
        self.setMinimumSize(580, 420)
        self._build_ui()
        if snippet:
            self._populate(snippet)

    def _build_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("e.g. Restart nginx")
        layout.addRow("Title *", self.title_edit)

        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.addItem("")
        for cat in repo.list_categories(self.session):
            self.category_combo.addItem(cat.name)
        self.category_combo.lineEdit().setPlaceholderText("Select or type a new category")
        layout.addRow("Category", self.category_combo)

        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("comma, separated, tags")
        layout.addRow("Tags", self.tags_edit)

        self.lang_combo = QComboBox()
        for lang in ["bash", "python", "sql", "javascript", "typescript",
                     "yaml", "toml", "json", "text"]:
            self.lang_combo.addItem(lang)
        layout.addRow("Language", self.lang_combo)

        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("Optional note about this snippet")
        layout.addRow("Description", self.desc_edit)

        layout.addRow(QLabel("Snippet *"))
        self.body_edit = QPlainTextEdit()
        self.body_edit.setPlaceholderText("Paste your command, code or URL here…")
        self.body_edit.setFont(QFont("Monospace", 10))
        self.body_edit.setMinimumHeight(140)
        layout.addRow(self.body_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _populate(self, snippet):
        self.title_edit.setText(snippet.title)
        self.body_edit.setPlainText(snippet.body)
        self.desc_edit.setText(snippet.description or "")
        if snippet.category:
            idx = self.category_combo.findText(snippet.category.name)
            if idx >= 0:
                self.category_combo.setCurrentIndex(idx)
            else:
                self.category_combo.setCurrentText(snippet.category.name)
        idx = self.lang_combo.findText(snippet.language or "bash")
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)
        self.tags_edit.setText(", ".join(t.name for t in snippet.tags))

    def _on_save(self):
        title = self.title_edit.text().strip()
        body  = self.body_edit.toPlainText().strip()
        if not title or not body:
            QMessageBox.warning(self, "Required fields", "Title and Body are required.")
            return
        category    = self.category_combo.currentText().strip() or None
        tags        = [t.strip() for t in self.tags_edit.text().split(",") if t.strip()]
        language    = self.lang_combo.currentText()
        description = self.desc_edit.text().strip()
        if self.snippet:
            repo.update_snippet(self.session, self.snippet.id,
                title=title, body=body, category=category,
                tags=tags, language=language, description=description)
        else:
            repo.create_snippet(self.session,
                title=title, body=body, category=category,
                tags=tags, language=language, description=description)
        self.accept()


# ---------------------------------------------------------------------------
# Category Dialog
# ---------------------------------------------------------------------------

class CategoryDialog(QDialog):
    def __init__(self, parent, session):
        super().__init__(parent)
        self.session = session
        self.setWindowTitle("Add Category")
        self.setMinimumWidth(360)
        self._build_ui()

    def _build_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. kubernetes")
        layout.addRow("Name *", self.name_edit)
        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("Optional description")
        layout.addRow("Description", self.desc_edit)
        self.colour_edit = QLineEdit("#5294e2")
        layout.addRow("Colour (hex)", self.colour_edit)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _on_save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Required", "Category name is required.")
            return
        repo.create_category(self.session, name=name,
            description=self.desc_edit.text().strip(),
            colour=self.colour_edit.text().strip())
        self.accept()


# ---------------------------------------------------------------------------
# Detail Pane
# ---------------------------------------------------------------------------

class DetailPane(QFrame):
    copy_requested        = pyqtSignal(object)
    copy_close_requested  = pyqtSignal(object)
    primary_requested     = pyqtSignal(object)
    edit_requested        = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.snippet = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)

        meta_layout = QHBoxLayout()
        self.title_label = QLabel()
        self.title_label.setFont(QFont(self.font().family(), -1, QFont.Weight.Bold))
        self.category_label = QLabel()
        self.category_label.setStyleSheet("color: grey;")
        meta_layout.addWidget(self.title_label)
        meta_layout.addWidget(self.category_label)
        meta_layout.addStretch()
        layout.addLayout(meta_layout)

        self.tags_label = QLabel()
        self.tags_label.setStyleSheet("color: grey; font-size: 11px;")
        layout.addWidget(self.tags_label)

        self.body_view = QTextBrowser()
        self.body_view.setOpenExternalLinks(True)
        self.body_view.setFont(QFont("Monospace", 10))
        self.body_view.setMinimumHeight(100)
        layout.addWidget(self.body_view)

        btn_layout = QHBoxLayout()
        self.edit_btn   = QPushButton("Edit  Ctrl+E")
        self.copy_btn   = QPushButton("Copy  Ctrl+C")
        self.middle_btn = QPushButton("Middle-click  Ctrl+M")
        self.paste_btn  = QPushButton("Copy && Close  Ctrl+↵")
        self.paste_btn.setDefault(True)

        for btn in (self.edit_btn, self.copy_btn, self.middle_btn, self.paste_btn):
            btn.setEnabled(False)
            btn_layout.addWidget(btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.edit_btn.clicked.connect(lambda: self.edit_requested.emit(self.snippet))
        self.copy_btn.clicked.connect(lambda: self.copy_requested.emit(self.snippet))
        self.middle_btn.clicked.connect(lambda: self.primary_requested.emit(self.snippet))
        self.paste_btn.clicked.connect(lambda: self.copy_close_requested.emit(self.snippet))

    _URL_RE = re.compile("https?://[^ \t\n<>]+", re.IGNORECASE)

    def _body_to_html(self, text: str) -> str:
        import html
        escaped = html.escape(text)
        def replace_url(m):
            url = m.group(0)
            return f'<a href="{url}" style="color:#5294e2;">{url}</a>'
        linked = self._URL_RE.sub(replace_url, escaped)
        return f'<pre style="font-family: monospace; white-space: pre-wrap; margin:0;">{linked}</pre>'

    def load(self, snippet):
        self.snippet = snippet
        enabled = snippet is not None
        for btn in (self.edit_btn, self.copy_btn, self.middle_btn, self.paste_btn):
            btn.setEnabled(enabled)
        if not snippet:
            self.title_label.setText("")
            self.category_label.setText("")
            self.tags_label.setText("")
            self.body_view.setPlainText("")
            return
        self.title_label.setText(snippet.title)
        self.category_label.setText(f"  {snippet.category.name if snippet.category else '—'}")
        self.tags_label.setText(", ".join(t.name for t in snippet.tags))
        self.body_view.setHtml(self._body_to_html(snippet.body))

    def _on_copy(self):
        if self.snippet:
            copy_to_clipboard(self.snippet.body)


# ---------------------------------------------------------------------------
# Main Window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):

    def __init__(self, session):
        super().__init__()
        self.session = session
        self.current_category = None
        self._snippets = []
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._refresh_snippets)
        self.setWindowTitle("Snippet Launcher")
        self.setMinimumSize(860, 540)
        self._build_ui()
        self._build_shortcuts()
        self._refresh_categories()
        self._refresh_snippets()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search snippets…")
        self.search_box.setMaximumWidth(300)
        self.search_box.textChanged.connect(self._on_search_changed)
        self.search_box.setClearButtonEnabled(True)
        toolbar.addWidget(self.search_box)
        toolbar.addSeparator()

        add_snippet_action = QAction("Add Snippet  Ctrl+N", self)
        add_snippet_action.setShortcut(QKeySequence("Ctrl+N"))
        add_snippet_action.triggered.connect(self._on_add_snippet)
        toolbar.addAction(add_snippet_action)

        add_cat_action = QAction("Add Category", self)
        add_cat_action.triggered.connect(self._on_add_category)
        toolbar.addAction(add_cat_action)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(splitter)

        # Sidebar
        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(4, 4, 4, 4)
        sidebar_layout.addWidget(QLabel("Categories"))
        self.cat_list = QListWidget()
        self.cat_list.currentRowChanged.connect(self._on_category_changed)
        sidebar_layout.addWidget(self.cat_list)
        del_cat_btn = QPushButton("Delete Category")
        del_cat_btn.clicked.connect(self._on_delete_category)
        sidebar_layout.addWidget(del_cat_btn)
        splitter.addWidget(sidebar)

        # Right pane
        right_splitter = QSplitter(Qt.Orientation.Vertical)

        self.snippet_table = QTableWidget()
        self.snippet_table.setColumnCount(3)
        self.snippet_table.setHorizontalHeaderLabels(["Title", "Tags", "Uses"])
        self.snippet_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self.snippet_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.snippet_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.snippet_table.verticalHeader().setVisible(False)
        self.snippet_table.setAlternatingRowColors(True)
        self.snippet_table.itemSelectionChanged.connect(
            lambda: self._on_snippet_selected(self.snippet_table.currentRow()))
        self.snippet_table.doubleClicked.connect(
            lambda: self._on_edit_snippet(self._current_snippet()))
        # Right-click context menu
        self.snippet_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.snippet_table.customContextMenuRequested.connect(self._on_context_menu)
        right_splitter.addWidget(self.snippet_table)

        self.detail = DetailPane()
        self.detail.copy_requested.connect(self._on_copy)
        self.detail.copy_close_requested.connect(self._on_copy_close)
        self.detail.primary_requested.connect(self._on_primary)
        self.detail.edit_requested.connect(self._on_edit_snippet)
        right_splitter.addWidget(self.detail)

        right_splitter.setStretchFactor(0, 2)
        right_splitter.setStretchFactor(1, 1)
        right_splitter.setHandleWidth(6)
        right_splitter.setStyleSheet("QSplitter::handle { background: palette(mid); border-radius: 3px; }")
        splitter.addWidget(right_splitter)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([180, 680])

        self.status = QStatusBar()
        self.setStatusBar(self.status)

    def _build_shortcuts(self):
        """Register keyboard shortcuts on the main window."""
        copy_sc = QAction(self)
        copy_sc.setShortcut(QKeySequence("Ctrl+C"))
        copy_sc.triggered.connect(lambda: self._on_copy(self._current_snippet()))
        self.addAction(copy_sc)

        primary_sc = QAction(self)
        primary_sc.setShortcut(QKeySequence("Ctrl+M"))
        primary_sc.triggered.connect(lambda: self._on_primary(self._current_snippet()))
        self.addAction(primary_sc)

        copy_close_sc = QAction(self)
        copy_close_sc.setShortcut(QKeySequence("Ctrl+Return"))
        copy_close_sc.triggered.connect(lambda: self._on_copy_close(self._current_snippet()))
        self.addAction(copy_close_sc)

        edit_sc = QAction(self)
        edit_sc.setShortcut(QKeySequence("Ctrl+E"))
        edit_sc.triggered.connect(lambda: self._on_edit_snippet(self._current_snippet()))
        self.addAction(edit_sc)

        delete_sc = QAction(self)
        delete_sc.setShortcut(QKeySequence("Delete"))
        delete_sc.triggered.connect(self._on_delete_snippet)
        self.addAction(delete_sc)

    # ------------------------------------------------------------------
    # Context menu
    # ------------------------------------------------------------------

    def _on_context_menu(self, pos):
        snippet = self._current_snippet()
        if not snippet:
            return

        menu = QMenu(self)

        edit_action = QAction("Edit snippet", self)
        edit_action.setShortcut(QKeySequence("Ctrl+E"))
        edit_action.triggered.connect(lambda: self._on_edit_snippet(snippet))
        menu.addAction(edit_action)

        menu.addSeparator()

        copy_action = QAction("Copy to Clipboard", self)
        copy_action.setShortcut(QKeySequence("Ctrl+C"))
        copy_action.triggered.connect(lambda: self._on_copy(snippet))
        menu.addAction(copy_action)

        middle_action = QAction("Middle-click Paste", self)
        middle_action.setShortcut(QKeySequence("Ctrl+M"))
        middle_action.triggered.connect(lambda: self._on_primary(snippet))
        menu.addAction(middle_action)

        close_action = QAction("Copy && Close", self)
        close_action.setShortcut(QKeySequence("Ctrl+Return"))
        close_action.triggered.connect(lambda: self._on_copy_close(snippet))
        menu.addAction(close_action)

        menu.addSeparator()

        delete_action = QAction("Delete snippet", self)
        delete_action.setShortcut(QKeySequence("Delete"))
        delete_action.triggered.connect(self._on_delete_snippet)
        menu.addAction(delete_action)

        menu.exec(self.snippet_table.viewport().mapToGlobal(pos))

    # ------------------------------------------------------------------
    # Data refresh
    # ------------------------------------------------------------------

    def _refresh_categories(self, restore_category: str | None = "__current__"):
        """Refresh the category list, optionally restoring a selection."""
        target = self.current_category if restore_category == "__current__" else restore_category

        self.cat_list.blockSignals(True)
        self.cat_list.clear()

        all_item = QListWidgetItem("All snippets")
        all_item.setData(Qt.ItemDataRole.UserRole, None)
        self.cat_list.addItem(all_item)

        restore_row = 0
        for i, cat in enumerate(repo.list_categories(self.session)):
            item = QListWidgetItem(f"{cat.name}  ({len(cat.snippets)})")
            item.setData(Qt.ItemDataRole.UserRole, cat.name)
            self.cat_list.addItem(item)
            if cat.name == target:
                restore_row = i + 1   # +1 for "All snippets" row

        self.cat_list.blockSignals(False)
        self.cat_list.setCurrentRow(restore_row)

    def _refresh_snippets(self):
        query    = self.search_box.text().strip()
        snippets = repo.search_snippets(
            self.session, query=query, category=self.current_category)
        self._snippets = snippets

        self.snippet_table.setRowCount(len(snippets))
        for row, s in enumerate(snippets):
            tags = ", ".join(t.name for t in s.tags)
            title_item = QTableWidgetItem(s.title)
            tags_item  = QTableWidgetItem(tags)
            uses_item  = QTableWidgetItem(str(s.use_count))

            # Tooltip: show description if set, otherwise first line of body
            tooltip = s.description.strip() if s.description and s.description.strip() \
                      else s.body.splitlines()[0][:100]
            for item in (title_item, tags_item, uses_item):
                item.setToolTip(tooltip)

            self.snippet_table.setItem(row, 0, title_item)
            self.snippet_table.setItem(row, 1, tags_item)
            self.snippet_table.setItem(row, 2, uses_item)

        self.snippet_table.setColumnWidth(1, 160)
        self.snippet_table.setColumnWidth(2, 45)

        self.status.showMessage(
            f"{len(snippets)} snippet{'s' if len(snippets) != 1 else ''}")

        if snippets:
            self.snippet_table.selectRow(0)
            self.detail.load(snippets[0])
        else:
            self.detail.load(None)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_search_changed(self, _text):
        self._search_timer.start(250)

    def _on_category_changed(self, row):
        if row < 0:
            return
        item = self.cat_list.item(row)
        self.current_category = item.data(Qt.ItemDataRole.UserRole)
        self._refresh_snippets()

    def _on_snippet_selected(self, row):
        if row < 0 or row >= len(self._snippets):
            self.detail.load(None)
            return
        self.detail.load(self._snippets[row])

    def _current_snippet(self):
        row = self.snippet_table.currentRow()
        if row < 0 or row >= len(self._snippets):
            return None
        return self._snippets[row]

    def _on_add_snippet(self):
        dlg = SnippetDialog(self, self.session)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._refresh_categories()
            self._refresh_snippets()

    def _on_edit_snippet(self, snippet=None):
        snippet = snippet or self._current_snippet()
        if not snippet:
            return
        dlg = SnippetDialog(self, self.session, snippet=snippet)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.session.expire_all()
            self._refresh_categories()
            self._refresh_snippets()

    def _on_delete_snippet(self):
        snippet = self._current_snippet()
        if not snippet:
            return
        reply = QMessageBox.question(
            self, "Delete snippet", f"Delete '{snippet.title}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            repo.delete_snippet(self.session, snippet.id)
            self._refresh_categories()   # restores current category
            self._refresh_snippets()

    def _on_add_category(self):
        dlg = CategoryDialog(self, self.session)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._refresh_categories()

    def _on_delete_category(self):
        item = self.cat_list.currentItem()
        if not item:
            return
        cat_name = item.data(Qt.ItemDataRole.UserRole)
        if not cat_name:
            return
        reply = QMessageBox.question(
            self, "Delete category",
            f"Delete category '{cat_name}'?\nSnippets will become uncategorised.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            repo.delete_category(self.session, cat_name)
            self.current_category = None
            self._refresh_categories(restore_category=None)
            self._refresh_snippets()

    def _on_copy(self, snippet=None):
        snippet = snippet or self._current_snippet()
        if not snippet:
            return
        repo.record_use(self.session, snippet.id)
        copy_to_clipboard(snippet.body)
        self.status.showMessage(f"✓ Copied: {snippet.title}", 3000)
        self._refresh_snippets()

    def _on_primary(self, snippet=None):
        snippet = snippet or self._current_snippet()
        if not snippet:
            return
        from paste.paster import copy_to_primary
        repo.record_use(self.session, snippet.id)
        result = copy_to_primary(snippet.body)
        if result.success:
            self.status.showMessage("✓ Ready — middle-click to paste", 3000)
            self.showMinimized()
        else:
            self.status.showMessage(f"✗ {result.message}", 5000)
        self._refresh_snippets()

    def _on_copy_close(self, snippet=None):
        snippet = snippet or self._current_snippet()
        if not snippet:
            return
        repo.record_use(self.session, snippet.id)
        result = copy_to_clipboard(snippet.body)
        if result.success:
            self.showMinimized()
        else:
            self.status.showMessage(f"✗ {result.message}", 5000)
        self._refresh_snippets()


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def run():
    engine  = init_db()
    session = get_session(engine)
    app = QApplication(sys.argv)
    app.setApplicationName("SnippetLauncher")
    app.setApplicationDisplayName("Snippet Launcher")

    # Set window icon from theme (matches .desktop file Icon= entry)
    from PyQt6.QtGui import QIcon
    icon = QIcon.fromTheme("format-text-code")
    if icon.isNull():
        icon = QIcon.fromTheme("accessories-text-editor")
    app.setWindowIcon(icon)

    win = MainWindow(session)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run()
