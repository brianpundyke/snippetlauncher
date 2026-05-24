"""
launcher/popup.py — Keyboard-driven snippet picker popup (PyQt6)

A minimal floating window that:
- Appears centred on screen
- Immediately has keyboard focus
- Filters snippets as you type
- Enter selects, Escape dismisses
- Works natively on Wayland + KDE Plasma
"""

from __future__ import annotations
import sys
import os

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLineEdit,
    QListWidget, QListWidgetItem, QLabel, QHBoxLayout,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QKeyEvent

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from db.models import init_db, get_session
import db.repository as repo
from paste.paster import copy_to_clipboard, copy_to_primary


# ---------------------------------------------------------------------------
# Popup window
# ---------------------------------------------------------------------------

class LauncherPopup(QWidget):

    def __init__(self, snippets, mode="clipboard"):
        """
        mode: "clipboard" | "primary"
        """
        super().__init__()
        self._all_snippets = snippets
        self._mode = mode
        self._build_ui()
        self._populate(snippets)
        self._apply_style()

    def _build_ui(self):
        self.setWindowTitle("Snippet Launcher")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setMinimumWidth(540)
        self.setMaximumHeight(440)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Header
        header = QHBoxLayout()
        icon_label = QLabel("⌨")
        icon_label.setStyleSheet("font-size: 18px; padding-right: 4px;")
        title_label = QLabel("Snippet Launcher")
        title_label.setStyleSheet("font-weight: bold;")
        hint_label = QLabel("Enter to copy · Double-click for middle-click paste · Esc to close")
        hint_label.setStyleSheet("color: grey; font-size: 11px;")
        header.addWidget(icon_label)
        header.addWidget(title_label)
        header.addStretch()
        header.addWidget(hint_label)
        layout.addLayout(header)

        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Type to filter snippets…")
        self.search_box.textChanged.connect(self._on_filter)
        self.search_box.setFixedHeight(34)
        layout.addWidget(self.search_box)

        # Snippet list
        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.itemActivated.connect(self._on_activate)
        self.list_widget.itemDoubleClicked.connect(self._on_double_click)
        self.list_widget.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        layout.addWidget(self.list_widget)

        # Status line
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: grey; font-size: 11px;")
        layout.addWidget(self.status_label)

        # Key handling on search box
        self.search_box.installEventFilter(self)

    def _apply_style(self):
        self.setStyleSheet("""
            QWidget {
                border-radius: 8px;
            }
            QLineEdit {
                border: 1px solid palette(mid);
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 13px;
            }
            QListWidget {
                border: 1px solid palette(mid);
                border-radius: 4px;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 5px 8px;
            }
            QListWidget::item:selected {
                background: palette(highlight);
                color: palette(highlighted-text);
            }
        """)

    def _populate(self, snippets):
        self.list_widget.clear()
        for s in snippets:
            cat  = s.category.name if s.category else "—"
            tags = ", ".join(t.name for t in s.tags) if s.tags else ""
            tag_part = f"  [{tags}]" if tags else ""
            label = f"{s.title}   {cat}{tag_part}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, s)
            # Right-align category in a dimmer colour via font
            item.setToolTip(s.body[:120] + ("…" if len(s.body) > 120 else ""))
            self.list_widget.addItem(item)

        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

        count = self.list_widget.count()
        self.status_label.setText(
            f"{count} snippet{'s' if count != 1 else ''}"
        )

    def _on_filter(self, text):
        query = text.strip().lower()
        if not query:
            self._populate(self._all_snippets)
            return

        filtered = [
            s for s in self._all_snippets
            if query in s.title.lower()
            or query in s.body.lower()
            or query in (s.category.name.lower() if s.category else "")
            or any(query in t.name.lower() for t in s.tags)
        ]
        self._populate(filtered)

    def _on_activate(self, item):
        snippet = item.data(Qt.ItemDataRole.UserRole)
        if not snippet:
            return
        self._dispatch(snippet, mode="clipboard")

    def _on_double_click(self, item):
        snippet = item.data(Qt.ItemDataRole.UserRole)
        if not snippet:
            return
        self._dispatch(snippet, mode="primary")

    def _dispatch(self, snippet, mode: str | None = None):
        """Copy snippet and close. mode overrides instance default."""
        effective_mode = mode or self._mode
        if effective_mode == "primary":
            copy_to_primary(snippet.body)
        else:
            copy_to_clipboard(snippet.body)

        # Record usage
        try:
            engine  = init_db()
            session = get_session(engine)
            repo.record_use(session, snippet.id)
        except Exception:
            pass

        self.close()

    # ------------------------------------------------------------------
    # Keyboard navigation
    # ------------------------------------------------------------------

    def eventFilter(self, obj, event):
        """
        Intercept key events on the search box so arrow keys
        move the list selection without losing text focus.
        """
        if obj is self.search_box and isinstance(event, QKeyEvent):
            key = event.key()

            if key == Qt.Key.Key_Escape:
                self.close()
                return True

            if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
                current = self.list_widget.currentItem()
                if current:
                    self._dispatch(current.data(Qt.ItemDataRole.UserRole), mode="clipboard")
                return True

            if key == Qt.Key.Key_Down:
                row = self.list_widget.currentRow()
                if row < self.list_widget.count() - 1:
                    self.list_widget.setCurrentRow(row + 1)
                return True

            if key == Qt.Key.Key_Up:
                row = self.list_widget.currentRow()
                if row > 0:
                    self.list_widget.setCurrentRow(row - 1)
                return True

        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()

    # ------------------------------------------------------------------
    # Show centred with focus
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        """Ensure the Qt event loop exits when window is closed."""
        QApplication.instance().quit()
        event.accept()

    def show_centred(self):
        screen = QApplication.primaryScreen().geometry()
        self.adjustSize()
        x = (screen.width()  - self.width())  // 2
        y = (screen.height() - self.height()) // 3   # slightly above centre
        self.move(x, y)
        self.show()
        self.raise_()
        self.activateWindow()
        # Small timer to ensure focus after window manager settles
        QTimer.singleShot(100, self.search_box.setFocus)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def run_popup(category: str | None = None, mode: str = "clipboard"):
    """
    Launch the popup picker.
    mode: "clipboard" | "primary"
    """
    engine   = init_db()
    session  = get_session(engine)
    snippets = repo.list_snippets(session, category=category, limit=500)

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("SnippetLauncher")

    popup = LauncherPopup(snippets, mode=mode)
    popup.show_centred()

    app.exec()
