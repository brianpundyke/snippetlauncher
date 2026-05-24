"""
launcher/rofi.py — pipe snippets into rofi and return the chosen one.

Rofi is used as a dumb display engine; we own all the data and logic.
Requires: rofi (X11) or rofi-wayland (Wayland) to be installed.
"""

from __future__ import annotations
import subprocess
import shutil
from typing import Optional

from db.models import Snippet


# ---------------------------------------------------------------------------
# Rofi helpers
# ---------------------------------------------------------------------------

def _rofi_available() -> bool:
    return shutil.which("rofi") is not None


def _build_entry(snippet: Snippet) -> str:
    """Format a single rofi list entry."""
    cat = snippet.category.name if snippet.category else "uncategorised"
    tags = ", ".join(t.name for t in snippet.tags) if snippet.tags else ""
    tag_part = f"  [{tags}]" if tags else ""
    return f"{snippet.title}  —  {cat}{tag_part}  (#{snippet.id})"


def _parse_id(entry: str) -> Optional[int]:
    """Extract snippet ID from the selected rofi entry string."""
    try:
        return int(entry.rsplit("(#", 1)[1].rstrip(")"))
    except (IndexError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def rofi_pick(
    snippets: list[Snippet],
    prompt: str = "snippet",
) -> Optional[Snippet]:
    """
    Show snippets in rofi, return the chosen Snippet or None.
    """
    if not _rofi_available():
        raise RuntimeError(
            "rofi is not installed. Install with: sudo apt install rofi"
        )

    if not snippets:
        return None

    entries = [_build_entry(s) for s in snippets]
    stdin_data = "\n".join(entries).encode()

    result = subprocess.run(
        [
            "rofi",
            "-dmenu",
            "-i",                   # case-insensitive filter
            "-p", prompt,
            "-format", "s",         # return the selected string
            "-theme-str", (
                'window { width: 60%; } '
                'listview { lines: 12; } '
            ),
        ],
        input=stdin_data,
        capture_output=True,
    )

    if result.returncode != 0:
        # User pressed Escape
        return None

    selected = result.stdout.decode().strip()
    snippet_id = _parse_id(selected)
    if snippet_id is None:
        return None

    # Match back to original list
    for s in snippets:
        if s.id == snippet_id:
            return s
    return None


def rofi_pick_category(categories: list[str], prompt: str = "category") -> Optional[str]:
    """Show a list of category names in rofi; return chosen or None."""
    if not _rofi_available() or not categories:
        return None

    stdin_data = "\n".join(categories).encode()
    result = subprocess.run(
        ["rofi", "-dmenu", "-i", "-p", prompt],
        input=stdin_data,
        capture_output=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.decode().strip() or None
