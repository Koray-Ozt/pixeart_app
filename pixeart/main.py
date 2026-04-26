import sys
import os

# Projenin kök dizinini sys.path'e ekleyelim ki 
# "from pixeart.core import..." gibi mutlak import'lar hatasız çalışsın.
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from PyQt6.QtWidgets import QApplication
from pixeart.ui.main_window import MainWindow

def main():
    # PyQt6 uygulamasını başlat
    app = QApplication(sys.argv)
    app.setApplicationName("PixeArt")
    
    # Modern bir görünüm için çapraz platform "Fusion" stilini kullan
    app.setStyle("Fusion")
    
    # Koyu tema için geçici ve şık bir stil (İleride dark_theme.qss dosyasına taşınacak)
    # Aseprite-inspired koyu tema
    app.setStyleSheet("""
        /* === Global === */
        QMainWindow, QWidget {
            background-color: #2b2b2b;
            color: #e0e0e0;
            font-size: 13px;
        }
        QLabel {
            padding: 0px;
        }

        /* === Dock Widget === */
        QDockWidget {
            titlebar-close-icon: url(pixeart/resources/icons/close.png);
            titlebar-normal-icon: url(pixeart/resources/icons/undock.png);
        }
        QDockWidget::title {
            background: #1a1a1a;
            color: #a0c0ff;
            padding: 5px 10px;
            font-weight: bold;
            font-size: 12px;
            border-bottom: 1px solid #333;
        }
        QDockWidget::close-button, QDockWidget::float-button {
            border: none;
            padding: 2px;
        }

        /* === Menu Bar === */
        QMenuBar {
            background-color: #1a1a1a;
            color: #d0d0d0;
            border-bottom: 1px solid #000;
            padding: 2px 0px;
            spacing: 4px;
        }
        QMenuBar::item {
            padding: 4px 10px;
            border-radius: 3px;
        }
        QMenuBar::item:selected {
            background-color: #3a3a3a;
        }
        QMenuBar::item:pressed {
            background-color: #005a9e;
            color: white;
        }

        /* === Menu === */
        QMenu {
            background-color: #252525;
            color: #e0e0e0;
            border: 1px solid #1a1a1a;
            padding: 4px 0px;
        }
        QMenu::item {
            padding: 5px 28px 5px 24px;
        }
        QMenu::item:selected {
            background-color: #005a9e;
            color: white;
        }
        QMenu::separator {
            height: 1px;
            background: #3a3a3a;
            margin: 4px 8px;
        }
        QMenu::indicator {
            width: 14px;
            height: 14px;
            margin-left: 6px;
        }

        /* === Status Bar === */
        QStatusBar {
            background-color: #005a9e;
            color: white;
            font-weight: bold;
            font-size: 12px;
            padding: 2px 8px;
        }

        /* === Scroll Bar (koyu ve ince) === */
        QScrollBar:vertical {
            background: #1e1e1e;
            width: 10px;
            margin: 0px;
        }
        QScrollBar::handle:vertical {
            background: #555;
            min-height: 30px;
            border-radius: 4px;
        }
        QScrollBar::handle:vertical:hover { background: #777; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        
        QScrollBar:horizontal {
            background: #1e1e1e;
            height: 10px;
            margin: 0px;
        }
        QScrollBar::handle:horizontal {
            background: #555;
            min-width: 30px;
            border-radius: 4px;
        }
        QScrollBar::handle:horizontal:hover { background: #777; }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }

        /* === Tab Widget === */
        QTabWidget::pane {
            border: 1px solid #333;
            background: #2b2b2b;
        }
        QTabBar::tab {
            background: #1e1e1e;
            color: #aaa;
            padding: 6px 14px;
            border: 1px solid #333;
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background: #2b2b2b;
            color: #fff;
            border-bottom: 2px solid #005a9e;
        }
        QTabBar::tab:hover:!selected {
            background: #333;
            color: #ddd;
        }

        /* === Buttons (genel) === */
        QPushButton {
            background-color: #333;
            color: #e0e0e0;
            border: 1px solid #444;
            border-radius: 4px;
            padding: 5px 12px;
            font-size: 12px;
        }
        QPushButton:hover {
            background-color: #404040;
            border: 1px solid #666;
        }
        QPushButton:pressed {
            background-color: #005a9e;
            border: 1px solid #007acc;
            color: white;
        }
        QPushButton:disabled {
            background-color: #2a2a2a;
            color: #555;
            border: 1px solid #333;
        }

        /* === Spin Box / Combo Box === */
        QSpinBox, QComboBox {
            background-color: #1e1e1e;
            color: #e0e0e0;
            border: 1px solid #444;
            border-radius: 3px;
            padding: 3px 6px;
        }
        QSpinBox:focus, QComboBox:focus {
            border: 1px solid #005a9e;
        }
        QComboBox::drop-down {
            border: none;
            width: 18px;
        }
        QComboBox QAbstractItemView {
            background: #252525;
            color: #e0e0e0;
            selection-background-color: #005a9e;
        }

        /* === Slider === */
        QSlider::groove:horizontal {
            height: 4px;
            background: #444;
            border-radius: 2px;
        }
        QSlider::handle:horizontal {
            background: #007acc;
            width: 14px;
            height: 14px;
            margin: -5px 0;
            border-radius: 7px;
        }
        QSlider::handle:horizontal:hover {
            background: #0098ff;
        }

        /* === List Widget === */
        QListWidget {
            background-color: #1e1e1e;
            border: 1px solid #333;
            outline: none;
        }
        QListWidget::item {
            padding: 4px;
            border-bottom: 1px solid #2a2a2a;
        }
        QListWidget::item:selected {
            background-color: #005a9e;
            color: white;
        }
        QListWidget::item:hover:!selected {
            background-color: #333;
        }

        /* === Dialog === */
        QDialog {
            background-color: #2b2b2b;
        }

        /* === Tooltip === */
        QToolTip {
            background-color: #1a1a1a;
            color: #e0e0e0;
            border: 1px solid #555;
            padding: 4px 8px;
            font-size: 12px;
        }
    """)
    
    # Ana pencereyi oluştur ve göster
    window = MainWindow()
    window.show()
    
    # Uygulama döngüsünü çalıştır
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
