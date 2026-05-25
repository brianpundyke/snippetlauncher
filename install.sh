#!/bin/bash
# =============================================================================
# SnippetLauncher — install.sh
# Installs SnippetLauncher for the current user only. No sudo required.
# =============================================================================

set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/.local/share/snippetlauncher"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
APP_NAME="Snippet Launcher"

# Colours
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()    { echo -e "${BLUE}▶${NC} $1"; }
success() { echo -e "${GREEN}✓${NC} $1"; }
warn()    { echo -e "${YELLOW}!${NC} $1"; }
error()   { echo -e "${RED}✗${NC} $1"; exit 1; }

echo ""
echo -e "${BLUE}╔══════════════════════════════════════╗${NC}"
echo -e "${BLUE}║      SnippetLauncher Installer       ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════╝${NC}"
echo ""

# -----------------------------------------------------------------------------
# 1. Check Python 3.11+
# -----------------------------------------------------------------------------
info "Checking Python version..."
if ! command -v python3 &>/dev/null; then
    error "Python 3 not found. Install with: sudo apt install python3"
fi

PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 11 ]; }; then
    error "Python 3.11+ required (found $PY_VERSION). Install with: sudo apt install python3.12"
fi
success "Python $PY_VERSION found"

# -----------------------------------------------------------------------------
# 2. Check python3-venv
# -----------------------------------------------------------------------------
info "Checking python3-venv..."
if ! python3 -m venv --help &>/dev/null; then
    error "python3-venv not found. Install with: sudo apt install python3-full python3-venv"
fi
success "python3-venv available"

# -----------------------------------------------------------------------------
# 3. Check Qt6 system libraries
# -----------------------------------------------------------------------------
info "Checking Qt6 system libraries..."
if python3 -c "from PyQt6.QtWidgets import QApplication" &>/dev/null 2>&1; then
    success "Qt6 system libraries found"
else
    # Not installed via pip yet — check for system Qt6
    if dpkg -l libqt6widgets6 &>/dev/null 2>&1 || dpkg -l libqt6gui6 &>/dev/null 2>&1; then
        success "Qt6 system libraries found"
    else
        warn "Qt6 system libraries may be missing."
        warn "If the app fails to launch, install with:"
        warn "  sudo apt install libqt6widgets6 libqt6gui6 libgl1"
        warn "Continuing install..."
    fi
fi

# -----------------------------------------------------------------------------
# 4. Check system clipboard tool (Wayland / X11)
# -----------------------------------------------------------------------------
info "Checking clipboard tools..."
SESSION="${XDG_SESSION_TYPE:-unknown}"
if [ "$SESSION" = "wayland" ]; then
    if ! command -v wl-copy &>/dev/null; then
        warn "wl-clipboard not found (needed for clipboard on Wayland)"
        warn "Install with: sudo apt install wl-clipboard"
        warn "Continuing install — clipboard features will not work until installed."
    else
        success "wl-clipboard found (Wayland)"
    fi
else
    if ! command -v xclip &>/dev/null && ! command -v xsel &>/dev/null; then
        warn "xclip/xsel not found (needed for clipboard on X11)"
        warn "Install with: sudo apt install xclip"
        warn "Continuing install — clipboard features will not work until installed."
    else
        success "Clipboard tool found (X11)"
    fi
fi

# -----------------------------------------------------------------------------
# 5. Copy app files to install dir
# -----------------------------------------------------------------------------
info "Installing app to $INSTALL_DIR ..."
mkdir -p "$INSTALL_DIR"

rsync -a --delete \
    --exclude='.git' \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='*.db' \
    "$REPO_DIR/" "$INSTALL_DIR/" 2>/dev/null || {
    # rsync may not be installed — fall back to cp
    cp -r "$REPO_DIR/." "$INSTALL_DIR/"
    rm -rf "$INSTALL_DIR/.git" "$INSTALL_DIR/.venv"
    find "$INSTALL_DIR" -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
    find "$INSTALL_DIR" -name '*.pyc' -delete 2>/dev/null || true
}
success "App files copied"

