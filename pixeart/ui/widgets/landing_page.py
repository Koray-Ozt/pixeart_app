import json
import os
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QFrame, QListWidget, QListWidgetItem, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QColor

RECENTS_FILE = os.path.join(os.path.expanduser("~"), ".pixeart_recents.json")
MAX_RECENTS = 15


def load_recents():
    try:
        with open(RECENTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [r for r in data if os.path.exists(r)]
    except (OSError, json.JSONDecodeError):
        return []


def save_recents(recents):
    try:
        with open(RECENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(recents[:MAX_RECENTS], f)
    except OSError:
        pass


def add_recent(file_path: str):
    recents = load_recents()
    abs_path = os.path.abspath(file_path)
    if abs_path in recents:
        recents.remove(abs_path)
    recents.insert(0, abs_path)
    save_recents(recents)


class LandingPage(QWidget):
    new_project_requested = pyqtSignal()
    open_file_requested = pyqtSignal()
    open_recent_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ===================== SOL PANEL =====================
        left_panel = QFrame()
        left_panel.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a1a2e, stop:1 #16213e);
            }
        """)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(50, 60, 50, 60)
        left_layout.setSpacing(20)

        # Logo / Başlık
        logo = QLabel("🎨")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet("font-size: 56px; background: transparent;")
        left_layout.addWidget(logo)

        title = QLabel("PixeArt")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            font-size: 36px; font-weight: bold;
            color: #e0e0e0; letter-spacing: 3px;
            background: transparent;
        """)
        left_layout.addWidget(title)

        subtitle = QLabel("Modern Pixel Art Editörü")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("font-size: 13px; color: #7a8ba6; background: transparent;")
        left_layout.addWidget(subtitle)

        left_layout.addSpacing(30)

        # Yeni Proje Butonu
        self.btn_new = QPushButton("   Yeni Proje")
        self.btn_new.setFixedHeight(52)
        self.btn_new.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0f3460, stop:1 #533483);
                color: white; font-size: 16px; font-weight: bold;
                border: none; border-radius: 10px;
                padding: 0 24px; text-align: left;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1a4f8a, stop:1 #6d44a8);
            }
            QPushButton:pressed { background: #0a2540; }
        """)
        self.btn_new.clicked.connect(self.new_project_requested.emit)
        left_layout.addWidget(self.btn_new)

        # Dosya Aç Butonu
        self.btn_open = QPushButton("   Dosya Aç (.pixe)")
        self.btn_open.setFixedHeight(52)
        self.btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #aab8d0; font-size: 15px; font-weight: bold;
                border: 2px solid #334466; border-radius: 10px;
                padding: 0 24px; text-align: left;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.04);
                border-color: #5577aa; color: white;
            }
            QPushButton:pressed { background: rgba(255, 255, 255, 0.02); }
        """)
        self.btn_open.clicked.connect(self.open_file_requested.emit)
        left_layout.addWidget(self.btn_open)

        left_layout.addStretch()

        # Versiyon
        ver = QLabel("v0.1.0")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ver.setStyleSheet("color: #3a4a60; font-size: 11px; background: transparent;")
        left_layout.addWidget(ver)

        # Sadece sol paneli yerleştir, genişliği sabit tutmuyoruz (esnek)
        root.addWidget(left_panel)

        self._populate_recents()

    def _populate_recents(self):
        # Son çalışmalar listesi UI'dan kaldırıldığı için içi boş bırakıldı
        pass

    def _on_recent_double_clicked(self, item: QListWidgetItem):
        pass

    def refresh(self):
        pass
