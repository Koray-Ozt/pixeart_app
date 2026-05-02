from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QSpinBox, QListWidget, QListWidgetItem, QAbstractItemView, QStackedWidget
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon

class TimelineWidget(QWidget):
    def __init__(self, animation_controller, parent=None):
        super().__init__(parent)
        self.controller = animation_controller
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        self.stacked = QStackedWidget(self)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.stacked)
        
        # --- Page 0: Activation ---
        self.activation_page = QWidget()
        act_layout = QHBoxLayout(self.activation_page)
        
        self.btn_activate = QPushButton("Animasyonu Etkinleştir")
        self.btn_activate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_activate.setFixedWidth(200)
        act_layout.addStretch()
        act_layout.addWidget(self.btn_activate)
        act_layout.addStretch()
        
        # --- Page 1: Timeline Controls ---
        self.controls_page = QWidget()
        layout = QVBoxLayout(self.controls_page)
        layout.setContentsMargins(5, 5, 5, 5)

        # Controls Row
        controls_layout = QHBoxLayout()
        
        self.btn_prev = QPushButton("⏮")
        self.btn_prev.setToolTip("Önceki Kare")
        self.btn_prev.setFixedWidth(30)
        
        self.btn_play = QPushButton("▶")
        self.btn_play.setToolTip("Oynat / Durdur")
        self.btn_play.setFixedWidth(30)
        
        self.btn_next = QPushButton("⏭")
        self.btn_next.setToolTip("Sonraki Kare")
        self.btn_next.setFixedWidth(30)



        
        controls_layout.addWidget(self.btn_prev)
        controls_layout.addWidget(self.btn_play)
        controls_layout.addWidget(self.btn_next)
        controls_layout.addSpacing(10)
        controls_layout.addStretch()
        
        # Frame actions
        self.btn_add_frame = QPushButton("+ Yeni Kare")
        self.btn_duplicate_frame = QPushButton("Kopyala")
        self.btn_delete_frame = QPushButton("Sil")
        
        controls_layout.addWidget(self.btn_add_frame)
        controls_layout.addWidget(self.btn_duplicate_frame)
        controls_layout.addWidget(self.btn_delete_frame)
        
        layout.addLayout(controls_layout)

        # Frames List
        self.frame_list = QListWidget()
        self.frame_list.setFlow(QListWidget.Flow.LeftToRight)
        self.frame_list.setViewMode(QListWidget.ViewMode.IconMode)
        self.frame_list.setIconSize(QSize(48, 48))
        self.frame_list.setSpacing(5)
        self.frame_list.setFixedHeight(80)
        self.frame_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.frame_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.frame_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        layout.addWidget(self.frame_list)
        
        self.stacked.addWidget(self.activation_page)
        self.stacked.addWidget(self.controls_page)
        self.stacked.setCurrentIndex(0)

    def _connect_signals(self):
        self.btn_prev.clicked.connect(self.controller.prev_frame)
        self.btn_next.clicked.connect(self.controller.next_frame)
        self.btn_play.clicked.connect(self.controller.toggle_playback)
        
        self.controller.playback_state_changed.connect(self._on_playback_state_changed)
        self.controller.frame_changed.connect(self._on_frame_changed)
        
        self.frame_list.currentRowChanged.connect(self._on_list_selection_changed)
        
        self.btn_add_frame.clicked.connect(self._on_add_frame)
        self.btn_duplicate_frame.clicked.connect(self._on_duplicate_frame)
        self.btn_delete_frame.clicked.connect(self._on_delete_frame)
        
        self.btn_activate.clicked.connect(self._activate_animation)
        
    def _activate_animation(self):
        self.stacked.setCurrentIndex(1)
        # Ensure we have at least 1 frame to show
        if self.controller.document and not self.controller.document.frames:
            self._on_add_frame()
        self.refresh_frames()

    def set_document(self, document):
        self.controller.set_document(document)
        # Reset to activation page if only 1 frame, else show timeline
        if document and len(document.frames) > 1:
            self.stacked.setCurrentIndex(1)
        else:
            self.stacked.setCurrentIndex(0)
        self.refresh_frames()

    def refresh_frames(self):
        self.frame_list.blockSignals(True)
        self.frame_list.clear()
        
        doc = self.controller.document
        if not doc or not doc.frames:
            self.frame_list.blockSignals(False)
            return
            
        for i, frame in enumerate(doc.frames):
            item = QListWidgetItem(f"Kare {i+1}")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.frame_list.addItem(item)
            
        if 0 <= doc.active_frame_index < self.frame_list.count():
            self.frame_list.setCurrentRow(doc.active_frame_index)
            
        self.frame_list.blockSignals(False)

    def _on_playback_state_changed(self, is_playing: bool):
        self.btn_play.setText("⏸" if is_playing else "▶")
        # Disable editing actions while playing
        is_stopped = not is_playing
        self.frame_list.setEnabled(is_stopped)
        self.btn_add_frame.setEnabled(is_stopped)
        self.btn_duplicate_frame.setEnabled(is_stopped)
        self.btn_delete_frame.setEnabled(is_stopped)

    def _on_frame_changed(self, index: int):
        self.frame_list.blockSignals(True)
        if 0 <= index < self.frame_list.count():
            self.frame_list.setCurrentRow(index)
        self.frame_list.blockSignals(False)

    def _on_list_selection_changed(self, index: int):
        if index >= 0:
            self.controller.go_to_frame(index)

    def _on_add_frame(self):
        doc = self.controller.document
        if not doc:
            return
            
        from pixeart.core.frame import Frame
        from pixeart.core.layer import Layer
        new_frame = Frame()
        new_frame.add_layer(Layer("Katman"))
        
        # Insert after current active frame
        insert_idx = doc.active_frame_index + 1 if doc.active_frame_index >= 0 else 0
        doc.add_frame(new_frame, insert_idx)
        self.refresh_frames()
        self.controller.go_to_frame(insert_idx)

    def _on_duplicate_frame(self):
        doc = self.controller.document
        if not doc or doc.active_frame_index < 0:
            return
            
        doc.duplicate_frame(doc.active_frame_index)
        self.refresh_frames()
        self.controller.go_to_frame(doc.active_frame_index + 1)

    def _on_delete_frame(self):
        doc = self.controller.document
        if not doc or len(doc.frames) <= 1:
            # En az 1 kare kalmalı
            return
            
        doc.remove_frame(doc.active_frame_index)
        self.refresh_frames()
        self.controller.go_to_frame(doc.active_frame_index)
