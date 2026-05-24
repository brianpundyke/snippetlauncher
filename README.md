# SnippetLauncher

A keyboard-driven snippet manager for Linux desktops — works great on **KDE Plasma** and **GNOME**.

Store commands, code blocks, URLs and text fragments in categorised groups. Retrieve and paste them via a clean Qt GUI or a lightweight quick-pick popup triggered by a global hotkey.

![Snippet Launcher screenshot](docs/screenshot.png)

---

## Features

- 📁 User-defined categories (supabase, services, git, docker, etc.)
- 🔍 Live search across title, body and description
- 🖱️ Three paste modes: clipboard, middle-click, and copy-and-close
- 🔗 URLs in snippets are automatically detected and clickable
- ⌨️ Keyboard-driven quick-pick popup for hotkey-triggered access without opening the full GUI
- 💾 Local SQLite database — your data stays on your machine
- 🎨 Inherits your desktop theme (KDE Plasma and GNOME)
- ⌨️ Keyboard shortcuts for all common actions (Ctrl+C, Ctrl+M, Ctrl+Enter, Ctrl+E)
- 🖱️ Right-click context menu on snippets
- 💬 Hover tooltips show snippet description or body preview

---

## Requirements

- Python 3.11+
- `python3-venv`
- `wl-clipboard` (Wayland) or `xclip` (X11) for clipboard support

Install system dependencies on Ubuntu/Debian/Pop!_OS:

```bash
# Required
sudo apt install python3-full python3-venv

# Clipboard (pick one based on your session)
sudo apt install wl-clipboard     # Wayland (KDE Plasma, GNOME on Wayland)
sudo apt install xclip            # X11
```

---

## Installation

```bash
git clone https://github.com/brianpundyke/snippetlauncher.git
cd snippetlauncher
chmod +x install.sh
./install.sh
```

The installer will:
- Check your Python version and dependencies
- Copy the app to `~/.local/share/snippetlauncher/`
- Create a virtual environment and install Python packages
- Seed example snippets to get you started
- Create a `snippetlauncher` command in `~/.local/bin/`
- Register the app in your desktop application menu
- Add `~/.local/bin` to your PATH if needed

No `sudo` required.

---

## Usage

### GUI

Launch from your app menu, or from the terminal:

```bash
snippetlauncher ui
```

### Quick-pick popup

A lightweight keyboard-driven popup for fast snippet access without opening the full GUI:

```bash
snippetlauncher launch                        # all snippets
snippetlauncher launch --category supabase    # filtered to a category
snippetlauncher launch --primary              # copies to primary selection (middle-click paste)
```

In the popup:
- **Type** to filter snippets instantly
- **↑ ↓** to navigate
- **Enter** to copy to clipboard
- **Double-click** to copy to primary selection (middle-click paste)
- **Escape** to dismiss

### CLI

```bash
snippetlauncher list                          # list all snippets
snippetlauncher list --category git           # filter by category
snippetlauncher search "docker"               # search snippets
snippetlauncher add                           # add a snippet interactively
snippetlauncher show 5                        # print snippet body
snippetlauncher show 5 | bash                 # execute directly
snippetlauncher delete 5                      # delete a snippet
snippetlauncher category list                 # list categories
snippetlauncher category add "kubernetes"     # add a category
```

### Keyboard shortcuts (GUI)

| Action | Shortcut |
|---|---|
| Add snippet | Ctrl+N |
| Edit snippet | Ctrl+E |
| Copy to clipboard | Ctrl+C |
| Middle-click paste | Ctrl+M |
| Copy & close | Ctrl+Enter |
| Delete snippet | Delete |

---

## Global Hotkey Setup

Register a hotkey in your desktop settings pointing to `snippetlauncher launch`:

**KDE Plasma:**
System Settings → Shortcuts → Custom Shortcuts → New → Command/URL
- Trigger: e.g. `Meta+S`
- Action: `snippetlauncher launch`

**GNOME:**
Settings → Keyboard → Custom Shortcuts → Add
- Command: `snippetlauncher launch`
- Shortcut: e.g. `Super+S`

---

## Uninstall

```bash
bash ~/.local/share/snippetlauncher/uninstall.sh
```

Your snippet database is preserved by default. The uninstaller will ask before deleting it.

If the app was pinned to your KDE Plasma panel, right-click the orphaned icon and select **Unpin from Task Manager**.

---

## Roadmap

- [ ] Custom app icon
- [ ] Import/export (JSON, CSV)
- [ ] Flatpak packaging for Flathub
- [ ] Tag filtering in the GUI sidebar

---

## Contributing

Pull requests welcome. Please open an issue first to discuss significant changes.

## Licence

MIT