# -----------------------------------------------------------------------------
# 6. Create virtual environment
# -----------------------------------------------------------------------------
info "Creating virtual environment..."
python3 -m venv "$INSTALL_DIR/.venv"
success "Virtual environment created"

# -----------------------------------------------------------------------------
# 7. Install Python dependencies
# -----------------------------------------------------------------------------
info "Installing Python dependencies..."
"$INSTALL_DIR/.venv/bin/pip" install --quiet --upgrade pip
"$INSTALL_DIR/.venv/bin/pip" install --quiet -r "$INSTALL_DIR/requirements.txt"
success "Python dependencies installed"

# -----------------------------------------------------------------------------
# 8. Initialise database and seed examples
# -----------------------------------------------------------------------------
info "Initialising database..."
cd "$INSTALL_DIR"
PYTHONPATH="$INSTALL_DIR" "$INSTALL_DIR/.venv/bin/python" seed.py
success "Database initialised"

# -----------------------------------------------------------------------------
# 9. Create launcher script in ~/.local/bin
# -----------------------------------------------------------------------------
info "Creating launcher script..."
mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/snippetlauncher" << EOF
#!/bin/bash
cd "$INSTALL_DIR"
source .venv/bin/activate
exec python cli.py "\$@"
EOF
chmod +x "$BIN_DIR/snippetlauncher"
success "Launcher created at $BIN_DIR/snippetlauncher"

# -----------------------------------------------------------------------------
# 10. Create hotkey launcher script
# -----------------------------------------------------------------------------
info "Creating hotkey launcher script..."
cat > "$BIN_DIR/snippetlauncher-launch" << LAUNCHEOF
#!/bin/bash
cd "$INSTALL_DIR"
source .venv/bin/activate
exec python cli.py launch
LAUNCHEOF
chmod +x "$BIN_DIR/snippetlauncher-launch"
success "Hotkey launcher created at $BIN_DIR/snippetlauncher-launch"

# -----------------------------------------------------------------------------
# 11. Create .desktop file
# -----------------------------------------------------------------------------
info "Creating .desktop entry..."
mkdir -p "$DESKTOP_DIR"
cat > "$DESKTOP_DIR/snippetlauncher.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Snippet Launcher
Comment=Store, search and paste code snippets
Exec=$BIN_DIR/snippetlauncher ui
Icon=format-text-code
Categories=Utility;Development;
Terminal=false
StartupNotify=true
StartupWMClass=python3
EOF

update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
success ".desktop entry created"

# -----------------------------------------------------------------------------
# 12. Ensure ~/.local/bin is on PATH
# -----------------------------------------------------------------------------
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    info "Adding $BIN_DIR to PATH..."
    SHELL_RC=""
    if [ -f "$HOME/.zshrc" ]; then
        SHELL_RC="$HOME/.zshrc"
    elif [ -f "$HOME/.bashrc" ]; then
        SHELL_RC="$HOME/.bashrc"
    fi

    if [ -n "$SHELL_RC" ]; then
        echo "" >> "$SHELL_RC"
        echo "# Added by SnippetLauncher installer" >> "$SHELL_RC"
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
        export PATH="$BIN_DIR:$PATH"
        success "Added $BIN_DIR to PATH in $SHELL_RC"
        warn "Run 'source $SHELL_RC' or open a new terminal for the PATH to take effect"
    else
        warn "Could not find ~/.bashrc or ~/.zshrc — manually add:"
        warn "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    fi
else
    success "$BIN_DIR is already on your PATH"
fi
# -----------------------------------------------------------------------------
# Done
# -----------------------------------------------------------------------------
echo ""
echo -e "${GREEN}╔══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     Installation complete!  🎉       ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"
echo ""
echo "  Launch from terminal:  snippetlauncher ui"
echo "  Quick-pick popup:      snippetlauncher launch"
echo "  Or find it in your app menu: '$APP_NAME'"
echo ""
echo "  To register a global hotkey, go to:"
echo "  KDE:   System Settings → Shortcuts → Custom Shortcuts"
echo "         Command: bash -c '$BIN_DIR/snippetlauncher-launch'"
echo "  GNOME: Settings → Keyboard → Custom Shortcuts"
echo "         Command: $BIN_DIR/snippetlauncher-launch"
echo ""
