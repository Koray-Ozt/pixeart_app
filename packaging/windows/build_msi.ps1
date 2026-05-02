param(
  [string]$Version = "1.0.0-alpha"
)

# Requires WiX Toolset (heat.exe, candle.exe, light.exe) on PATH
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$root = Resolve-Path "$scriptDir/../.."
$dist = Join-Path $root "dist"
Push-Location $scriptDir

if (-not (Test-Path $dist)) {
  throw "dist directory not found. Run PyInstaller first."
}

$harvest = Join-Path $scriptDir "pixeart.wxs"
& heat.exe dir $dist -dr INSTALLFOLDER -cg PixeArtFiles -sfrag -srd -out $harvest

& candle.exe -dVersion=$Version installer.wxs pixeart.wxs -out pixeart.wixobj
& light.exe pixeart.wixobj -out "pixeart-$Version.msi"

Pop-Location
