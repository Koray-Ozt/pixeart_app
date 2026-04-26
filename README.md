<div align="center">
  <img src="pixeart/resources/icons/logo.png" alt="PixeArt Logo" width="200" />
  
  # PixeArt

  <b>A Modern, High-Performance Pixel Art Editor built with Python & PyQt6</b>
</div>

<br/>

PixeArt is an Aseprite-inspired, professional-grade pixel art editor designed for game developers, digital artists, and pixel enthusiasts. It offers a sleek dark-themed interface, advanced grid systems, symmetry drawing, and robust layer management—providing everything you need to create stunning digital art.

## ✨ Features

*   **Modern Workspace**: Fully customizable and dockable panels (Tools, Layers, Palette, History, Navigator) with a premium dark theme.
*   **Essential Drawing Tools**: Pixel-perfect Pencil, Eraser, Fill Bucket, Color Picker, and Selection tools (Rectangle & Lasso).
*   **Advanced Grid System**: 1x1 Pixel grid, customizable tile grids, and "Snap to Grid" functionality.
*   **Tiled Mode**: Seamlessly create repeating patterns and textures with Tiling on the X, Y, or both axes.
*   **Symmetry Drawing**: Real-time vertical, horizontal, and quad (both) symmetry modes to speed up your workflow.
*   **Layer Management**: Full support for creating, hiding, and ordering multiple layers.
*   **Non-Destructive Workflow**: Unlimited History with robust Undo/Redo tracking.
*   **Pro Navigator**: Mini-map viewport with extreme zoom capabilities (10% to 5000%).
*   **File Formats**: Save and load custom `.pixe` project files, and export to standard image formats.

## 🚀 Installation

### Prerequisites
*   Python 3.10 or higher

### Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Koray-Ozt/pixeart_app.git
   cd pixeart_app
   ```

2. **Create a virtual environment (Recommended):**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Launch PixeArt:**
   ```bash
   python pixeart/main.py
   ```

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
| :--- | :--- |
| `B` | Pencil Tool |
| `E` | Eraser Tool |
| `G` | Fill Bucket |
| `I` | Color Picker |
| `M` | Selection Tool |
| `Ctrl+N` | New Project |
| `Ctrl+O` | Open Project |
| `Ctrl+S` | Save Project |
| `Ctrl+E` | Export Image |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |
| `F11` | Full Screen |

## 🛠️ Architecture

PixeArt is built on a clean, modular architecture:
*   `core/`: Core state management containing `Document`, `Layer`, and `History` logic.
*   `ui/`: Signal-driven PyQt6 interface, containing the `CanvasView`, `MainWindow`, and `widgets` (Docks).
*   `tools/`: Tool behaviors and canvas interaction logic.

## 📄 License

This project is licensed under the terms of the MIT license. See the `LICENSE` file for details.
