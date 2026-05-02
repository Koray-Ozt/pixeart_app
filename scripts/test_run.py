import sys
from PyQt6.QtWidgets import QApplication
from pixeart.ui.main_window import MainWindow

app = QApplication(sys.argv)
try:
    window = MainWindow()
    print("Application initialized successfully.")
    sys.exit(0)
except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)
