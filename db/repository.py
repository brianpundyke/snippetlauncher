"""
Repository layer — all database operations live here.
The CLI and UI call these functions; they never touch SQLAlchemy directly.
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from .models import Category, Snippet, Tag, snippet_tags


# ---------------------------------------------------------------------------
# Category helpers
# ---------------------------------------------------------------------------

def list_categories(session: Session) -> list[Category]:
    return session.query(Category).order_by(Category.name).all()


def get_category(session: Session, name_or_id: str | int) -> Optional[Category]:
    if isinstance(name_or_id, int):
        return session.get(Category, name_or_id)
    return session.query(Category).filter_by(name=name_or_id).first()


def create_category(
    session: Session,
    name: str,
    description: str = "",
    colour: str = "#5294e2",
    icon: str = "code-symbolic",
) -> Category:
    cat = Category(name=name, description=description, colour=colour, icon=icon)
    session.add(cat)
    session.commit()
    session.refresh(cat)
    return cat


def delete_category(session: Session, name_or_id: str | int) -> bool:
    cat = get_category(session, name_or_id)
    if not cat:
        return False
    session.delete(cat)
    session.commit()
    return True


# ---------------------------------------------------------------------------
# Tag helpers
# ---------------------------------------------------------------------------

def get_or_create_tag(session: Session, name: str) -> Tag:
    tag = session.query(Tag).filter_by(name=name.lower().strip()).first()
    if not tag:
        tag = Tag(name=name.lower().strip())
        session.add(tag)
        session.flush()
    return tag


def list_tags(session: Session) -> list[Tag]:
    return session.query(Tag).order_by(Tag.name).all()


# ---------------------------------------------------------------------------
# Snippet CRUD
# ---------------------------------------------------------------------------

def create_snippet(
    session: Session,
    title: str,
    body: str,
    category: str | None = None,
    description: str = "",
    language: str = "bash",
    tags: list[str] | None = None,
    append_newline: bool = True,
) -> Snippet:
    cat = None
    if category:
        cat = get_category(session, category)
        if not cat:
            cat = create_category(session, category)

    snippet = Snippet(
        title=title,
        body=body,
        description=description,
        language=language,
        category=cat,
        is_multiline="\n" in body,
        append_newline=append_newline,
    )
    session.add(snippet)
    session.flush()

    for tag_name in (tags or []):
        snippet.tags.append(get_or_create_tag(session, tag_name))

    session.commit()
    session.refresh(snippet)
    return snippet


def get_snippet(session: Session, snippet_id: int) -> Optional[Snippet]:
    return session.get(Snippet, snippet_id)


def update_snippet(
    session: Session,
    snippet_id: int,
    **kwargs,
) -> Optional[Snippet]:
    snippet = get_snippet(session, snippet_id)
    if not snippet:
        return None

    allowed = {"title", "body", "description", "language", "append_newline"}
    for key, val in kwargs.items():
        if key in allowed:
            setattr(snippet, key, val)

    if "category" in kwargs:
        cat_name = kwargs["category"]
        snippet.category = get_category(session, cat_name) if cat_name else None

    if "tags" in kwargs:
        snippet.tags = [get_or_create_tag(session, t) for t in kwargs["tags"]]

    snippet.updated_at = datetime.utcnow()
    session.commit()
    session.refresh(snippet)
    return snippet


def delete_snippet(session: Session, snippet_id: int) -> bool:
    snippet = get_snippet(session, snippet_id)
    if not snippet:
        return False
    session.delete(snippet)
    session.commit()
    return True


def record_use(session: Session, snippet_id: int) -> None:
    """Increment use counter and record timestamp."""
    snippet = get_snippet(session, snippet_id)
    if snippet:
        snippet.use_count += 1
        snippet.last_used = datetime.utcnow()
        session.commit()


# ---------------------------------------------------------------------------
# Search / filter
# ---------------------------------------------------------------------------

def search_snippets(
    session: Session,
    query: str = "",
    category: str | None = None,
    tags: list[str] | None = None,
    limit: int = 50,
) -> list[Snippet]:
    """
    Full-text search across title, body, and description.
    Optionally filter by category name and/or tags.
    Results ordered by: use_count DESC, updated_at DESC.
    """
    q = session.query(Snippet)

    if query:
        pattern = f"%{query}%"
        q = q.filter(
            or_(
                Snippet.title.ilike(pattern),
                Snippet.body.ilike(pattern),
                Snippet.description.ilike(pattern),
            )
        )

    if category:
        cat = get_category(session, category)
        if cat:
            q = q.filter(Snippet.category_id == cat.id)

    if tags:
        for tag_name in tags:
            tag = session.query(Tag).filter_by(name=tag_name.lower()).first()
            if tag:
                q = q.filter(Snippet.tags.contains(tag))

    q = q.order_by(Snippet.use_count.desc(), Snippet.updated_at.desc())
    return q.limit(limit).all()


def list_snippets(
    session: Session,
    category: str | None = None,
    limit: int = 200,
) -> list[Snippet]:
    return search_snippets(session, query="", category=category, limit=limit)
