#!/bin/bash
set -e

APP_NAME="whack-a-hacker"
ARCH=$(uname -m)
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"

echo "=== Building Whack-a-Hacker AppImage (${ARCH}) ==="

# ---- Check dependencies ----
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found"
    exit 1
fi

if ! python3 -c "import pygame" 2>/dev/null; then
    echo "ERROR: pygame not installed. Run: sudo apt install python3-pygame"
    exit 1
fi

PYTHON_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PYTHON_BIN=$(readlink -f "$(which python3)")
echo "Using system Python ${PYTHON_VER} at ${PYTHON_BIN}"

# ---- Clean previous build ----
rm -rf ${SCRIPT_DIR}/build-appimage
mkdir -p build-appimage/AppDir/usr/bin
mkdir -p build-appimage/AppDir/usr/lib
mkdir -p build-appimage/AppDir/usr/share/fonts
mkdir -p build-appimage/AppDir/app
cd ${SCRIPT_DIR}/build-appimage
APPDIR="$(pwd)/AppDir"

# ---- Copy Python binary ----
echo "Copying Python binary..."
cp "${PYTHON_BIN}" "${APPDIR}/usr/bin/python3"
chmod +x "${APPDIR}/usr/bin/python3"

# ---- Copy Python standard library ----
echo "Copying Python standard library..."
STDLIB=$(python3 -c "import sysconfig; print(sysconfig.get_path('stdlib'))")
cp -r "${STDLIB}" "${APPDIR}/usr/lib/python${PYTHON_VER}"

# ---- Copy lib-dynload ----
DYNLOAD="${STDLIB}/lib-dynload"
if [ -d "${DYNLOAD}" ]; then
    echo "Copying lib-dynload..."
    cp -r "${DYNLOAD}" "${APPDIR}/usr/lib/python${PYTHON_VER}/"
fi

# ---- Copy dist-packages / site-packages (where pygame lives) ----
echo "Copying pygame and dependencies..."
mkdir -p "${APPDIR}/usr/lib/python${PYTHON_VER}/dist-packages"

# Check all possible locations for pygame
PYGAME_FOUND=false
for sp in \
    "/usr/lib/python3/dist-packages" \
    "/usr/lib/python${PYTHON_VER}/dist-packages" \
    "/usr/local/lib/python${PYTHON_VER}/dist-packages" \
    $(python3 -c "import site; print(' '.join(site.getsitepackages()))" 2>/dev/null) \
    $(python3 -c "import site; print(site.getusersitepackages())" 2>/dev/null); do
    if [ -d "$sp/pygame" ]; then
        echo "  Found pygame at: $sp/pygame"
        cp -r "$sp/pygame" "${APPDIR}/usr/lib/python${PYTHON_VER}/dist-packages/"
        cp -r "$sp/pygame"*.dist-info "${APPDIR}/usr/lib/python${PYTHON_VER}/dist-packages/" 2>/dev/null || true
        cp -r "$sp/pygame"*.egg-info "${APPDIR}/usr/lib/python${PYTHON_VER}/dist-packages/" 2>/dev/null || true
        PYGAME_FOUND=true
        break
    fi
done

if [ "$PYGAME_FOUND" = false ]; then
    echo "ERROR: Could not find pygame installation"
    exit 1
fi

# ---- Bundle shared libraries ----
echo "Bundling shared libraries..."
mkdir -p "${APPDIR}/usr/lib/bundled"

# System libs to skip (provided by every Linux system)
SKIP="linux-vdso|ld-linux|libc\.so|libm\.so|libdl\.so|librt\.so|libpthread|libresolv|libnss|libstdc\+\+"

# Collect all .so files in our AppDir
ALL_SOS=$(find "${APPDIR}" -name "*.so*" -type f 2>/dev/null)

# Add the python binary itself
ALL_BINS="${APPDIR}/usr/bin/python3 ${ALL_SOS}"

