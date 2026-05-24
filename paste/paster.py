"""
paste.py — auto-type or clipboard-copy a snippet body.

Strategy:
  1. Detect X11 vs Wayland at runtime via XDG_SESSION_TYPE.
  2. On X11  → xdotool type  (most reliable)
  3. On Wayland + tool available → ydotool or wtype
  4. Fallback → wl-clipboard / xclip (copy to clipboard, notify user)
"""

from __future__ import annotations
import os
import shutil
import subprocess
import time


# ---------------------------------------------------------------------------
# Session detection
# ---------------------------------------------------------------------------

def get_session_type() -> str:
    """Return 'x11', 'wayland', or 'unknown'."""
    return os.environ.get("XDG_SESSION_TYPE", "unknown").lower()


def get_desktop() -> str:
    """Return 'kde', 'gnome', or the raw value."""
    raw = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    if "kde" in raw:
        return "kde"
    if "gnome" in raw:
        return "gnome"
    return raw


# ---------------------------------------------------------------------------
# Auto-type
# ---------------------------------------------------------------------------

def _type_x11(text: str) -> bool:
    """Use xdotool to type text on X11."""
    if not shutil.which("xdotool"):
        return False
    # Small sleep so the calling window can regain focus
    time.sleep(0.15)
    result = subprocess.run(
        ["xdotool", "type", "--clearmodifiers", "--", text],
        capture_output=True,
    )
    return result.returncode == 0


def _type_wayland_ydotool(text: str) -> bool:
    """Use ydotool to type text on Wayland (requires ydotoold daemon)."""
    if not shutil.which("ydotool"):
        return False
    time.sleep(0.15)
    result = subprocess.run(["ydotool", "type", "--", text], capture_output=True)
    return result.returncode == 0


def _type_wayland_wtype(text: str) -> bool:
    """Use wtype to type text on Wayland."""
    if not shutil.which("wtype"):
        return False
    time.sleep(0.15)
    result = subprocess.run(["wtype", "--", text], capture_output=True)
    return result.returncode == 0


# ---------------------------------------------------------------------------
# Clipboard fallback
# ---------------------------------------------------------------------------

def _copy_to_clipboard(text: str) -> bool:
    """Copy text to clipboard using wl-copy (Wayland) or xclip (X11)."""
    if shutil.which("wl-copy"):
        # wl-copy must stay alive to hold clipboard contents on Wayland.
        # Use Popen (non-blocking) so it does not freeze the Qt main thread.
        proc = subprocess.Popen(
            ["wl-copy"],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        proc.stdin.write(text.encode())
        proc.stdin.close()
        return True
    if shutil.which("xclip"):
        proc = subprocess.run(
            ["xclip", "-selection", "clipboard"],
            input=text.encode(), capture_output=True,
        )
        return proc.returncode == 0
    if shutil.which("xsel"):
        proc = subprocess.run(
            ["xsel", "--clipboard", "--input"],
            input=text.encode(), capture_output=True,
        )
        return proc.returncode == 0
    return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class PasteResult:
    def __init__(self, success: bool, method: str, message: str = ""):
        self.success = success
        self.method  = method   # "typed" | "clipboard" | "failed"
        self.message = message

    def __repr__(self):
        return f"<PasteResult method={self.method!r} success={self.success}>"


def paste_snippet(text: str, append_newline: bool = True) -> PasteResult:
    """
    Paste snippet text into the focused window.
    Tries auto-type first, falls back to clipboard.
    """
    body = text + ("\n" if append_newline else "")
    session = get_session_type()

    # --- X11 path ---
    if session == "x11":
        if _type_x11(body):
            return PasteResult(True, "typed", "Typed via xdotool")
        # xdotool missing — clipboard fallback
        if _copy_to_clipboard(text):
            return PasteResult(True, "clipboard",
                               "xdotool not found — copied to clipboard (Ctrl+V to paste)")
        return PasteResult(False, "failed",
                           "Install xdotool: sudo apt install xdotool")

    # --- Wayland path ---
    if session == "wayland":
        if _type_wayland_ydotool(body):
            return PasteResult(True, "typed", "Typed via ydotool")
        if _type_wayland_wtype(body):
            return PasteResult(True, "typed", "Typed via wtype")
        # Fallback to clipboard
        if _copy_to_clipboard(text):
            return PasteResult(True, "clipboard",
                               "Auto-type unavailable — copied to clipboard (Ctrl+V to paste)")
        return PasteResult(False, "failed",
                           "Install wl-clipboard: sudo apt install wl-clipboard")

    # --- Unknown session — clipboard only ---
    if _copy_to_clipboard(text):
        return PasteResult(True, "clipboard", "Copied to clipboard")
    return PasteResult(False, "failed", "Could not detect session or find paste tools")


def copy_to_clipboard(text: str) -> PasteResult:
    """Explicitly copy to clipboard without attempting to type."""
    if _copy_to_clipboard(text):
        return PasteResult(True, "clipboard", "Copied to clipboard")
    return PasteResult(False, "failed", "No clipboard tool found")


def copy_to_primary(text: str) -> PasteResult:
    """Copy to primary selection so middle-click pastes it."""
    if shutil.which("wl-copy"):
        proc = subprocess.Popen(
            ["wl-copy", "--primary"],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        proc.stdin.write(text.encode())
        proc.stdin.close()
        return PasteResult(True, "primary", "Ready to middle-click paste")
    if shutil.which("xclip"):
        proc = subprocess.run(
            ["xclip", "-selection", "primary"],
            input=text.encode(), capture_output=True,
        )
        if proc.returncode == 0:
            return PasteResult(True, "primary", "Ready to middle-click paste")
    if shutil.which("xsel"):
        proc = subprocess.run(
            ["xsel", "--primary", "--input"],
            input=text.encode(), capture_output=True,
        )
        if proc.returncode == 0:
            return PasteResult(True, "primary", "Ready to middle-click paste")
    return PasteResult(False, "failed", "No primary selection tool found")
