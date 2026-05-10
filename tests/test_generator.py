from __future__ import annotations

import sys
from pathlib import Path
from shutil import rmtree

import pytest
from sqlalchemy.sql.sqltypes import NullType

# Add fixtures to path to allow import
sys.path.append(str(Path(__file__).parent / "fixtures"))

from sqlalchemy_pydantic_codegen.core.generator import ModelGenerator, load_models  # noqa: E402


@pytest.fixture(scope="module")
def sample_models_module():
    # This ensures the module is loaded once per test session
    from tests.fixtures import sample_models

    return sample_models


@pytest.fixture
def generator(tmp_path: Path):
    """Fixture to create a ModelGenerator instance with a temporary output directory."""
    template_dir = (
        Path(__file__).parent.parent / "src/sqlalchemy_pydantic_codegen/templates"
    )
    output_dir = tmp_path / "models"
    return ModelGenerator(output_dir=output_dir, template_dir=template_dir)


def test_load_models(sample_models_module):
    """Tests that SQLAlchemy models are loaded correctly from a module."""
    mappers = load_models("tests.fixtures.sample_models")
    assert len(mappers) == 2
    class_names = {m.class_.__name__ for m in mappers}
    assert "User" in class_names
    assert "Post" in class_names


def test_generate_models(generator: ModelGenerator, sample_models_module):
    """Tests the full model generation process."""
    mappers = load_models("tests.fixtures.sample_models")
    generator.generate_models(mappers)

    output_dir = generator.output_dir
    assert (output_dir / "__init__.py").exists()
    assert (output_dir / "user.py").exists()
    assert (output_dir / "post.py").exists()
    for fname, schema in [("user.py", "User"), ("post.py", "Post")]:
        content = (output_dir / fname).read_text()
        assert f"class {schema}Schema(BaseModel):" in content
        assert f"class {schema}Row({schema}Schema):" in content
        assert f"class {schema}Insert({schema}Schema):" in content
        assert f"class {schema}Update({schema}Schema):" in content

    user_content = (output_dir / "user.py").read_text()
    print(user_content)
    assert "class UserSchema(BaseModel):" in user_content
    assert "id: UUID | None = Field(default=None)" in user_content
    assert "name: str | None = Field(default=None)" in user_content
    assert "email: str | None = Field(default=None)" in user_content

    post_content = (output_dir / "post.py").read_text()
    print(post_content)
    assert "class PostSchema(BaseModel):" in post_content
    assert "title: str | None = Field(default=None)" in post_content
    assert "content: str | None = Field(default=None)" in post_content

    # Verify relationship fields are generated
    assert "author: UserRow | None = None" in post_content
    assert "posts: list[PostRow] = []" in user_content

    # Verify validators are generated for models with relationships
    assert "_extract_attrs" in user_content
    assert "_extract_attrs" in post_content
    assert "model_validator" in user_content
    assert "model_validator" in post_content

    # Verify cyclic reference validators are generated
    assert "_drop_cyclic_posts" in user_content
    assert "_drop_cyclic_author" in post_content

    # Verify dict early-return in _extract_attrs
    assert "if isinstance(obj, dict):" in user_content
    assert "if isinstance(obj, dict):" in post_content

    # Clean up the created directory
    rmtree(output_dir)


def test_load_models_accepts_mapped_any_nulltype(tmp_path: Path):
    """sqlacodegen emits `Mapped[Any] = mapped_column(NullType)` for unknown
    DB types (pgvector's vector, tsvector, geometry, custom domains).
    load_models registers Any -> NULLTYPE in sqltypes._type_map so SQLAlchemy
    accepts the annotation instead of raising MappedAnnotationError."""
    module_dir = tmp_path / "nulltype_pkg"
    module_dir.mkdir()
    (module_dir / "__init__.py").write_text("")
    (module_dir / "nulltype_models.py").write_text(
        "from typing import Any\n"
        "from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column\n"
        "from sqlalchemy.sql.sqltypes import NullType\n"
        "\n"
        "class Base(DeclarativeBase):\n"
        "    pass\n"
        "\n"
        "class Embed(Base):\n"
        "    __tablename__ = 'embed'\n"
        "    id: Mapped[int] = mapped_column(primary_key=True)\n"
        "    embedding: Mapped[Any] = mapped_column(NullType)\n"
    )

    sys.path.insert(0, str(tmp_path))
    try:
        mappers = load_models("nulltype_pkg.nulltype_models")
        embed = next(m for m in mappers if m.class_.__name__ == "Embed")
        embedding_col = embed.columns["embedding"]
        assert isinstance(embedding_col.type, NullType)
    finally:
        sys.path.remove(str(tmp_path))
        for name in list(sys.modules):
            if name.startswith("nulltype_pkg"):
                del sys.modules[name]
