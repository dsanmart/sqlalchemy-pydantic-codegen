from __future__ import annotations

import sys
from pathlib import Path
from shutil import rmtree

import pytest

# Add fixtures to path to allow import
sys.path.append(str(Path(__file__).parent / "fixtures"))

from sqlalchemy_pydantic_codegen.core.generator import ModelGenerator, load_models


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

    # Clean up the created directory
    rmtree(output_dir)
