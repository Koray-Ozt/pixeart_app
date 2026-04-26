from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QStackedWidget,
    QStatusBar, QLabel, QDockWidget, QMenuBar,
    QFileDialog, QMessageBox, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QActionGroup, QColor, QShortcut, QKeySequence

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
from pixeart.ui.widgets.landing_page import LandingPage, add_recent
from pixeart.ui.widgets.navigator import NavigatorWidget
from pixeart.tools.manager import ToolManager, SymmetryMode
from pixeart.tools.base_tool import BrushShape
from pixeart.tools.selection import SelectionTool


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

        import os
        from PyQt6.QtGui import QIcon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources", "icons", "logo.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Proje Durumu (Core State)
        self.document = None
        self.history = History()

        # Araç Yöneticisi (ToolManager)
        self.tool_manager = ToolManager(self.history)

        # Seçim aracını kaydet
        self._selection_tool = SelectionTool()
        self.tool_manager.register_tool("selection", self._selection_tool)

        # Undo/Redo aksiyonlarının durumunu güncellemek için history callback
        self.history.register_callback(self._update_undo_redo_actions)

        self._init_ui()
        self._connect_signals()

        # Global Kısayollar
        QShortcut(QKeySequence("B"), self).activated.connect(lambda: self.toolbar_widget.select_tool("pencil"))
        QShortcut(QKeySequence("E"), self).activated.connect(lambda: self.toolbar_widget.select_tool("eraser"))
        QShortcut(QKeySequence("G"), self).activated.connect(lambda: self.toolbar_widget.select_tool("fill"))
        QShortcut(QKeySequence("M"), self).activated.connect(lambda: self.toolbar_widget.select_tool("selection"))

        # Uygulama açılışında Landing Page göster
        self._show_landing()

    def showEvent(self, event):
        super().showEvent(event)
        target_width = int(self.width() * 0.2)
        target_widths = [target_width, target_width, target_width, target_width]
        docks = [self.layers_dock, self.color_dock, self.navigator_dock, self.history_dock]
        self.resizeDocks(docks, target_widths, Qt.Orientation.Horizontal)
        
        # Position floating navigator dock at top right if it is floating
        QTimer.singleShot(0, self._position_navigator)

    def _position_navigator(self):
        if self.navigator_dock.isFloating():
            geom = self.geometry()
            dock_geom = self.navigator_dock.geometry()
            self.navigator_dock.move(geom.right() - dock_geom.width() - 40, geom.top() + 60)

    def closeEvent(self, event):
        """Uygulamadan çıkarken kaydedilmemiş değişiklikleri kontrol et."""
        if self.document and self.document.is_dirty:
            reply = QMessageBox.question(
                self, "Kaydedilmemiş Değişiklikler",
                "Kaydedilmemiş değişiklikler var.\nÇıkmadan önce kaydetmek ister misiniz?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Save:
                self._on_save_file()
                if self.document and self.document.is_dirty:
                    # Kullanıcı kaydetme diyalogunu iptal ettiyse
                    event.ignore()
                    return
            elif reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
        event.accept()

    def _init_ui(self):
        """Arayüz bileşenlerini sırasıyla oluşturur."""
        self._create_central_widget()
        self._create_docks()
        self._create_menus()

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("PixeArt başlatıldı.")

    def _create_central_widget(self):
        """Merkez çalışma alanını (Landing Page + Tuval) oluşturur."""
        self.landing_page = LandingPage()
        self.landing_page.new_project_requested.connect(self._on_new_file)
        self.landing_page.open_file_requested.connect(self._on_open_file)
        self.landing_page.open_recent_requested.connect(self._open_file_from_path)

        self.canvas_scene = CanvasScene()
        self.canvas_view = CanvasView(self.canvas_scene)

        self.stacked = QStackedWidget()
        self.stacked.addWidget(self.landing_page)
        self.stacked.addWidget(self.canvas_view)
        self.setCentralWidget(self.stacked)

    def _create_docks(self):
        """Bağımsız Widget'ları Ana Pencere üzerindeki Dock'lara bağlar."""
        # 1. Araçlar
        self.tools_dock = QDockWidget("Araçlar", self)
        self.tools_dock.setAllowedAreas(Qt.DockWidgetArea.TopDockWidgetArea | Qt.DockWidgetArea.BottomDockWidgetArea)
        self.tools_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetFloatable | QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.toolbar_widget = ToolBarWidget()
        self.tools_dock.setWidget(self.toolbar_widget)
        self.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, self.tools_dock)

        # 2. Katmanlar
        def create_scrollable_dock(dock_widget, inner_widget):
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QScrollArea.Shape.NoFrame)
            scroll.setWidget(inner_widget)
            dock_widget.setWidget(scroll)
            inner_widget.setMinimumHeight(150)
            inner_widget.setMinimumWidth(200)
            
        # 2. Katmanlar (Layers)
        self.layers_dock = QDockWidget("Katmanlar", self)
        self.layers_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.layer_panel = LayerPanel()
        create_scrollable_dock(self.layers_dock, self.layer_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.layers_dock)

        # 3. Renk Paleti
        self.color_dock = QDockWidget("Renk Paleti", self)
        self.color_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.color_palette = ColorPalette()
        create_scrollable_dock(self.color_dock, self.color_palette)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.color_dock)

        # 4. Navigator
        self.navigator_dock = QDockWidget("Gezgin", self)
        self.navigator_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.navigator = NavigatorWidget(self.canvas_view, self.canvas_scene)
        self.navigator.setMinimumHeight(200) # Navigator için özel min boyut
        self.navigator.setMinimumWidth(200)
        self.navigator_dock.setWidget(self.navigator) # Navigator kendi resize mantığına sahip
        self.navigator_dock.setFloating(True) # Varsayılan olarak yüzer modda başlat
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.navigator_dock)

        # 5. Geçmiş (History)
        self.history_dock = QDockWidget("Geçmiş", self)
        self.history_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        from pixeart.ui.widgets.history_panel import HistoryPanel
        self.history_panel = HistoryPanel(self.history)
        create_scrollable_dock(self.history_dock, self.history_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.history_dock)

    def _create_menus(self):
        """Üst menü çubuğunu ve diyalog bağlantılarını oluşturur."""
        menubar = self.menuBar()

        # --- Dosya Menüsü ---
        file_menu = menubar.addMenu("Dosya")

        import os
        icon_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources", "icons")
        from PyQt6.QtGui import QIcon

        new_action = QAction(QIcon(os.path.join(icon_dir, "new.png")), "Yeni...", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._on_new_file)
        file_menu.addAction(new_action)

        open_action = QAction(QIcon(os.path.join(icon_dir, "open.png")), "Aç...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._on_open_file)
        file_menu.addAction(open_action)

        save_action = QAction(QIcon(os.path.join(icon_dir, "save.png")), "Kaydet", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._on_save_file)
        file_menu.addAction(save_action)

        export_action = QAction("Dışa Aktar...", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self._on_export)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        ref_action = QAction("Referans Görsel Yükle...", self)
        ref_action.triggered.connect(self._on_load_reference)
        file_menu.addAction(ref_action)

        clear_ref_action = QAction("Referans Görseli Kaldır", self)
        clear_ref_action.triggered.connect(lambda: self.canvas_scene.clear_reference_image())
        file_menu.addAction(clear_ref_action)

        file_menu.addSeparator()

        exit_action = QAction("Çıkış", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # --- Düzen Menüsü ---
        edit_menu = menubar.addMenu("Düzen")

        self.undo_action = QAction("Geri Al (Undo)", self)
        self.undo_action.setShortcut("Ctrl+Z")
        self.undo_action.setEnabled(False)
        self.undo_action.triggered.connect(self.history.undo)
        edit_menu.addAction(self.undo_action)

        self.redo_action = QAction("İleri Al (Redo)", self)
        self.redo_action.setShortcut("Ctrl+Y")
        self.redo_action.setEnabled(False)
        self.redo_action.triggered.connect(self.history.redo)
        edit_menu.addAction(self.redo_action)

        edit_menu.addSeparator()

        paste_special_menu = edit_menu.addMenu("Özel Yapıştır (Paste Special)")
        paste_new_layer = QAction("Yeni Katmana Yapıştır (Paste as New Layer)", self)
        paste_new_layer.triggered.connect(self._on_paste_new_layer)
        paste_special_menu.addAction(paste_new_layer)
        
        paste_new_sprite = QAction("Yeni Belgeye Yapıştır (Paste as New Sprite)", self)
        paste_new_sprite.triggered.connect(self._on_paste_new_sprite)
        paste_special_menu.addAction(paste_new_sprite)

        edit_menu.addSeparator()

        cut_action = QAction("Kes (Cut)", self)
        cut_action.setShortcut("Ctrl+X")
        cut_action.triggered.connect(self._on_cut)
        edit_menu.addAction(cut_action)

        copy_action = QAction("Kopyala (Copy)", self)
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(self._on_copy)
        edit_menu.addAction(copy_action)

        paste_action = QAction("Yapıştır (Paste)", self)
        paste_action.setShortcut("Ctrl+V")
        paste_action.triggered.connect(self._on_paste)
        edit_menu.addAction(paste_action)

        delete_action = QAction("Sil (Delete)", self)
        delete_action.setShortcut("Del")
        delete_action.triggered.connect(self._on_delete_selection)
        edit_menu.addAction(delete_action)

        deselect_action = QAction("Seçimi Kaldır (Deselect)", self)
        deselect_action.setShortcut("Ctrl+D")
        deselect_action.triggered.connect(self._on_deselect)
        edit_menu.addAction(deselect_action)

        edit_menu.addSeparator()

        fill_action = QAction("Doldur (Fill)", self)
        fill_action.setShortcut("Shift+F")
        fill_action.triggered.connect(self._on_fill)
        edit_menu.addAction(fill_action)
        
        stroke_action = QAction("Sınır Çiz (Stroke)", self)
        stroke_action.triggered.connect(self._on_stroke)
        edit_menu.addAction(stroke_action)

        edit_menu.addSeparator()

        # --- Transform ---
        transform_menu = edit_menu.addMenu("Dönüştür (Transform)")
        
        flip_h = QAction("Yatay Çevir (Flip Horizontal)", self)
        flip_h.triggered.connect(lambda: self._apply_transform("flip_h"))
        transform_menu.addAction(flip_h)
        
        flip_v = QAction("Dikey Çevir (Flip Vertical)", self)
        flip_v.triggered.connect(lambda: self._apply_transform("flip_v"))
        transform_menu.addAction(flip_v)
        
        rot_180 = QAction("180° Döndür", self)
        rot_180.triggered.connect(lambda: self._apply_transform("rot_180"))
        transform_menu.addAction(rot_180)
        
        rot_90cw = QAction("90° Saat Yönünde (CW)", self)
        rot_90cw.triggered.connect(lambda: self._apply_transform("rot_90cw"))
        transform_menu.addAction(rot_90cw)
        
        rot_90ccw = QAction("90° Saat Yönü Tersi (CCW)", self)
        rot_90ccw.triggered.connect(lambda: self._apply_transform("rot_90ccw"))
        transform_menu.addAction(rot_90ccw)

        # --- Shift ---
        shift_menu = edit_menu.addMenu("Kaydır (Shift)")
        shift_left = QAction("Sola (Left)", self)
        shift_left.triggered.connect(lambda: self._apply_transform("shift_left"))
        shift_menu.addAction(shift_left)
        
        shift_right = QAction("Sağa (Right)", self)
        shift_right.triggered.connect(lambda: self._apply_transform("shift_right"))
        shift_menu.addAction(shift_right)
        
        shift_up = QAction("Yukarı (Up)", self)
        shift_up.triggered.connect(lambda: self._apply_transform("shift_up"))
        shift_menu.addAction(shift_up)
        
        shift_down = QAction("Aşağı (Down)", self)
        shift_down.triggered.connect(lambda: self._apply_transform("shift_down"))
        shift_menu.addAction(shift_down)

        edit_menu.addSeparator()

        # --- Effects & Colors ---
        replace_color_action = QAction("Rengi Değiştir... (Replace Color)", self)
        replace_color_action.setShortcut("Shift+R")
        replace_color_action.triggered.connect(self._on_replace_color)
        edit_menu.addAction(replace_color_action)

        invert_action = QAction("Renkleri Tersine Çevir (Invert)", self)
        invert_action.setShortcut("Ctrl+I")
        invert_action.triggered.connect(lambda: self._apply_effect("invert"))
        edit_menu.addAction(invert_action)
        
        grayscale_action = QAction("Siyah-Beyaz (Grayscale)", self)
        grayscale_action.triggered.connect(lambda: self._apply_effect("grayscale"))
        edit_menu.addAction(grayscale_action)

        adj_menu = edit_menu.addMenu("Ayarlar (Adjustments)")
        bc_action = QAction("Parlaklık / Kontrast...", self)
        bc_action.triggered.connect(self._on_brightness_contrast)
        adj_menu.addAction(bc_action)
        
        hs_action = QAction("Ton / Doygunluk (Hue/Sat)...", self)
        hs_action.setShortcut("Ctrl+U")
        hs_action.triggered.connect(self._on_hue_saturation)
        adj_menu.addAction(hs_action)
        
        curve_action = QAction("Renk Eğrisi (Color Curve)...", self)
        curve_action.setShortcut("Ctrl+M")
        curve_action.triggered.connect(self._on_color_curve)
        adj_menu.addAction(curve_action)

        fx_menu = edit_menu.addMenu("Efektler (FX)")
        outline_action = QAction("Dış Çizgi (Outline)...", self)
        outline_action.triggered.connect(self._on_outline)
        fx_menu.addAction(outline_action)
        
        despeckle_action = QAction("Gürültü Azalt (Despeckle)", self)
        despeckle_action.triggered.connect(lambda: self._apply_effect("despeckle"))
        fx_menu.addAction(despeckle_action)
        
        blur_action = QAction("Bulanıklaştır (Blur)", self)
        blur_action.triggered.connect(self._on_blur)
        fx_menu.addAction(blur_action)
        
        conv_action = QAction("Matris Filtresi (Convolution)...", self)
        conv_action.triggered.connect(self._on_convolution)
        fx_menu.addAction(conv_action)
        
        lighting_action = QAction("Aydınlatma (Lighting)...", self)
        lighting_action.triggered.connect(self._on_lighting)
        fx_menu.addAction(lighting_action)

        # --- Görünüm (View) Menüsü ---
        view_menu = menubar.addMenu("Görünüm")

        # -- Paneller (Panels) Alt Menüsü --
        panels_menu = view_menu.addMenu("Paneller")
        panels_menu.addAction(self.tools_dock.toggleViewAction())
        panels_menu.addAction(self.layers_dock.toggleViewAction())
        panels_menu.addAction(self.color_dock.toggleViewAction())
        panels_menu.addAction(self.navigator_dock.toggleViewAction())
        panels_menu.addAction(self.history_dock.toggleViewAction())

        view_menu.addSeparator()

        # -- Show (Göster) Alt Menüsü --
        show_menu = view_menu.addMenu("Göster (Show)")

        self.show_layer_edges_action = QAction("Layer Edges", self)
        self.show_layer_edges_action.setCheckable(True)
        self.show_layer_edges_action.setChecked(False)
        self.show_layer_edges_action.triggered.connect(self._on_toggle_layer_edges)
        show_menu.addAction(self.show_layer_edges_action)

        self.show_selection_edges_action = QAction("Selection Edges", self)
        self.show_selection_edges_action.setCheckable(True)
        self.show_selection_edges_action.setChecked(True)
        self.show_selection_edges_action.triggered.connect(self._on_toggle_selection_edges)
        show_menu.addAction(self.show_selection_edges_action)

        self.show_grid_action = QAction("Grid (Izgara)", self)
        self.show_grid_action.setShortcut("Ctrl+'")
        self.show_grid_action.setCheckable(True)
        self.show_grid_action.setChecked(True)
        self.show_grid_action.triggered.connect(self._on_toggle_grid)
        show_menu.addAction(self.show_grid_action)

        self.show_auto_guides_action = QAction("Auto Guides", self)
        self.show_auto_guides_action.setCheckable(True)
        self.show_auto_guides_action.setChecked(False)
        show_menu.addAction(self.show_auto_guides_action)

        self.show_slices_action = QAction("Slices", self)
        self.show_slices_action.setCheckable(True)
        self.show_slices_action.setChecked(False)
        show_menu.addAction(self.show_slices_action)

        self.show_pixel_grid_action = QAction("Pixel Grid", self)
        self.show_pixel_grid_action.setCheckable(True)
        self.show_pixel_grid_action.setChecked(True)
        self.show_pixel_grid_action.triggered.connect(self._on_toggle_pixel_grid)
        show_menu.addAction(self.show_pixel_grid_action)

        view_menu.addSeparator()

        # -- Grid (Izgara) Alt Menüsü --
        grid_menu = view_menu.addMenu("Izgara (Grid)")

        grid_settings_action = QAction("Grid Settings...", self)
        grid_settings_action.triggered.connect(self._on_grid_settings)
        grid_menu.addAction(grid_settings_action)

        selection_as_grid_action = QAction("Selection as Grid", self)
        selection_as_grid_action.triggered.connect(self._on_selection_as_grid)
        grid_menu.addAction(selection_as_grid_action)

        grid_menu.addSeparator()

        self.snap_to_grid_action = QAction("Snap to Grid", self)
        self.snap_to_grid_action.setShortcut("Shift+S")
        self.snap_to_grid_action.setCheckable(True)
        self.snap_to_grid_action.setChecked(False)
        self.snap_to_grid_action.triggered.connect(self._on_toggle_snap_to_grid)
        grid_menu.addAction(self.snap_to_grid_action)

        # -- Tiled Mode (Döşeme Modu) Alt Menüsü --
        tiled_menu = view_menu.addMenu("Döşeme Modu (Tiled Mode)")
        self.tiled_group = QActionGroup(self)
        self.tiled_group.setExclusive(True)

        tiled_options = [
            ("None", "none"),
            ("Tiled in Both Axes", "both"),
            ("Tiled in X Axis", "x"),
            ("Tiled in Y Axis", "y"),
        ]
        self._tiled_mode = "none"
        for label, code in tiled_options:
            action = QAction(label, self)
            action.setCheckable(True)
            action.setData(code)
            if code == "none":
                action.setChecked(True)
            self.tiled_group.addAction(action)
            tiled_menu.addAction(action)
        self.tiled_group.triggered.connect(self._on_tiled_mode_changed)

        view_menu.addSeparator()

        # -- Bağımsız Seçenekler --
        duplicate_view_action = QAction("Duplicate View", self)
        duplicate_view_action.triggered.connect(self._on_duplicate_view)
        view_menu.addAction(duplicate_view_action)

        self.extras_action = QAction("Extras", self)
        self.extras_action.setShortcut("Ctrl+H")
        self.extras_action.setCheckable(True)
        self.extras_action.setChecked(True)
        self.extras_action.triggered.connect(self._on_toggle_extras)
        view_menu.addAction(self.extras_action)

        view_menu.addSeparator()

        symmetry_options_action = QAction("Symmetry Options...", self)
        symmetry_options_action.triggered.connect(self._on_symmetry_options)
        view_menu.addAction(symmetry_options_action)

        self.onion_action = QAction("Show Onion Skin", self)
        self.onion_action.setShortcut("F3")
        self.onion_action.setCheckable(True)
        self.onion_action.triggered.connect(self._on_toggle_onion)
        view_menu.addAction(self.onion_action)

        view_menu.addSeparator()

        timeline_action = QAction("Timeline", self)
        timeline_action.triggered.connect(lambda: self.statusBar.showMessage("Timeline henüz aktif değil.", 3000))
        view_menu.addAction(timeline_action)

        preview_action = QAction("Preview", self)
        preview_action.triggered.connect(self._on_toggle_preview)
        view_menu.addAction(preview_action)

        view_menu.addSeparator()

        fullscreen_action = QAction("Full Screen Mode", self)
        fullscreen_action.setShortcut("F11")
        fullscreen_action.triggered.connect(self._on_toggle_fullscreen)
        view_menu.addAction(fullscreen_action)

    def _connect_signals(self):
        """Tüm paneller arasındaki haberleşme sinyallerini merkeze bağlar."""
        self.layer_panel.layer_structure_changed.connect(self._on_layer_structure_changed)
        self.layer_panel.layer_visibility_changed.connect(self._on_layer_visibility_changed)

        self.toolbar_widget.tool_changed.connect(self._on_tool_changed)
        self.toolbar_widget.brush_size_changed.connect(self._on_brush_size_changed)
        self.toolbar_widget.brush_shape_changed.connect(self._on_brush_shape_changed)

        # Grid kontrolleri
        self.toolbar_widget.grid_visible_changed.connect(self.canvas_view.set_grid_visible)
        self.toolbar_widget.tile_grid_visible_changed.connect(self.canvas_view.set_tile_grid_visible)
        self.toolbar_widget.tile_size_changed.connect(self.canvas_view.set_tile_size)

        # Simetri
        self.toolbar_widget.symmetry_changed.connect(self._on_symmetry_changed)

        # Seçim modu
        self.toolbar_widget.selection_mode_changed.connect(self._on_selection_mode_changed)

        self.color_palette.primary_color_changed.connect(self._on_primary_color_changed)
        self.color_palette.secondary_color_changed.connect(self._on_secondary_color_changed)
        self.tool_manager.color_palette = self.color_palette

        self.canvas_scene.pixel_clicked.connect(self.tool_manager.handle_press)
        self.canvas_scene.pixel_dragged.connect(self.tool_manager.handle_drag)
        self.canvas_scene.pixel_released.connect(self.tool_manager.handle_release)

        # Navigator güncelleme sinyali
        self.canvas_view.zoom_changed.connect(lambda z: self.navigator.update_preview())

    # --- Sayfa Geçişleri ---

    def _show_landing(self):
        self.landing_page.refresh()
        self.stacked.setCurrentIndex(0)
        self.tools_dock.hide()
        self.layers_dock.hide()
        self.color_dock.hide()
        self.navigator_dock.hide()

    def _show_editor(self):
        self.stacked.setCurrentIndex(1)
        self.tools_dock.show()
        self.layers_dock.show()
        self.color_dock.show()
        self.navigator_dock.show()

    # --- Dosya İşlemleri ---

    def _on_new_file(self):
        dialog = NewFileDialog(self)
        if dialog.exec():
            width = dialog.width_spin.value()
            height = dialog.height_spin.value()
            self._create_document(width, height)

    def _on_export(self):
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
            add_recent(file_path)
            self.statusBar.showMessage("Proje başarıyla kaydedildi.", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Kaydetme hatası:\n{str(e)}")

    def _on_open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Proje Aç", "", "PixeArt Projesi (*.pixe)")
        if file_path:
            self._open_file_from_path(file_path)

    def _open_file_from_path(self, file_path: str):
        try:
            doc = Document.load_from_file(file_path)
            self.document = doc
            add_recent(file_path)

            self.canvas_scene.set_document(self.document)
            self.layer_panel.set_document(self.document)
            self.tool_manager.set_document(self.document)
            self.tool_manager.set_canvas_scene(self.canvas_scene)

            self._show_editor()
            self.canvas_view.reset_view()
            self.navigator.set_canvas(self.canvas_view, self.canvas_scene)
            self.navigator.update_preview()

            self.history = History()
            self.history.register_callback(self._update_undo_redo_actions)
            self.tool_manager.history = self.history
            self._update_undo_redo_actions()

            self.statusBar.showMessage("Proje başarıyla yüklendi.", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Dosya açma hatası:\n{str(e)}")

    def _on_load_reference(self):
        path, _ = QFileDialog.getOpenFileName(self, "Referans Görsel", "",
                                              "Görseller (*.png *.jpg *.jpeg *.bmp *.gif);;Tüm Dosyalar (*)")
        if path:
            self.canvas_scene.set_reference_image(path)

    def _create_document(self, width: int, height: int):
        self.document = Document(width, height)
        bg_layer = Layer("Arkaplan")
        self.document.add_layer(bg_layer)

        self.canvas_scene.set_document(self.document)
        self.layer_panel.set_document(self.document)
        self.tool_manager.set_document(self.document)
        self.tool_manager.set_canvas_scene(self.canvas_scene)

        self._show_editor()
        self.canvas_view.reset_view()
        self.navigator.set_canvas(self.canvas_view, self.canvas_scene)
        self.navigator.update_preview()

        self.statusBar.showMessage(f"Yeni belge oluşturuldu: {width}x{height}", 3000)

    # --- SİNYAL YAKALAYICILAR (Slotlar) ---

    def _on_layer_structure_changed(self):
        self.canvas_scene.sync_layers()

    def _on_layer_visibility_changed(self):
        self.canvas_scene.sync_layers()

    def _on_tool_changed(self, tool_code: str):
        self.statusBar.showMessage(f"Araç seçildi: {tool_code}", 2000)
        self.tool_manager.set_tool(tool_code)

    def _on_brush_size_changed(self, size: int):
        self.tool_manager.brush_size = size

    def _on_brush_shape_changed(self, shape_str: str):
        if shape_str == "circle":
            self.tool_manager.brush_shape = BrushShape.CIRCLE
        else:
            self.tool_manager.brush_shape = BrushShape.SQUARE

    def _on_symmetry_changed(self, mode: str):
        mode_map = {
            "none": SymmetryMode.NONE,
            "vertical": SymmetryMode.VERTICAL,
            "horizontal": SymmetryMode.HORIZONTAL,
            "both": SymmetryMode.BOTH,
        }
        self.tool_manager.symmetry_mode = mode_map.get(mode, SymmetryMode.NONE)
        self.canvas_view.set_symmetry_mode(mode)
        self.statusBar.showMessage(f"Simetri: {mode}", 2000)

    def _on_selection_mode_changed(self, mode: str):
        self._selection_tool.mode = mode

    def _on_primary_color_changed(self, color: QColor):
        self.tool_manager.set_primary_color(color)

    def _on_secondary_color_changed(self, color: QColor):
        self.tool_manager.set_secondary_color(color)

    def _on_toggle_onion(self, checked: bool):
        self.canvas_scene.set_onion_skinning(checked)
        self.statusBar.showMessage(f"Onion Skinning: {'Açık' if checked else 'Kapalı'}", 2000)

    # --- Görünüm (View) Menüsü Slot'ları ---

    def _on_toggle_layer_edges(self, checked: bool):
        """Katman sınırlarını göster/gizle (scene rect border)."""
        self.canvas_scene.show_layer_edges = checked
        self.canvas_scene.update()
        self.statusBar.showMessage(f"Layer Edges: {'Açık' if checked else 'Kapalı'}", 2000)

    def _on_toggle_selection_edges(self, checked: bool):
        """Seçim kenarlarını (karınca sürüsü) göster/gizle."""
        self.canvas_scene.show_selection_edges = checked
        self.canvas_scene.update()
        self.statusBar.showMessage(f"Selection Edges: {'Açık' if checked else 'Kapalı'}", 2000)

    def _on_toggle_grid(self, checked: bool):
        """Tile ızgarasını aç/kapa."""
        self.canvas_view.set_tile_grid_visible(checked)
        self.statusBar.showMessage(f"Grid: {'Açık' if checked else 'Kapalı'}", 2000)

    def _on_toggle_pixel_grid(self, checked: bool):
        """1x1 piksel ızgarasını aç/kapa."""
        self.canvas_view.set_grid_visible(checked)
        self.statusBar.showMessage(f"Pixel Grid: {'Açık' if checked else 'Kapalı'}", 2000)

    def _on_toggle_snap_to_grid(self, checked: bool):
        """Snap to Grid durumunu güncelle."""
        self.canvas_view.snap_to_grid = checked
        self.statusBar.showMessage(f"Snap to Grid: {'Açık' if checked else 'Kapalı'}", 2000)

    def _on_grid_settings(self):
        """Izgara boyutu ve rengini ayarlamak için diyalog."""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QPushButton, QColorDialog
        dlg = QDialog(self)
        dlg.setWindowTitle("Grid Settings")
        layout = QVBoxLayout(dlg)

        size_row = QHBoxLayout()
        size_row.addWidget(QLabel("Tile Boyutu:"))
        spin = QSpinBox()
        spin.setRange(2, 256)
        spin.setValue(self.canvas_view._tile_size)
        size_row.addWidget(spin)
        layout.addLayout(size_row)

        color_btn = QPushButton("Izgara Rengi Seç...")
        selected_color = [self.canvas_view._tile_grid_color]
        def pick_color():
            c = QColorDialog.getColor(selected_color[0], self, "Izgara Rengi")
            if c.isValid():
                selected_color[0] = c
                color_btn.setStyleSheet(f"background-color: {c.name()};")
        color_btn.clicked.connect(pick_color)
        layout.addWidget(color_btn)

        btn_row = QHBoxLayout()
        ok_btn = QPushButton("Tamam")
        cancel_btn = QPushButton("İptal")
        ok_btn.clicked.connect(dlg.accept)
        cancel_btn.clicked.connect(dlg.reject)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.canvas_view.set_tile_size(spin.value())
            self.canvas_view.set_tile_grid_color(selected_color[0])
            self.statusBar.showMessage(f"Grid: {spin.value()}x{spin.value()} ayarlandı.", 3000)

    def _on_selection_as_grid(self):
        """Mevcut seçimi ızgara boyutu olarak ayarla."""
        if not hasattr(self, '_selection_tool') or not self._selection_tool.selection_rect:
            self.statusBar.showMessage("Aktif seçim yok.", 3000)
            return
        rect = self._selection_tool.selection_rect
        size = max(int(rect.width()), int(rect.height()))
        if size >= 2:
            self.canvas_view.set_tile_size(size)
            self.statusBar.showMessage(f"Grid boyutu seçime göre ayarlandı: {size}x{size}", 3000)

    def _on_tiled_mode_changed(self, action):
        """Döşeme modunu güncelle."""
        self._tiled_mode = action.data()
        self.canvas_view.set_tiled_mode(self._tiled_mode)
        self.statusBar.showMessage(f"Tiled Mode: {action.text()}", 2000)

    def _on_duplicate_view(self):
        """Tuvali yeni bir pencerede göster."""
        from PyQt6.QtWidgets import QMainWindow as QMW
        viewer = QMW(self)
        viewer.setWindowTitle("PixeArt – Duplicate View")
        dup_view = CanvasView(self.canvas_scene, viewer)
        viewer.setCentralWidget(dup_view)
        viewer.resize(600, 500)
        dup_view.set_zoom(self.canvas_view._zoom_factor)
        viewer.show()
        self.statusBar.showMessage("Duplicate view açıldı.", 2000)

    def _on_toggle_extras(self, checked: bool):
        """Tüm yardımcı gösterimleri (grid, simetri, seçim) tek tuşla aç/kapa."""
        self.canvas_view.set_grid_visible(checked)
        self.canvas_view.set_tile_grid_visible(checked)
        # Menüdeki checkmark'ları senkronize et
        self.show_grid_action.setChecked(checked)
        self.show_pixel_grid_action.setChecked(checked)
        self.statusBar.showMessage(f"Extras: {'Açık' if checked else 'Kapalı'}", 2000)

    def _on_symmetry_options(self):
        """Simetri modunu seçmek için hızlı diyalog."""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QRadioButton, QPushButton, QHBoxLayout
        dlg = QDialog(self)
        dlg.setWindowTitle("Symmetry Options")
        layout = QVBoxLayout(dlg)

        modes = [("Kapalı", "none"), ("Dikey (Vertical)", "vertical"),
                 ("Yatay (Horizontal)", "horizontal"), ("Her İki Eksen (Both)", "both")]
        radios = []
        for label, code in modes:
            rb = QRadioButton(label)
            if self.canvas_view._symmetry_mode == code:
                rb.setChecked(True)
            rb.code = code
            radios.append(rb)
            layout.addWidget(rb)

        btn_row = QHBoxLayout()
        ok_btn = QPushButton("Tamam")
        ok_btn.clicked.connect(dlg.accept)
        cancel_btn = QPushButton("İptal")
        cancel_btn.clicked.connect(dlg.reject)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            for rb in radios:
                if rb.isChecked():
                    self._on_symmetry_changed(rb.code)
                    break

    def _on_toggle_preview(self):
        """Navigator dock'unu göster/gizle."""
        is_visible = self.navigator_dock.isVisible()
        self.navigator_dock.setVisible(not is_visible)
        self.statusBar.showMessage(f"Preview: {'Gizlendi' if is_visible else 'Gösterildi'}", 2000)

    def _on_toggle_fullscreen(self):
        """Tam ekran modunu aç/kapa."""
        if self.isFullScreen():
            self.showNormal()
            self.statusBar.showMessage("Tam ekrandan çıkıldı.", 2000)
        else:
            self.showFullScreen()
            self.statusBar.showMessage("Tam ekran moduna geçildi.", 2000)

    # --- Seçim İşlemleri ---
    def _on_copy(self):
        self._selection_tool.copy_selection()
        self.statusBar.showMessage("Seçim kopyalandı.", 2000)

    def _on_paste(self):
        self._selection_tool.paste_clipboard()
        self.canvas_scene.sync_layers()
        self.statusBar.showMessage("Yapıştırıldı.", 2000)

    def _on_delete_selection(self):
        self._selection_tool.delete_selection()
        self.canvas_scene.sync_layers()
        self.statusBar.showMessage("Seçim silindi.", 2000)

    def _on_deselect(self):
        self._selection_tool.clear_selection()
        self.statusBar.showMessage("Seçim kaldırıldı.", 2000)

    def _update_undo_redo_actions(self):
        self.undo_action.setEnabled(self.history.can_undo)
        self.redo_action.setEnabled(self.history.can_redo)
        self.canvas_scene.sync_layers()
        self.layer_panel.update_thumbnails()
        self.navigator.update_preview()
        if hasattr(self, 'history_panel'):
            self.history_panel.refresh()

    def _on_cut(self):
        self._on_copy()
        self._on_delete_selection()
        
    # --- Transform İşlemleri ---
    def _apply_transform(self, t_type: str):
        if not self.document or self.document.active_layer_index < 0: return
        
        idx = self.document.active_layer_index
        layer = self.document.layers[idx]
        before_pixels_full = layer.active_pixels.copy()
        
        sel_pixels = self._selection_tool.selection_pixels
        bbox = None
        
        if sel_pixels:
            xs = [p[0] for p in sel_pixels]
            ys = [p[1] for p in sel_pixels]
            bbox = (min(xs), min(ys), max(xs), max(ys))
            
            target_pixels = {}
            for (x, y) in sel_pixels:
                if (x, y) in before_pixels_full:
                    target_pixels[(x, y)] = before_pixels_full[(x, y)]
        else:
            target_pixels = before_pixels_full.copy()
        
        if t_type == "flip_h":
            transformed_pixels = self.document.get_flipped_horizontal(target_pixels, bbox)
        elif t_type == "flip_v":
            transformed_pixels = self.document.get_flipped_vertical(target_pixels, bbox)
        elif t_type == "rot_180":
            transformed_pixels = self.document.get_rotated(target_pixels, 180, bbox)
        elif t_type == "rot_90cw":
            transformed_pixels = self.document.get_rotated(target_pixels, 90, bbox)
        elif t_type == "rot_90ccw":
            transformed_pixels = self.document.get_rotated(target_pixels, 270, bbox)
        elif t_type == "shift_left":
            transformed_pixels = self.document.get_shifted(target_pixels, -1, 0)
        elif t_type == "shift_right":
            transformed_pixels = self.document.get_shifted(target_pixels, 1, 0)
        elif t_type == "shift_up":
            transformed_pixels = self.document.get_shifted(target_pixels, 0, -1)
        elif t_type == "shift_down":
            transformed_pixels = self.document.get_shifted(target_pixels, 0, 1)
        else:
            return
            
        if sel_pixels:
            after_pixels_full = before_pixels_full.copy()
            for (x, y) in sel_pixels:
                if (x, y) in after_pixels_full:
                    del after_pixels_full[(x, y)]
            for (x, y), color in transformed_pixels.items():
                after_pixels_full[(x, y)] = color
                
            self._selection_tool.transform_selection(t_type, bbox)
        else:
            after_pixels_full = transformed_pixels
            
        from pixeart.core.commands import ModifyLayerCommand
        cmd = ModifyLayerCommand(self.document, idx, before_pixels_full, after_pixels_full, name=f"Transform: {t_type}")
        self.tool_manager.commit_command(cmd)

    # --- Hızlı Efekt İşlemleri ---
    def _apply_effect(self, e_type: str):
        if not self.document or self.document.active_layer_index < 0: return
        
        idx = self.document.active_layer_index
        layer = self.document.layers[idx]
        before_pixels_full = layer.active_pixels.copy()
        
        sel_pixels = self._selection_tool.selection_pixels
        if sel_pixels:
            target_pixels = {}
            for (x, y) in sel_pixels:
                if (x, y) in before_pixels_full:
                    target_pixels[(x, y)] = before_pixels_full[(x, y)]
        else:
            target_pixels = before_pixels_full.copy()
        
        from pixeart.core.effects_logic import invert_colors, grayscale, apply_despeckle
        if e_type == "invert":
            transformed_pixels = invert_colors(target_pixels)
        elif e_type == "grayscale":
            transformed_pixels = grayscale(target_pixels)
        elif e_type == "despeckle":
            transformed_pixels = apply_despeckle(target_pixels, self.document.width, self.document.height)
        else:
            return
            
        if sel_pixels:
            after_pixels_full = before_pixels_full.copy()
            for (x, y) in sel_pixels:
                if (x, y) in after_pixels_full:
                    del after_pixels_full[(x, y)]
            for (x, y), color in transformed_pixels.items():
                after_pixels_full[(x, y)] = color
        else:
            after_pixels_full = transformed_pixels
            
        from pixeart.core.commands import ModifyLayerCommand
        cmd = ModifyLayerCommand(self.document, idx, before_pixels_full, after_pixels_full, name=f"FX: {e_type}")
        self.tool_manager.commit_command(cmd)

    # --- Diyaloglu Efekt İşlemleri (Preview Destekli) ---
    def _apply_dialog_effect(self, dialog_class, effect_func, initial_args=None, name="FX"):
        if not self.document or self.document.active_layer_index < 0: return
        
        layer_idx = self.document.active_layer_index
        layer = self.document.layers[layer_idx]
        before_pixels_full = layer.active_pixels.copy()
        
        sel_pixels = self._selection_tool.selection_pixels
        
        if initial_args is None: initial_args = {}
        dialog = dialog_class(**initial_args, parent=self)
        
        def apply_preview(is_active, args):
            layer.clear()
            if is_active:
                if sel_pixels:
                    target_pixels = { (x,y): before_pixels_full[(x,y)] for (x,y) in sel_pixels if (x,y) in before_pixels_full }
                else:
                    target_pixels = before_pixels_full.copy()
                    
                transformed_pixels = effect_func(target_pixels, **args)
                
                if sel_pixels:
                    temp_full = before_pixels_full.copy()
                    for (x, y) in sel_pixels:
                        if (x, y) in temp_full: del temp_full[(x, y)]
                    for (x, y), c in transformed_pixels.items():
                        temp_full[(x, y)] = c
                    new_pixels = temp_full
                else:
                    new_pixels = transformed_pixels
                    
                for (x, y), c in new_pixels.items():
                    if not c.is_transparent:
                        layer.set_pixel(x, y, c)
            else:
                for (x, y), c in before_pixels_full.items():
                    if not c.is_transparent:
                        layer.set_pixel(x, y, c)
            self.canvas_scene.sync_layers()
            self.navigator.update_preview()
            
        dialog.preview_requested.connect(apply_preview)
        
        if dialog.exec():
            args = dialog._get_args()
            
            if sel_pixels:
                target_pixels = { (x,y): before_pixels_full[(x,y)] for (x,y) in sel_pixels if (x,y) in before_pixels_full }
            else:
                target_pixels = before_pixels_full.copy()
                
            transformed_pixels = effect_func(target_pixels, **args)
            
            if sel_pixels:
                after_pixels_full = before_pixels_full.copy()
                for (x, y) in sel_pixels:
                    if (x, y) in after_pixels_full: del after_pixels_full[(x, y)]
                for (x, y), c in transformed_pixels.items():
                    after_pixels_full[(x, y)] = c
            else:
                after_pixels_full = transformed_pixels
            
            # Commit için orijinali geri yükle
            layer.clear()
            for (x, y), c in before_pixels_full.items():
                if not c.is_transparent:
                    layer.set_pixel(x, y, c)
                
            from pixeart.core.commands import ModifyLayerCommand
            cmd = ModifyLayerCommand(self.document, layer_idx, before_pixels_full, after_pixels_full, name=name)
            self.tool_manager.commit_command(cmd)
        else:
            # İptal edildi, eski haline dön
            apply_preview(False, {})

    def _on_replace_color(self):
        from pixeart.ui.dialogs.effects_dialogs import ReplaceColorDialog
        from pixeart.core.effects_logic import replace_color
        prim = self.tool_manager.primary_color
        t_color = QColor(prim.r, prim.g, prim.b, prim.a)
        self._apply_dialog_effect(ReplaceColorDialog, replace_color, {"target_color": t_color})

    def _on_brightness_contrast(self):
        from pixeart.ui.dialogs.effects_dialogs import BrightnessContrastDialog
        from pixeart.core.effects_logic import adjust_brightness_contrast
        self._apply_dialog_effect(BrightnessContrastDialog, adjust_brightness_contrast)

    def _on_hue_saturation(self):
        from pixeart.ui.dialogs.effects_dialogs import HueSaturationDialog
        from pixeart.core.effects_logic import adjust_hue_saturation
        self._apply_dialog_effect(HueSaturationDialog, adjust_hue_saturation)

    def _on_outline(self):
        from pixeart.ui.dialogs.effects_dialogs import OutlineDialog
        from pixeart.core.effects_logic import apply_outline
        self._apply_dialog_effect(OutlineDialog, apply_outline)

    def _on_convolution(self):
        from pixeart.ui.dialogs.effects_dialogs import ConvolutionDialog
        from pixeart.core.effects_logic import apply_convolution_matrix
        
        def effect_wrapper(pixels, matrix):
            return apply_convolution_matrix(pixels, matrix, self.document.width, self.document.height)
            
        self._apply_dialog_effect(ConvolutionDialog, effect_wrapper)

    def start_eyedropper_for_dialog(self, dialog):
        self._waiting_dialog = dialog
        self.canvas_scene.picking_target_color = True
        self.canvas_view.setCursor(Qt.CursorShape.CrossCursor)
        
        def on_color_picked(qcolor):
            self.canvas_scene.picking_target_color = False
            self.canvas_view.setCursor(Qt.CursorShape.ArrowCursor)
            self.canvas_scene.color_picked.disconnect(on_color_picked)
            if self._waiting_dialog:
                self._waiting_dialog.set_target_color(qcolor)
                self._waiting_dialog = None
                
        self.canvas_scene.color_picked.connect(on_color_picked)

    def _on_color_curve(self):
        from pixeart.ui.dialogs.effects_dialogs import ColorCurveDialog
        from pixeart.core.effects_logic import apply_color_curve
        self._apply_dialog_effect(ColorCurveDialog, apply_color_curve, name="Color Curve")

    def _on_lighting(self):
        from pixeart.ui.dialogs.effects_dialogs import LightingEffectDialog
        from pixeart.core.rendering_logic import apply_lighting_pipeline
        
        def effect_wrapper(pixels, lx, ly, lz, kd, ks, shininess, num_bands):
            return apply_lighting_pipeline(
                pixels, self.document.width, self.document.height,
                lx, ly, lz, kd, ks, shininess, num_bands
            )
            
        self._apply_dialog_effect(LightingEffectDialog, effect_wrapper, name="FX: Lighting")

    def _on_blur(self):
        from pixeart.core.effects_logic import apply_convolution_matrix
        matrix = [[1/9, 1/9, 1/9], [1/9, 1/9, 1/9], [1/9, 1/9, 1/9]]
        
        if not self.document or self.document.active_layer_index < 0: return
        idx = self.document.active_layer_index
        layer = self.document.layers[idx]
        before_pixels_full = layer.active_pixels.copy()
        
        sel_pixels = self._selection_tool.selection_pixels
        target_pixels = { (x,y): before_pixels_full[(x,y)] for (x,y) in sel_pixels if (x,y) in before_pixels_full } if sel_pixels else before_pixels_full.copy()
        
        transformed = apply_convolution_matrix(target_pixels, matrix, self.document.width, self.document.height)
        
        after_pixels_full = before_pixels_full.copy()
        if sel_pixels:
            for (x, y) in sel_pixels:
                if (x, y) in after_pixels_full: del after_pixels_full[(x, y)]
        for (x, y), color in transformed.items():
            after_pixels_full[(x, y)] = color
            
        from pixeart.core.commands import ModifyLayerCommand
        cmd = ModifyLayerCommand(self.document, idx, before_pixels_full, after_pixels_full, name="FX: Blur")
        self.tool_manager.commit_command(cmd)

    def _on_fill(self):
        if not self.document or self.document.active_layer_index < 0: return
        idx = self.document.active_layer_index
        layer = self.document.layers[idx]
        before_pixels_full = layer.active_pixels.copy()
        sel = self._selection_tool.selection_pixels
        c = self.tool_manager.primary_color
        
        after_pixels_full = self.document.get_filled_pixels(before_pixels_full, sel, c)
        
        from pixeart.core.commands import ModifyLayerCommand
        cmd = ModifyLayerCommand(self.document, idx, before_pixels_full, after_pixels_full, name="Fill Selection")
        self.tool_manager.commit_command(cmd)

    def _on_stroke(self):
        if not self.document or self.document.active_layer_index < 0: return
        idx = self.document.active_layer_index
        layer = self.document.layers[idx]
        before_pixels_full = layer.active_pixels.copy()
        sel = self._selection_tool.selection_pixels
        c = self.tool_manager.primary_color
        
        after_pixels_full = self.document.get_stroked_pixels(before_pixels_full, sel, c)
        
        from pixeart.core.commands import ModifyLayerCommand
        cmd = ModifyLayerCommand(self.document, idx, before_pixels_full, after_pixels_full, name="Stroke Selection")
        self.tool_manager.commit_command(cmd)

    def _on_paste_new_layer(self):
        if not self.document or not self._selection_tool.clipboard: return
        from pixeart.core.layer import Layer
        from pixeart.core.selection_commands import PasteCommand
        
        new_layer = Layer(f"Katman {len(self.document.layers) + 1}")
        self.document.add_layer(new_layer)
        self.document.set_active_layer(len(self.document.layers) - 1)
        
        cmd = PasteCommand(self.document, self.document.active_layer_index, self._selection_tool.clipboard.copy(), 0, 0, name="Paste as New Layer")
        self.tool_manager.commit_command(cmd)
        
    def _on_paste_new_sprite(self):
        if not self._selection_tool.clipboard: return
        # Calculate size of clipboard content
        xs = [p[0] for p in self._selection_tool.clipboard.keys()]
        ys = [p[1] for p in self._selection_tool.clipboard.keys()]
        if not xs or not ys: return
        
        w = max(xs) + 1
        h = max(ys) + 1
        
        self._create_document(w, h)
        from pixeart.core.selection_commands import PasteCommand
        cmd = PasteCommand(self.document, 0, self._selection_tool.clipboard.copy(), 0, 0, name="Paste")
        self.tool_manager.commit_command(cmd)
