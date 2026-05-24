"""
SQLAlchemy models for SnippetLauncher.
Database lives at $XDG_DATA_HOME/snippetlauncher/snippets.db
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey,
    Table, Boolean, create_engine
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker
import os

# ---------------------------------------------------------------------------
# XDG-compliant database path
# ---------------------------------------------------------------------------

def get_db_path() -> str:
    data_home = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
    db_dir = os.path.join(data_home, "snippetlauncher")
    os.makedirs(db_dir, exist_ok=True)
    return os.path.join(db_dir, "snippets.db")


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Association table: snippets <-> tags  (many-to-many)
# ---------------------------------------------------------------------------

snippet_tags = Table(
    "snippet_tags",
    Base.metadata,
    Column("snippet_id", Integer, ForeignKey("snippets.id", ondelete="CASCADE")),
    Column("tag_id",     Integer, ForeignKey("tags.id",     ondelete="CASCADE")),
)


# ---------------------------------------------------------------------------
# Category
# ---------------------------------------------------------------------------

class Category(Base):
    """User-defined categories, e.g. 'supabase', 'services', 'git'."""
    __tablename__ = "categories"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    name        = Column(String(100), unique=True, nullable=False)
    description = Column(Text, default="")
    colour      = Column(String(7), default="#5294e2")   # hex colour for UI badge
    icon        = Column(String(64), default="code-symbolic")  # icon name
    created_at  = Column(DateTime, default=datetime.utcnow)

    snippets    = relationship("Snippet", back_populates="category",
                               cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Category id={self.id} name={self.name!r}>"


# ---------------------------------------------------------------------------
# Tag
# ---------------------------------------------------------------------------

class Tag(Base):
    """Free-form tags for cross-category filtering."""
    __tablename__ = "tags"

    id   = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), unique=True, nullable=False)

    snippets = relationship("Snippet", secondary=snippet_tags, back_populates="tags")

    def __repr__(self):
        return f"<Tag {self.name!r}>"


# ---------------------------------------------------------------------------
# Snippet
# ---------------------------------------------------------------------------

class Snippet(Base):
    """The core model — a stored command, code block, or text fragment."""
    __tablename__ = "snippets"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    title       = Column(String(200), nullable=False)
    body        = Column(Text, nullable=False)           # the actual snippet content
    description = Column(Text, default="")              # optional human note
    language    = Column(String(32), default="bash")    # for syntax highlighting

    # behaviour flags
    is_multiline   = Column(Boolean, default=False)     # hint: paste as block, not typed
    append_newline = Column(Boolean, default=True)      # auto-press Enter after pasting

    # relations
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"),
                         nullable=True)
    category    = relationship("Category", back_populates="snippets")
    tags        = relationship("Tag", secondary=snippet_tags, back_populates="snippets")

    # usage tracking
    use_count  = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_used  = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<Snippet id={self.id} title={self.title!r}>"


# ---------------------------------------------------------------------------
# Engine / Session factory
# ---------------------------------------------------------------------------

def get_engine(db_path: str | None = None):
    path = db_path or get_db_path()
    return create_engine(f"sqlite:///{path}", echo=False)


def init_db(db_path: str | None = None):
    """Create all tables if they don't exist yet. Safe to call on every run."""
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)
    return engine


def get_session(engine=None):
    if engine is None:
        engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()
