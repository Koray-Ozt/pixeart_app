#!/usr/bin/env bash
set -euo pipefail

VER=${1:-1.0.0-alpha}
PYTHON=${PYTHON:-python3}

echo "Building PixeArt ($VER)..."

$PYTHON -m pip install --upgrade pip
$PYTHON -m pip install -r requirements.txt pyinstaller || true

rm -rf build dist
pyinstaller --noconfirm --onefile --name PixeArt pixeart/main.py

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

if command -v fpm >/dev/null 2>&1; then
  echo "Creating .deb and .rpm with fpm..."
  fpm -s dir -t deb -n pixeart -v "$VER" -C "$PKGDIR" --description "PixeArt - Pixel art editor" .
  fpm -s dir -t rpm -n pixeart -v "$VER" -C "$PKGDIR" --description "PixeArt - Pixel art editor" .
  mkdir -p artifacts
  mv *.deb *.rpm artifacts/ || true
else
  echo "fpm not found; artifacts left in $PKGDIR for manual packaging."
fi

tar -czf pixeart-$VER.tar.gz -C dist PixeArt
echo "Artifacts:"
ls -la artifacts || true
echo "Done."
