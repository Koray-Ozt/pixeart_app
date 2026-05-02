import re

with open('pixeart/ui/widgets/timeline.py', 'r') as f:
    t_content = f.read()

# Remove fps UI elements
t_content = re.sub(r'\s*self\.lbl_fps.*?\n', '\n', t_content)
t_content = re.sub(r'\s*self\.spin_fps.*?\n', '\n', t_content)
t_content = re.sub(r'\s*controls_layout\.addWidget\(self\.lbl_fps\)\n', '\n', t_content)
t_content = re.sub(r'\s*controls_layout\.addWidget\(self\.spin_fps\)\n', '\n', t_content)
t_content = re.sub(r'\s*self\.spin_fps\.valueChanged\.connect\(self\.controller\.set_fps\)\n', '\n', t_content)

with open('pixeart/ui/widgets/timeline.py', 'w') as f:
    f.write(t_content)

with open('pixeart/ui/animation_controller.py', 'r') as f:
    a_content = f.read()

a_content = re.sub(r'\s*def set_fps\(self, fps: int\):.*?self\._fps = max\(1, fps\)', '', a_content, flags=re.DOTALL)
a_content = re.sub(r'\s*self\._fps = \d+\n', '\n', a_content)
# Add _update_timer_interval calls
a_content = re.sub(r'(self\.document\.set_active_frame\(index\)\n\s*)(self\.frame_changed\.emit\(index\))', r'\1self._update_timer_interval()\n        \2', a_content)
a_content = re.sub(r'(if self\._is_playing:\n\s*)(self\._timer\.start\(\))', r'\1self._update_timer_interval()\n            \2', a_content)


with open('pixeart/ui/animation_controller.py', 'w') as f:
    f.write(a_content)
