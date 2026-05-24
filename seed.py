#!/usr/bin/env python3
"""
seed.py — populate the database with example categories and snippets.
Run once after installation:  python seed.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from db.models import init_db, get_session
import db.repository as repo

engine = init_db()
session = get_session(engine)

print("Seeding categories...")

# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------
cats = {
    "supabase":    ("#3fcf8e", "Supabase CLI and SQL helpers"),
    "services":    ("#f97316", "systemd service management"),
    "git":         ("#f05033", "Git commands and workflows"),
    "docker":      ("#2496ed", "Docker and Docker Compose"),
    "networking":  ("#a855f7", "Network diagnostics and config"),
    "system":      ("#64748b", "General system administration"),
}

for name, (colour, desc) in cats.items():
    if not repo.get_category(session, name):
        repo.create_category(session, name=name, colour=colour, description=desc)
        print(f"  ✓ category: {name}")

# ---------------------------------------------------------------------------
# Example snippets
# ---------------------------------------------------------------------------
snippets = [
    # supabase
    dict(title="Supabase start",        body="supabase start",                              category="supabase", language="bash", tags=["local-dev"]),
    dict(title="Supabase stop",         body="supabase stop",                               category="supabase", language="bash", tags=["local-dev"]),
    dict(title="Supabase db reset",     body="supabase db reset",                           category="supabase", language="bash", tags=["local-dev", "database"]),
    dict(title="Supabase status",       body="supabase status",                             category="supabase", language="bash"),
    dict(title="Supabase link project", body="supabase link --project-ref <project-ref>",   category="supabase", language="bash"),

    # services
    dict(title="Restart nginx",         body="sudo systemctl restart nginx",                category="services", language="bash", tags=["nginx"]),
    dict(title="Enable service",        body="sudo systemctl enable --now <service>",       category="services", language="bash"),
    dict(title="Service status",        body="sudo systemctl status <service>",             category="services", language="bash"),
    dict(title="List failed units",     body="systemctl --failed",                          category="services", language="bash"),
    dict(title="Reload daemon",         body="sudo systemctl daemon-reload",                category="services", language="bash"),
    dict(title="Journal follow",        body="sudo journalctl -u <service> -f",             category="services", language="bash", tags=["logs"]),

    # git
    dict(title="Git log pretty",        body="git log --oneline --graph --decorate --all",  category="git",      language="bash"),
    dict(title="Git undo last commit",  body="git reset --soft HEAD~1",                    category="git",      language="bash"),
    dict(title="Git stash all",         body="git stash push -u -m 'wip'",                 category="git",      language="bash"),
    dict(title="Git delete merged",     body="git branch --merged | grep -v '\\*\\|main\\|master' | xargs git branch -d", category="git", language="bash"),

    # docker
    dict(title="Docker ps all",         body="docker ps -a",                               category="docker",   language="bash"),
    dict(title="Docker prune all",      body="docker system prune -af --volumes",          category="docker",   language="bash", tags=["cleanup"]),
    dict(title="Compose up detached",   body="docker compose up -d",                       category="docker",   language="bash"),
    dict(title="Compose logs follow",   body="docker compose logs -f",                     category="docker",   language="bash", tags=["logs"]),

    # networking
    dict(title="List open ports",       body="ss -tulnp",                                  category="networking", language="bash"),
    dict(title="Check DNS",             body="dig +short <domain>",                        category="networking", language="bash"),
    dict(title="Ping sweep",            body="nmap -sn 192.168.1.0/24",                    category="networking", language="bash"),

    # system
    dict(title="Disk usage human",      body="df -h",                                      category="system",   language="bash"),
    dict(title="Find large files",      body="du -ah / 2>/dev/null | sort -rh | head -20", category="system",   language="bash"),
    dict(title="Who is logged in",      body="w",                                          category="system",   language="bash"),
    dict(title="Watch processes",       body="watch -n1 'ps aux --sort=-%cpu | head -20'", category="system",   language="bash"),
]

print("\nSeeding snippets...")
for s in snippets:
    existing = repo.search_snippets(session, query=s["title"], category=s.get("category"))
    if not any(e.title == s["title"] for e in existing):
        snippet = repo.create_snippet(session, **s)
        print(f"  ✓ #{snippet.id} {snippet.title}")
    else:
        print(f"  · skipped (exists): {s['title']}")

print("\nDone! Run: python cli.py list")
