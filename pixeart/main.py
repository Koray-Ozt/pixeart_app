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
    app.setStyleSheet("""
        QMainWindow, QWidget {
            background-color: #2b2b2b;
            color: #e0e0e0;
        }
        QDockWidget {
            titlebar-close-icon: url(close.png);
            titlebar-normal-icon: url(undock.png);
        }
        QDockWidget::title {
            background: #1e1e1e;
            color: #ffffff;
            padding: 6px;
            font-weight: bold;
        }
        QMenuBar {
            background-color: #1e1e1e;
            color: #ffffff;
            border-bottom: 1px solid #000000;
        }
        QMenuBar::item:selected {
            background-color: #3e3e3e;
            border-radius: 4px;
        }
        QMenu {
            background-color: #2b2b2b;
            color: #ffffff;
            border: 1px solid #1e1e1e;
        }
        QMenu::item:selected {
            background-color: #007acc;
        }
        QStatusBar {
            background-color: #007acc;
            color: white;
            font-weight: bold;
        }
    """)
    
    # Ana pencereyi oluştur ve göster
    window = MainWindow()
    window.show()
    
    # Uygulama döngüsünü çalıştır
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
