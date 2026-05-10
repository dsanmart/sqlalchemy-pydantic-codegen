from __future__ import annotations

from pathlib import Path

import pytest

from sqlalchemy_pydantic_codegen.core.cleaner import clean_models, clean_schema_file


@pytest.fixture
def schema_file(tmp_path: Path) -> Path:
    """Creates a temporary schema file for testing."""
    content = """from typing import Any, Union

class UserRow(BaseModel):
    id: int

class PostSchema(BaseModel):
    id: int | None = None
    title: str | None = None
    author: Union[UserRow, None]
    metadata: list[dict[str, Any]] | dict[str, Any] | None
"""
    schema_path = tmp_path / "post.py"
    schema_path.write_text(content)
    return schema_path


def test_clean_schema_file_defaults(schema_file: Path):
    """Tests the default cleaning operations."""
    original_content = schema_file.read_text()
    assert "Union[UserRow, None]" in original_content

    clean_schema_file(schema_file)

    cleaned_content = schema_file.read_text()
    assert "Union[UserRow, None]" not in cleaned_content
    assert "author: UserRow | None" in cleaned_content


def test_clean_schema_file_with_mapping(schema_file: Path):
    """Tests cleaning with custom model mappings."""
    field_map = {"metadata": "MetadataModel"}
    custom_imports = {"MetadataModel": "from .custom_types import MetadataModel"}

    clean_schema_file(schema_file, field_map, custom_imports)

    cleaned_content = schema_file.read_text()

    assert "from .custom_types import MetadataModel" in cleaned_content
    assert "metadata: MetadataModel | None" in cleaned_content
    assert "list[dict[str, Any]] | dict[str, Any] | None" not in cleaned_content


def test_clean_models_rewrites_nulltype_columns(tmp_path: Path):
    """NullType columns (e.g. pgvector) must be rewritten to an importable
    form — otherwise SQLAlchemy raises MappedAnnotationError at import time."""
    raw = tmp_path / "raw.py"
    raw.write_text(
        "class HostReplyEmbedding(Base):\n"
        "    __tablename__ = 'host_reply_embedding'\n"
        "    embedding: Mapped[Any] = mapped_column(NullType)\n"
    )
    out = tmp_path / "out.py"

    clean_models(raw, out)
    cleaned = out.read_text()

    assert "Mapped[Any] = mapped_column(NullType)" not in cleaned
    assert "embedding: Mapped[Optional[list]] = mapped_column(ARRAY(REAL))" in cleaned


def test_clean_models_warns_on_nulltype(tmp_path: Path, caplog):
    """Rewriting NullType is lossy — users need to see a warning naming the
    column so they can fix it upstream if they want high-fidelity types."""
    import logging

    raw = tmp_path / "raw.py"
    raw.write_text(
        "class HostReplyEmbedding(Base):\n"
        "    embedding: Mapped[Any] = mapped_column(NullType)\n"
    )
    out = tmp_path / "out.py"

    with caplog.at_level(logging.WARNING):
        clean_models(raw, out)

    assert any(
        "embedding" in record.message and "NullType" in record.message
        for record in caplog.records
    )


def test_clean_models_leaves_other_columns_untouched(tmp_path: Path):
    raw = tmp_path / "raw.py"
    raw.write_text(
        "class Foo(Base):\n"
        "    name: Mapped[str] = mapped_column(String)\n"
        "    embedding: Mapped[Any] = mapped_column(NullType)\n"
        "    count: Mapped[int] = mapped_column(Integer)\n"
    )
    out = tmp_path / "out.py"

    clean_models(raw, out)
    cleaned = out.read_text()

    assert "name: Mapped[str] = mapped_column(String)" in cleaned
    assert "count: Mapped[int] = mapped_column(Integer)" in cleaned
    assert "Mapped[Optional[list]] = mapped_column(ARRAY(REAL))" in cleaned
