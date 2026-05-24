#!/usr/bin/env python3
"""
snippetlauncher CLI
===================
Usage examples:

  # Launch rofi picker and auto-paste chosen snippet
  snippetlauncher launch

  # Launch picker filtered to a category
  snippetlauncher launch --category supabase

  # Add a new snippet interactively
  snippetlauncher add

  # Add non-interactively (great for scripts / pipe)
  snippetlauncher add --title "Restart nginx" --body "sudo systemctl restart nginx" --category services

  # List all snippets
  snippetlauncher list

  # List snippets in a category
  snippetlauncher list --category git

  # Search snippets
  snippetlauncher search "docker ps"

  # Show a snippet's body (for piping)
  snippetlauncher show 42

  # Delete a snippet
  snippetlauncher delete 42

  # Manage categories
  snippetlauncher category list
  snippetlauncher category add "kubernetes" --colour "#326ce5"
  snippetlauncher category delete "old-stuff"
"""

import sys
import click
from rich.console import Console
from rich.table import Table
from rich import box

from db.models import init_db, get_session
import db.repository as repo
from paste.paster import copy_to_clipboard

console = Console()


# ---------------------------------------------------------------------------
# Shared session context
# ---------------------------------------------------------------------------

@click.group()
@click.pass_context
def cli(ctx):
    """SnippetLauncher — store, search, and paste snippets from the CLI."""
    engine = init_db()
    ctx.ensure_object(dict)
    ctx.obj["session"] = get_session(engine)


def get_db(ctx):
    return ctx.obj["session"]


# ---------------------------------------------------------------------------
# launch
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--category", "-c", default=None, help="Filter by category name")
@click.option("--primary", is_flag=True, help="Copy to primary selection (middle-click paste)")
@click.pass_context
def launch(ctx, category, primary):
    """Open the quick-pick popup and copy the chosen snippet."""
    from launcher.popup import run_popup
    mode = "primary" if primary else "clipboard"
    run_popup(category=category, mode=mode)


# ---------------------------------------------------------------------------
# add
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--title", "-t", default=None)
@click.option("--body",  "-b", default=None)
@click.option("--category", "-c", default=None)
@click.option("--description", "-d", default="")
@click.option("--language", "-l", default="bash")
@click.option("--tags", default="", help="Comma-separated tags")
@click.option("--no-newline", is_flag=True, help="Don't append newline when pasting")
@click.pass_context
def add(ctx, title, body, category, description, language, tags, no_newline):
    """Add a new snippet (interactive if --title/--body omitted)."""
    session = get_db(ctx)

    if not title:
        title = click.prompt("Title")
    if not body:
        console.print("[dim]Enter snippet body (Ctrl+D to finish):[/dim]")
        lines = []
        try:
            while True:
                lines.append(input())
        except EOFError:
            pass
        body = "\n".join(lines)

    if not category:
        cats = [c.name for c in repo.list_categories(session)]
        if cats:
            console.print(f"[dim]Categories: {', '.join(cats)}[/dim]")
        category = click.prompt("Category (leave blank for none)", default="")
        category = category.strip() or None

    tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    snippet = repo.create_snippet(
        session,
        title=title,
        body=body,
        category=category,
        description=description,
        language=language,
        tags=tag_list,
        append_newline=not no_newline,
    )
    console.print(f"[green]✓ Snippet #{snippet.id} '{snippet.title}' saved.[/green]")


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------