# Get their dependencies
for bin in ${ALL_BINS}; do
    if [ -f "$bin" ]; then
        ldd "$bin" 2>/dev/null | grep "=> /" | awk '{print $3}' | while read -r dep; do
            BASENAME=$(basename "$dep")
            if ! echo "$BASENAME" | grep -qE "${SKIP}"; then
                if [ ! -f "${APPDIR}/usr/lib/bundled/${BASENAME}" ]; then
                    cp "$dep" "${APPDIR}/usr/lib/bundled/" 2>/dev/null || true
                fi
            fi
        done
    fi
done

# Also grab libpython if not already bundled
LIBPYTHON=$(find /usr/lib -name "libpython${PYTHON_VER}*.so*" -type f 2>/dev/null | head -1)
if [ -n "$LIBPYTHON" ]; then
    cp "$LIBPYTHON" "${APPDIR}/usr/lib/bundled/" 2>/dev/null || true
    # Copy all symlinks too
    LIBPYTHON_DIR=$(dirname "$LIBPYTHON")
    for f in "${LIBPYTHON_DIR}"/libpython${PYTHON_VER}*; do
        cp -a "$f" "${APPDIR}/usr/lib/bundled/" 2>/dev/null || true
    done
fi

LIB_COUNT=$(ls "${APPDIR}/usr/lib/bundled/" 2>/dev/null | wc -l)
echo "  Bundled ${LIB_COUNT} shared libraries"

# ---- Copy fonts ----
echo "Copying fonts..."
for fdir in /usr/share/fonts/truetype/freefont \
            /usr/share/fonts/truetype/dejavu \
            /usr/share/fonts/truetype/liberation; do
    if [ -d "$fdir" ]; then
        cp -r "$fdir" "${APPDIR}/usr/share/fonts/" 2>/dev/null || true
    fi
done

# ---- Copy game files ----
echo "Copying game files..."
cp "${SCRIPT_DIR}/code/main.py" "${APPDIR}/app/"
cp -r "${SCRIPT_DIR}/code/assets" "${APPDIR}/app/" 2>/dev/null || mkdir -p "${APPDIR}/app/assets"

# ---- Create AppRun ----
echo "Creating AppRun..."
cat > "${APPDIR}/AppRun" << APPRUN
#!/bin/bash
set -e

SELF="\$(readlink -f "\$0")"
APPDIR="\${SELF%/*}"

export PATH="\${APPDIR}/usr/bin:\${PATH}"
export LD_LIBRARY_PATH="\${APPDIR}/usr/lib/bundled:\${APPDIR}/usr/lib:\${LD_LIBRARY_PATH}"
export PYTHONHOME="\${APPDIR}/usr"
export PYTHONPATH="\${APPDIR}/usr/lib/python${PYTHON_VER}:\${APPDIR}/usr/lib/python${PYTHON_VER}/dist-packages:\${APPDIR}/app"
export XDG_DATA_DIRS="\${APPDIR}/usr/share:\${XDG_DATA_DIRS}"
export FONTCONFIG_PATH="/etc/fonts"
export SDL_VIDEODRIVER="\${SDL_VIDEODRIVER:-x11}"

export WHACK_DATA_DIR="\${XDG_DATA_HOME:-\$HOME/.local/share}/whack-a-hacker"
mkdir -p "\${WHACK_DATA_DIR}"

# Install icon and .desktop file for the system to find
ICON_DIR="\${HOME}/.local/share/icons/hicolor/256x256/apps"
DESKTOP_DIR="\${HOME}/.local/share/applications"
mkdir -p "\${ICON_DIR}" "\${DESKTOP_DIR}"

if [ ! -f "\${ICON_DIR}/whack-a-hacker.png" ]; then
    cp "\${APPDIR}/whack-a-hacker.png" "\${ICON_DIR}/whack-a-hacker.png" 2>/dev/null || true
fi

# Create a .desktop file pointing to the actual AppImage location
APPIMAGE_PATH="\$(readlink -f "\${OWD:-\$(pwd)}/\$(basename "\${ARGV0:-\$0}")" 2>/dev/null || true)"
if [ -n "\${APPIMAGE}" ]; then
    APPIMAGE_PATH="\${APPIMAGE}"
