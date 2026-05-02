from PyQt6.QtCore import QObject, QTimer, pyqtSignal

class AnimationController(QObject):
    frame_changed = pyqtSignal(int)
    playback_state_changed = pyqtSignal(bool)

    def __init__(self, document=None):
        super().__init__()
        self.document = document
        self._timer = QTimer()
        self._timer.timeout.connect(self.next_frame)
        self._is_playing = False

    def set_document(self, document):
        self.stop()
        self.document = document
        if self.document and self.document.frames:
            self.frame_changed.emit(self.document.active_frame_index)

    def _update_timer_interval(self):
        if not self.document or not self.document.frames:
            self._timer.setInterval(100)
            return
            
        frame = self.document.active_frame
        if frame:
            self._timer.setInterval(frame.duration_ms)
        else:
            self._timer.setInterval(100)

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    def play(self):
        if not self.document or len(self.document.frames) <= 1:
            return
        if not self._is_playing:
            self._is_playing = True
            self._update_timer_interval()
            self._timer.start()
            self.playback_state_changed.emit(True)

    def stop(self):
        if self._is_playing:
            self._is_playing = False
            self._timer.stop()
            self.playback_state_changed.emit(False)

    def toggle_playback(self):
        if self._is_playing:
            self.stop()
        else:
            self.play()

    def next_frame(self):
        if not self.document or not self.document.frames:
            return
            
        current = self.document.active_frame_index
        next_idx = (current + 1) % len(self.document.frames)
        self.document.set_active_frame(next_idx)
        self._update_timer_interval()
        self.frame_changed.emit(next_idx)

    def prev_frame(self):
        if not self.document or not self.document.frames:
            return
            
        current = self.document.active_frame_index
        prev_idx = (current - 1) % len(self.document.frames)
        self.document.set_active_frame(prev_idx)
        self._update_timer_interval()
        self.frame_changed.emit(prev_idx)

    def go_to_frame(self, index: int):
        if not self.document or not self.document.frames:
            return
        if 0 <= index < len(self.document.frames):
            self.document.set_active_frame(index)
            self._update_timer_interval()
            self.frame_changed.emit(index)
