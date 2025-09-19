from __future__ import annotations

from pathlib import Path

import pytest

from sqlalchemy_pydantic_codegen.core.cleaner import clean_schema_file


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