fi
cat > "\${DESKTOP_DIR}/whack-a-hacker.desktop" << DESK
[Desktop Entry]
Type=Application
Name=Whack-a-Hacker
Comment=Cyber Security Whack-a-Mole Game
Exec=\${APPIMAGE_PATH}
Icon=whack-a-hacker
Categories=Game;ArcadeGame;
Terminal=false
DESK

cd "\${APPDIR}/app"
exec "\${APPDIR}/usr/bin/python3" main.py "\$@"
APPRUN
chmod +x "${APPDIR}/AppRun"

# ---- Create .desktop file ----
cat > "${APPDIR}/whack-a-hacker.desktop" << 'DESKTOP'
[Desktop Entry]
Type=Application
Name=Whack-a-Hacker
Comment=Cyber Security Whack-a-Mole Game
Exec=AppRun
Icon=whack-a-hacker
Categories=Game;ArcadeGame;
Terminal=false
DESKTOP

# ---- Generate icon ----
if [ -f "${SCRIPT_DIR}/whack-a-hacker.png" ]; then
    cp "${SCRIPT_DIR}/whack-a-hacker.png" "${APPDIR}/whack-a-hacker.png"
else
    echo "Generating icon..."
    python3 -c "
import pygame
pygame.init()
sz = 256
s = pygame.Surface((sz, sz), pygame.SRCALPHA)
pygame.draw.circle(s, (15, 15, 35), (128, 128), 120)
pygame.draw.circle(s, (0, 200, 255), (128, 128), 120, 4)
pygame.draw.rect(s, (140, 140, 150), (85, 40, 86, 50), border_radius=8)
pygame.draw.rect(s, (180, 180, 190), (85, 40, 86, 50), 4, border_radius=8)
pygame.draw.line(s, (160, 120, 60), (128, 90), (128, 200), 16)
pygame.draw.circle(s, (200, 40, 40), (128, 145), 30)
pygame.draw.rect(s, (200, 40, 40), (98, 170, 60, 40), border_radius=8)
pygame.draw.rect(s, (0, 255, 0), (112, 138, 10, 5))
pygame.draw.rect(s, (0, 255, 0), (134, 138, 10, 5))
f = pygame.font.SysFont('monospace', 22, bold=True)
t = f.render('WHACK', True, (0, 255, 200))
s.blit(t, (128 - t.get_width() // 2, 215))
pygame.image.save(s, '${APPDIR}/whack-a-hacker.png')
pygame.quit()
" 2>/dev/null || echo "WARNING: Could not generate icon"
fi

mkdir -p "${APPDIR}/usr/share/icons/hicolor/256x256/apps"
cp "${APPDIR}/whack-a-hacker.png" "${APPDIR}/usr/share/icons/hicolor/256x256/apps/" 2>/dev/null || true

# ---- Verify bundle ----
echo "Verifying Python starts..."
"${APPDIR}/AppRun" -c "import pygame; print(f'pygame {pygame.ver} OK')" 2>/dev/null && echo "  Verification passed!" || echo "  WARNING: Verification failed, AppImage may not work on other systems"

# ---- Download appimagetool ----
if [ ! -f appimagetool ]; then
    echo "Downloading appimagetool..."
    wget -v "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-${ARCH}.AppImage" \
        -O appimagetool
    chmod +x appimagetool
fi

# ---- Build AppImage ----
echo "Packaging AppImage..."
OUTPUT_DIR="${SCRIPT_DIR}/AppImages"
mkdir -p "${OUTPUT_DIR}"
ARCH=${ARCH} ./appimagetool "${APPDIR}" "${OUTPUT_DIR}/${APP_NAME}-${ARCH}.AppImage"

cd "${OUTPUT_DIR}"
chmod +x "${APP_NAME}-${ARCH}.AppImage"

SIZE=$(du -h "${APP_NAME}-${ARCH}.AppImage" | cut -f1)

# ---- Cleanup ----
cd ${SCRIPT_DIR}
rm -rf build-appimage

echo ""
echo "=== Done! ==="
echo "Output: ${APP_NAME}-${ARCH}.AppImage (${SIZE})"
echo "Run with: ./${APP_NAME}-${ARCH}.AppImage"