@cli.command("list")
@click.option("--category", "-c", default=None)
@click.pass_context
def list_snippets(ctx, category):
    """List all snippets, optionally filtered by category."""
    session = get_db(ctx)
    snippets = repo.list_snippets(session, category=category)

    if not snippets:
        console.print("[yellow]No snippets found.[/yellow]")
        return

    table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold cyan")
    table.add_column("ID",       style="dim",    width=5)
    table.add_column("Title",    style="bold",   width=30)
    table.add_column("Category", style="yellow", width=18)
    table.add_column("Tags",     style="cyan",   width=20)
    table.add_column("Lang",     style="dim",    width=8)
    table.add_column("Uses",     style="green",  width=5)

    for s in snippets:
        cat  = s.category.name if s.category else "—"
        tags = ", ".join(t.name for t in s.tags) if s.tags else "—"
        table.add_row(str(s.id), s.title, cat, tags, s.language, str(s.use_count))

    console.print(table)


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("query")
@click.option("--category", "-c", default=None)
@click.pass_context
def search(ctx, query, category):
    """Search snippets by title, body, or description."""
    session = get_db(ctx)
    snippets = repo.search_snippets(session, query=query, category=category)

    if not snippets:
        console.print(f"[yellow]No results for '{query}'.[/yellow]")
        return

    for s in snippets:
        cat = s.category.name if s.category else "—"
        console.print(f"[bold]#{s.id}[/bold]  [cyan]{s.title}[/cyan]  [dim]({cat})[/dim]")
        # Show first line of body as preview
        preview = s.body.splitlines()[0][:80]
        console.print(f"     [dim]{preview}[/dim]")


# ---------------------------------------------------------------------------
# show
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("snippet_id", type=int)
@click.pass_context
def show(ctx, snippet_id):
    """Print the body of a snippet (useful for piping: snippetlauncher show 5 | bash)."""
    session = get_db(ctx)
    snippet = repo.get_snippet(session, snippet_id)
    if not snippet:
        console.print(f"[red]Snippet #{snippet_id} not found.[/red]")
        sys.exit(1)
    # Raw print so it can be piped cleanly
    print(snippet.body)


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("snippet_id", type=int)
@click.confirmation_option(prompt="Are you sure?")
@click.pass_context
def delete(ctx, snippet_id):
    """Delete a snippet by ID."""
    session = get_db(ctx)
    if repo.delete_snippet(session, snippet_id):
        console.print(f"[green]✓ Snippet #{snippet_id} deleted.[/green]")
    else:
        console.print(f"[red]Snippet #{snippet_id} not found.[/red]")
        sys.exit(1)


# ---------------------------------------------------------------------------
# category subcommand group
# ---------------------------------------------------------------------------

@cli.group()
def category():
    """Manage snippet categories."""
    pass


@category.command("list")
@click.pass_context
def category_list(ctx):
    session = get_db(ctx)
    cats = repo.list_categories(session)
    if not cats:
        console.print("[yellow]No categories yet.[/yellow]")
        return

    table = Table(box=box.SIMPLE_HEAVY, header_style="bold cyan")
    table.add_column("ID",          width=5)
    table.add_column("Name",        width=20)
    table.add_column("Colour",      width=9)
    table.add_column("Description", width=40)
    table.add_column("Snippets",    width=8)

    for c in cats:
        table.add_row(
            str(c.id), c.name, c.colour, c.description, str(len(c.snippets))
        )
    console.print(table)


@category.command("add")
@click.argument("name")
@click.option("--colour", default="#5294e2", help="Hex colour for UI badge")
@click.option("--description", "-d", default="")
@click.pass_context
def category_add(ctx, name, colour, description):
    session = get_db(ctx)
    cat = repo.create_category(session, name=name, colour=colour, description=description)
    console.print(f"[green]✓ Category '{cat.name}' created (id={cat.id}).[/green]")


@category.command("delete")
@click.argument("name")
@click.confirmation_option(prompt="Delete category and reassign its snippets to null?")
@click.pass_context
def category_delete(ctx, name):
    session = get_db(ctx)
    if repo.delete_category(session, name):
        console.print(f"[green]✓ Category '{name}' deleted.[/green]")
    else:
        console.print(f"[red]Category '{name}' not found.[/red]")
        sys.exit(1)


# ---------------------------------------------------------------------------
# UI command
# ---------------------------------------------------------------------------

@cli.command()
def ui():
    """Open the graphical management window."""
    from ui.app import run
    run()


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli(obj={})
