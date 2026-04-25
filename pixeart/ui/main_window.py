from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, 
    QStatusBar, QLabel, QDockWidget, QMenuBar,
    QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QColor, QShortcut, QKeySequence

from pixeart.core.history import History
from pixeart.core.document import Document
from pixeart.core.layer import Layer

from pixeart.ui.canvas.scene import CanvasScene
from pixeart.ui.canvas.view import CanvasView
from pixeart.ui.dialogs.new_file_dialog import NewFileDialog
from pixeart.ui.dialogs.export_dialog import ExportDialog
from pixeart.ui.widgets.toolbar import ToolBarWidget
from pixeart.ui.widgets.layer_panel import LayerPanel
from pixeart.ui.widgets.color_palette import ColorPalette
from pixeart.tools.manager import ToolManager
from pixeart.tools.base_tool import BrushShape

class MainWindow(QMainWindow):
    """
    PixeArt ana penceresi (Hub).
    Tuval (Canvas), araç çubukları ve yan panelleri barındırır.
    Tüm modüllerin birbirleriyle konuştuğu merkezi sistemdir.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PixeArt - Modern Pixel Art Editörü")
        self.resize(1280, 720) 
        
        # Proje Durumu (Core State)
        self.document = None
        self.history = History()
        
        # Araç Yöneticisi (ToolManager)
        self.tool_manager = ToolManager(self.history)
        
        # Undo/Redo aksiyonlarının durumunu güncellemek için history callback
        self.history.register_callback(self._update_undo_redo_actions)
        
        self._init_ui()
        self._connect_signals()
        
        QShortcut(QKeySequence("B"), self).activated.connect(lambda: self.toolbar_widget.select_tool("pencil"))
        QShortcut(QKeySequence("E"), self).activated.connect(lambda: self.toolbar_widget.select_tool("eraser"))
        QShortcut(QKeySequence("G"), self).activated.connect(lambda: self.toolbar_widget.select_tool("fill"))
        
    def _init_ui(self):
        """Arayüz bileşenlerini sırasıyla oluşturur."""
        self._create_central_widget()
        self._create_docks()
        self._create_menus()
        
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("PixeArt başlatıldı. Çizime başlamak için Dosya > Yeni... diyerek belge açın.")

    def _create_central_widget(self):
        """Merkez çalışma alanını (Tuval ve Kamera) oluşturur."""
        self.central_widget = QWidget()
        self.central_layout = QVBoxLayout(self.central_widget)
        self.central_layout.setContentsMargins(0, 0, 0, 0)
        
        # Gerçek Grafik Sahnesi ve Kamerası
        self.canvas_scene = CanvasScene()
        self.canvas_view = CanvasView(self.canvas_scene)
        
        self.central_layout.addWidget(self.canvas_view)
        self.setCentralWidget(self.central_widget)

    def _create_docks(self):
        """Bağımsız Widget'ları Ana Pencere üzerindeki Dock'lara bağlar."""
        # 1. Araçlar (Toolbar Widget)
        self.tools_dock = QDockWidget("Araçlar", self)
        self.tools_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.tools_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetFloatable | QDockWidget.DockWidgetFeature.DockWidgetMovable)
        
        self.toolbar_widget = ToolBarWidget()
        self.tools_dock.setWidget(self.toolbar_widget)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.tools_dock)
        
        # 2. Katmanlar (Layer Panel Widget)
        self.layers_dock = QDockWidget("Katmanlar", self)
        self.layers_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        
        self.layer_panel = LayerPanel()
        self.layers_dock.setWidget(self.layer_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.layers_dock)

        # 3. Renk Paleti (Color Palette Widget)
        self.color_dock = QDockWidget("Renk Paleti", self)
        self.color_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        
        self.color_palette = ColorPalette()
        self.color_dock.setWidget(self.color_palette)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.color_dock)

    def _create_menus(self):
        """Üst menü çubuğunu ve diyalog bağlantılarını oluşturur."""
        menubar = self.menuBar()
        
        # --- Dosya Menüsü ---
        file_menu = menubar.addMenu("Dosya")
        
        new_action = QAction("Yeni...", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._on_new_file)
        file_menu.addAction(new_action)
        
        open_action = QAction("Aç...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._on_open_file)
        file_menu.addAction(open_action)
        
        save_action = QAction("Kaydet", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._on_save_file)
        file_menu.addAction(save_action)
        
        export_action = QAction("Dışa Aktar...", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self._on_export)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Çıkış", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # --- Düzen Menüsü ---
        edit_menu = menubar.addMenu("Düzen")
        
        self.undo_action = QAction("Geri Al", self)
        self.undo_action.setShortcut("Ctrl+Z")
        self.undo_action.setEnabled(False) 
        self.undo_action.triggered.connect(self.history.undo)
        edit_menu.addAction(self.undo_action)
        
        self.redo_action = QAction("İleri Al", self)
        self.redo_action.setShortcut("Ctrl+Y")
        self.redo_action.setEnabled(False)
        self.redo_action.triggered.connect(self.history.redo)
        edit_menu.addAction(self.redo_action)
        
    def _connect_signals(self):
        """Tüm paneller arasındaki haberleşme sinyallerini merkeze bağlar."""
        self.layer_panel.layer_structure_changed.connect(self._on_layer_structure_changed)
        self.layer_panel.layer_visibility_changed.connect(self._on_layer_visibility_changed)
        
        self.toolbar_widget.tool_changed.connect(self._on_tool_changed)
        self.toolbar_widget.brush_size_changed.connect(self._on_brush_size_changed)
        self.toolbar_widget.brush_shape_changed.connect(self._on_brush_shape_changed)
        
        self.color_palette.primary_color_changed.connect(self._on_primary_color_changed)
        self.color_palette.secondary_color_changed.connect(self._on_secondary_color_changed)
        self.tool_manager.color_palette = self.color_palette
        
        self.canvas_scene.pixel_clicked.connect(self.tool_manager.handle_press)
        self.canvas_scene.pixel_dragged.connect(self.tool_manager.handle_drag)
        self.canvas_scene.pixel_released.connect(self.tool_manager.handle_release)
        
    def _on_new_file(self):
        """'Yeni Dosya' diyaloğunu açar ve kullanıcı onaylarsa yeni Document üretir."""
        dialog = NewFileDialog(self)
        if dialog.exec():
            width = dialog.width_spin.value()
            height = dialog.height_spin.value()
            self._create_document(width, height)
            
    def _on_export(self):
        """'Dışa Aktar' diyaloğunu açar."""
        if not self.document:
            self.statusBar.showMessage("Dışa aktarılacak belge yok!", 3000)
            return
            
        dialog = ExportDialog(self.document, self)
        if dialog.exec():
            dialog.export_image()
            
    def _on_save_file(self):
        if not self.document:
            return
            
        file_path = self.document.file_path
        if not file_path:
            file_path, _ = QFileDialog.getSaveFileName(self, "Projeyi Kaydet", "", "PixeArt Projesi (*.pixe)")
            if not file_path:
                return
                
        try:
            self.document.save_to_file(file_path)
            self.statusBar.showMessage("Proje başarıyla kaydedildi.", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Kaydetme hatası:\\n{str(e)}")

    def _on_open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Proje Aç", "", "PixeArt Projesi (*.pixe)")
        if not file_path:
            return
            
        try:
            doc = Document.load_from_file(file_path)
            self.document = doc
            self.canvas_scene.set_document(self.document)
            self.layer_panel.set_document(self.document)
            self.tool_manager.set_document(self.document)
            self.canvas_view.reset_view()
            
            # History'yi sıfırla
            self.history = History()
            self.history.on_history_changed = self._update_undo_redo_actions
            self.tool_manager.history = self.history
            self._update_undo_redo_actions()
            
            self.statusBar.showMessage("Proje başarıyla yüklendi.", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Dosya açma hatası:\\n{str(e)}")

    def _create_document(self, width: int, height: int):
        """Yeni bir boş belge oluşturur ve sistemi ayağa kaldırır."""
        self.document = Document(width, height)
        
        # Uygulama açılır açılmaz standart bir 'Arkaplan' katmanı oluştur.
        bg_layer = Layer("Arkaplan")
        self.document.add_layer(bg_layer)
        
        # Document (Data) nesnesini Arayüz birimlerine enjekte ediyoruz (Dependency Injection)
        self.canvas_scene.set_document(self.document)
        self.layer_panel.set_document(self.document)
        
        self.tool_manager.set_document(self.document)
        self.tool_manager.set_canvas_scene(self.canvas_scene)
        
        # Kamera (View) açısını sıfırla ve tuvalin ortasına odaklan
        self.canvas_view.reset_view()
        
        self.statusBar.showMessage(f"Yeni belge oluşturuldu: {width}x{height}", 3000)

    # --- SİNYAL YAKALAYICILAR (Slotlar) ---

    def _on_layer_structure_changed(self):
        """Kullanıcı katman eklediğinde veya sildiğinde Canvas'a senkronizasyon emri yollar."""
        self.canvas_scene.sync_layers()
        
    def _on_layer_visibility_changed(self):
        """Göz ikonuna tıklandığında Canvas'ın katman görünürlüklerini güncellemesini sağlar."""
        self.canvas_scene.sync_layers()

    def _on_tool_changed(self, tool_code: str):
        """Toolbar'da farklı bir araca tıklandığında tetiklenir."""
        self.statusBar.showMessage(f"Araç seçildi: {tool_code}", 2000)
        self.tool_manager.set_tool(tool_code)
        
    def _on_brush_size_changed(self, size: int):
        self.tool_manager.brush_size = size
        
    def _on_brush_shape_changed(self, shape_str: str):
        if shape_str == "circle":
            self.tool_manager.brush_shape = BrushShape.CIRCLE
        else:
            self.tool_manager.brush_shape = BrushShape.SQUARE

    def _on_primary_color_changed(self, color: QColor):
        """Paletten yeni ana renk seçildiğinde tetiklenir."""
        self.tool_manager.set_primary_color(color)
        
    def _on_secondary_color_changed(self, color: QColor):
        """Paletten ikinci renk seçildiğinde tetiklenir."""
        self.tool_manager.set_secondary_color(color)
        
    def _update_undo_redo_actions(self):
        """History callback tetiklendiğinde butonların aktifliğini ayarlar."""
        self.undo_action.setEnabled(self.history.can_undo)
        self.redo_action.setEnabled(self.history.can_redo)
        # Ekranı komple tazeleyebiliriz, ancak ToolManager zaten hızlı güncellemeyi yapıyor.
        # Undo/Redo sonucu gerçek bir render almalıyız çünkü çoklu piksel değişimi oluyor.
        self.canvas_scene.sync_layers()
        self.layer_panel.update_thumbnails()
