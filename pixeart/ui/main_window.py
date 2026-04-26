from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QStackedWidget,
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
        self.tools_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.tools_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetFloatable | QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.toolbar_widget = ToolBarWidget()
        self.tools_dock.setWidget(self.toolbar_widget)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.tools_dock)

        # 2. Katmanlar
        self.layers_dock = QDockWidget("Katmanlar", self)
        self.layers_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.layer_panel = LayerPanel()
        self.layers_dock.setWidget(self.layer_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.layers_dock)

        # 3. Renk Paleti
        self.color_dock = QDockWidget("Renk Paleti", self)
        self.color_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.color_palette = ColorPalette()
        self.color_dock.setWidget(self.color_palette)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.color_dock)

        # 4. Navigator
        self.navigator_dock = QDockWidget("Gezgin", self)
        self.navigator_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.navigator = NavigatorWidget(self.canvas_view, self.canvas_scene)
        self.navigator_dock.setWidget(self.navigator)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.navigator_dock)

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
        hs_action.triggered.connect(self._on_hue_saturation)
        adj_menu.addAction(hs_action)

        fx_menu = edit_menu.addMenu("Efektler (FX)")
        outline_action = QAction("Dış Çizgi (Outline)...", self)
        outline_action.triggered.connect(self._on_outline)
        fx_menu.addAction(outline_action)
        
        conv_action = QAction("Matris Filtresi (Convolution)...", self)
        conv_action.triggered.connect(self._on_convolution)
        fx_menu.addAction(conv_action)

        # --- Görünüm Menüsü ---
        view_menu = menubar.addMenu("Görünüm")

        self.onion_action = QAction("Onion Skinning", self)
        self.onion_action.setShortcut("O")
        self.onion_action.setCheckable(True)
        self.onion_action.triggered.connect(self._on_toggle_onion)
        view_menu.addAction(self.onion_action)

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

    def _on_cut(self):
        self._on_copy()
        self._on_delete_selection()
        
    # --- Transform İşlemleri ---
    def _apply_transform(self, t_type: str):
        if not self.document or self.document.active_layer_index < 0: return
        
        idx = self.document.active_layer_index
        layer = self.document.layers[idx]
        before_pixels = layer.active_pixels.copy()
        
        if t_type == "flip_h":
            after_pixels = self.document.get_flipped_horizontal(before_pixels)
        elif t_type == "flip_v":
            after_pixels = self.document.get_flipped_vertical(before_pixels)
        elif t_type == "rot_180":
            after_pixels = self.document.get_rotated(before_pixels, 180)
        elif t_type == "rot_90cw":
            after_pixels = self.document.get_rotated(before_pixels, 90)
        elif t_type == "rot_90ccw":
            after_pixels = self.document.get_rotated(before_pixels, 270)
        elif t_type == "shift_left":
            after_pixels = self.document.get_shifted(before_pixels, -1, 0)
        elif t_type == "shift_right":
            after_pixels = self.document.get_shifted(before_pixels, 1, 0)
        elif t_type == "shift_up":
            after_pixels = self.document.get_shifted(before_pixels, 0, -1)
        elif t_type == "shift_down":
            after_pixels = self.document.get_shifted(before_pixels, 0, 1)
        else:
            return
            
        from pixeart.core.commands import ModifyLayerCommand
        cmd = ModifyLayerCommand(self.document, idx, before_pixels, after_pixels)
        self.tool_manager.commit_command(cmd)

    # --- Hızlı Efekt İşlemleri ---
    def _apply_effect(self, e_type: str):
        if not self.document or self.document.active_layer_index < 0: return
        
        idx = self.document.active_layer_index
        layer = self.document.layers[idx]
        before_pixels = layer.active_pixels.copy()
        
        from pixeart.core.effects_logic import invert_colors, grayscale
        if e_type == "invert":
            after_pixels = invert_colors(before_pixels)
        elif e_type == "grayscale":
            after_pixels = grayscale(before_pixels)
        else:
            return
            
        from pixeart.core.commands import ModifyLayerCommand
        cmd = ModifyLayerCommand(self.document, idx, before_pixels, after_pixels)
        self.tool_manager.commit_command(cmd)

    # --- Diyaloglu Efekt İşlemleri (Preview Destekli) ---
    def _apply_dialog_effect(self, dialog_class, effect_func, initial_args=None):
        if not self.document or self.document.active_layer_index < 0: return
        
        layer_idx = self.document.active_layer_index
        layer = self.document.layers[layer_idx]
        original_pixels = layer.active_pixels.copy()
        
        if initial_args is None: initial_args = {}
        dialog = dialog_class(**initial_args, parent=self)
        
        def apply_preview(is_active, args):
            layer.clear()
            if is_active:
                new_pixels = effect_func(original_pixels, **args)
                for (x, y), c in new_pixels.items():
                    if not c.is_transparent:
                        layer.set_pixel(x, y, c)
            else:
                for (x, y), c in original_pixels.items():
                    if not c.is_transparent:
                        layer.set_pixel(x, y, c)
            self.canvas_scene.sync_layers()
            self.navigator.update_preview()
            
        dialog.preview_requested.connect(apply_preview)
        
        if dialog.exec():
            args = dialog._get_args()
            new_pixels = effect_func(original_pixels, **args)
            
            # Commit için orijinali geri yükle
            layer.clear()
            for (x, y), c in original_pixels.items():
                if not c.is_transparent:
                    layer.set_pixel(x, y, c)
                
            from pixeart.core.commands import ModifyLayerCommand
            cmd = ModifyLayerCommand(self.document, layer_idx, original_pixels, new_pixels)
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
