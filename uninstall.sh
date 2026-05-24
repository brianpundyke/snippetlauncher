#!/bin/bash
# =============================================================================
# SnippetLauncher — uninstall.sh
# Removes the app but preserves your snippet database by default.
# =============================================================================

set -e

INSTALL_DIR="$HOME/.local/share/snippetlauncher"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
DB_PATH="$HOME/.local/share/snippetlauncher/snippets.db"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()    { echo -e "${BLUE}▶${NC} $1"; }
success() { echo -e "${GREEN}✓${NC} $1"; }
warn()    { echo -e "${YELLOW}!${NC} $1"; }

echo ""
echo -e "${YELLOW}╔══════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║     SnippetLauncher Uninstaller      ║${NC}"
echo -e "${YELLOW}╚══════════════════════════════════════╝${NC}"
echo ""

# Ask about database
echo -e "${YELLOW}Your snippet database contains your personal snippets.${NC}"
read -p "Delete your snippet database too? [y/N]: " DELETE_DB
DELETE_DB="${DELETE_DB:-N}"

echo ""

# Remove launcher script
if [ -f "$BIN_DIR/snippetlauncher" ]; then
    info "Removing launcher script..."
    rm -f "$BIN_DIR/snippetlauncher"
    success "Launcher removed"
fi

# Remove .desktop file
if [ -f "$DESKTOP_DIR/snippetlauncher.desktop" ]; then
    info "Removing .desktop entry..."
    rm -f "$DESKTOP_DIR/snippetlauncher.desktop"
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
    success ".desktop entry removed"
fi

# Remove app files (preserve db unless asked)
if [ -d "$INSTALL_DIR" ]; then
    if [[ "$DELETE_DB" =~ ^[Yy]$ ]]; then
        info "Removing app and database..."
        rm -rf "$INSTALL_DIR"
        success "App and database removed"
    else
        info "Removing app files (preserving database)..."
        # Back up the db, wipe dir, restore db
        DB_BACKUP="/tmp/snippetlauncher_backup_$$.db"
        [ -f "$DB_PATH" ] && cp "$DB_PATH" "$DB_BACKUP"
        rm -rf "$INSTALL_DIR"
        if [ -f "$DB_BACKUP" ]; then
            mkdir -p "$INSTALL_DIR"
            mv "$DB_BACKUP" "$DB_PATH"
            success "App removed — database preserved at $DB_PATH"
        else
            success "App removed"
        fi
    fi
fi

echo ""
echo -e "${GREEN}SnippetLauncher has been uninstalled.${NC}"
if [[ ! "$DELETE_DB" =~ ^[Yy]$ ]] && [ -f "$DB_PATH" ]; then
    echo "Your snippets are saved at: $DB_PATH"
fi
echo ""
echo "  Note: if SnippetLauncher was pinned to your KDE Plasma panel,"
echo "  right-click the orphaned icon and select 'Unpin from Task Manager'."
echo ""
