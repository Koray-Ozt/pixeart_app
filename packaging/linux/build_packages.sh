#!/usr/bin/env bash
set -euo pipefail

VER=${1:-1.0.0-alpha}
PYTHON=${PYTHON:-python3}

echo "Building PixeArt ($VER)..."

$PYTHON -m pip install --upgrade pip
$PYTHON -m pip install -r requirements.txt pyinstaller || true

rm -rf build dist
pyinstaller --noconfirm --onefile --name PixeArt pixeart/main.py

# Prepare temporary package directory for system packages
PKGDIR=$(mktemp -d)
mkdir -p "$PKGDIR/usr/bin"
cp dist/PixeArt "$PKGDIR/usr/bin/pixeart"
chmod +x "$PKGDIR/usr/bin/pixeart"

mkdir -p "$PKGDIR/usr/share/applications" "$PKGDIR/usr/share/icons/hicolor/256x256/apps"
if [ -f pixeart/resources/icons/logo.png ]; then
  cp pixeart/resources/icons/logo.png "$PKGDIR/usr/share/icons/hicolor/256x256/apps/pixeart.png" || true
fi
cat > "$PKGDIR/usr/share/applications/pixeart.desktop" <<EOF
[Desktop Entry]
Name=PixeArt
Exec=/usr/bin/pixeart
Icon=pixeart
Type=Application
Categories=Graphics;2DGraphics;
EOF

# If fpm is available, create native packages
if command -v fpm >/dev/null 2>&1; then
  echo "Creating .deb, .rpm and pacman (Arch) with fpm..."
  fpm -s dir -t deb -n pixeart -v "$VER" -C "$PKGDIR" --description "PixeArt - Pixel art editor" .
  fpm -s dir -t rpm -n pixeart -v "$VER" -C "$PKGDIR" --description "PixeArt - Pixel art editor" .
  # Create pacman package for Arch-based distros
  fpm -s dir -t pacman -n pixeart -v "$VER" -C "$PKGDIR" --description "PixeArt - Pixel art editor" .
  mkdir -p artifacts
  # Move known package types into artifacts; use globs to catch pacman extensions
  mv -- *.deb *.rpm *.pkg.* artifacts/ 2>/dev/null || true
else
  echo "fpm not found; artifacts left in $PKGDIR for manual packaging."
fi

# Create a bundled tarball that includes the executable and resource files (icons, etc.)
BUNDLEDIR=$(mktemp -d)
mkdir -p "$BUNDLEDIR/pixeart"
cp -a dist/PixeArt "$BUNDLEDIR/pixeart/PixeArt"
if [ -d "pixeart/resources" ]; then
  cp -a pixeart/resources "$BUNDLEDIR/pixeart/resources"
fi
if [ -f "README.md" ]; then
  cp README.md "$BUNDLEDIR/"
fi
tar -czf pixeart-$VER.tar.gz -C "$BUNDLEDIR" .

mkdir -p artifacts
cp -a pixeart-$VER.tar.gz artifacts/ || true
echo "Artifacts:"
ls -la artifacts || true
echo "Done."
