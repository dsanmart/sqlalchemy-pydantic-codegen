"""Tests for the runtime behavior of generated Row model validators.

These tests construct Pydantic models that mirror what model.jinja2 generates,
then verify _extract_attrs (dict passthrough, ORM-object extraction,
MissingGreenlet handling) and _drop_cyclic_* (recursion pruning).
"""

from __future__ import annotations

from typing import Any, Callable

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)
from sqlalchemy.exc import MissingGreenlet


def _is_recursion_validation_error(exc: ValidationError) -> bool:
    errs = exc.errors()
    return len(errs) == 1 and errs[0]["type"] == "recursion_loop"


# ── Minimal models that mirror the template output ──────────────────────


class PostSchema(BaseModel):
    title: str | None = Field(default=None)


class PostRow(PostSchema):
    id: int = Field(default=...)

    author: AuthorRow | None = None

    @model_validator(mode="before")
    @classmethod
    def _extract_attrs(cls, obj: Any) -> dict[str, Any]:
        if isinstance(obj, dict):
            return obj
        data: dict[str, Any] = {}
        for name, _ in cls.model_fields.items():
            try:
                data[name] = getattr(obj, name)
            except MissingGreenlet:
                continue
            except Exception:
                continue
        return data

    @field_validator("author", mode="wrap")
    @classmethod
    def _drop_cyclic_author(
        cls, value: Any, handler: Callable[[Any], Any]
    ) -> Any | None:
        try:
            return handler(value)
        except ValidationError as exc:
            if not _is_recursion_validation_error(exc):
                raise
            return None

    model_config = ConfigDict(from_attributes=True)


class AuthorSchema(BaseModel):
    name: str | None = Field(default=None)


class AuthorRow(AuthorSchema):
    id: int = Field(default=...)

    posts: list[PostRow] = []

    @model_validator(mode="before")
    @classmethod
    def _extract_attrs(cls, obj: Any) -> dict[str, Any]:
        if isinstance(obj, dict):
            return obj
        data: dict[str, Any] = {}
        for name, _ in cls.model_fields.items():
            try:
                data[name] = getattr(obj, name)
            except MissingGreenlet:
                continue
            except Exception:
                continue
        return data

    @field_validator("posts", mode="wrap")
    @classmethod
    def _drop_cyclic_posts(
        cls, value: Any, handler: Callable[[Any], Any]
    ) -> Any | None:
        try:
            return handler(value)
        except ValidationError as exc:
            if not _is_recursion_validation_error(exc):
                raise
            pruned: list[Any] = []
            for item in value or []:
                try:
                    pruned.extend(handler([item]))
                except ValidationError:
                    continue
            return pruned

    model_config = ConfigDict(from_attributes=True)


# Rebuild forward refs now that both models are defined
PostRow.model_rebuild()
AuthorRow.model_rebuild()


# ── Helper: fake ORM-like object ────────────────────────────────────────


class FakeOrmObject:
    """Simulates a SQLAlchemy model instance."""

    def __init__(self, **kwargs: Any):
        for k, v in kwargs.items():
            setattr(self, k, v)


class FakeOrmWithLazyRel:
    """Simulates a SQLAlchemy model whose relationship raises MissingGreenlet."""

    def __init__(self, **kwargs: Any):
        self._loaded = kwargs

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        if name in self._loaded:
            return self._loaded[name]
        raise MissingGreenlet(
            "greenlet_spawn has not been called; can't call await_only()"
        )


# ── Tests: _extract_attrs ───────────────────────────────────────────────


class TestExtractAttrsDict:
    """When obj is already a dict, _extract_attrs should return it as-is."""

    def test_dict_passthrough(self):
        row = PostRow.model_validate({"id": 1, "title": "hello"})
        assert row.id == 1
        assert row.title == "hello"
        assert row.author is None

    def test_dict_with_nested_relationship(self):
        row = PostRow.model_validate(
            {"id": 1, "title": "hello", "author": {"id": 10, "name": "Alice"}}
        )
        assert row.author is not None
        assert row.author.id == 10
        assert row.author.name == "Alice"

    def test_dict_with_extra_keys_ignored(self):
        row = PostRow.model_validate({"id": 1, "title": "t", "unknown_field": 99})
        assert row.id == 1
        assert row.title == "t"


class TestExtractAttrsOrmObject:
    """When obj is an ORM-like object, _extract_attrs should use getattr."""

    def test_orm_object(self):
        obj = FakeOrmObject(id=1, title="from orm", author=None)
        row = PostRow.model_validate(obj)
        assert row.id == 1
        assert row.title == "from orm"
        assert row.author is None

    def test_orm_object_with_nested(self):
        author_obj = FakeOrmObject(id=10, name="Bob", posts=[])
        obj = FakeOrmObject(id=2, title="nested", author=author_obj)
        row = PostRow.model_validate(obj)
        assert row.id == 2
        assert row.author is not None
        assert row.author.name == "Bob"

    def test_missing_greenlet_skips_relationship(self):
        obj = FakeOrmWithLazyRel(id=3, title="lazy")
        row = PostRow.model_validate(obj)
        assert row.id == 3
        assert row.title == "lazy"
        # author was not loaded → falls back to default (None)
        assert row.author is None

    def test_missing_greenlet_on_uselist(self):
        obj = FakeOrmWithLazyRel(id=5, name="user")
        row = AuthorRow.model_validate(obj)
        assert row.id == 5
        assert row.name == "user"
        # posts was not loaded → falls back to default ([])
        assert row.posts == []


# ── Tests: cyclic reference handling ────────────────────────────────────


class TestCyclicReferences:
    def test_one_level_nesting_no_cycle(self):
        """A post with an author (no back-reference) should work fine."""
        row = PostRow.model_validate(
            {"id": 1, "title": "p", "author": {"id": 10, "name": "A"}}
        )
        assert row.author is not None
        assert row.author.posts == []

    def test_uselist_with_nested_items(self):
        """An author with posts should work when there's no cycle."""
        row = AuthorRow.model_validate(
            {
                "id": 1,
                "name": "Alice",
                "posts": [
                    {"id": 10, "title": "first"},
                    {"id": 11, "title": "second"},
                ],
            }
        )
        assert len(row.posts) == 2
        assert row.posts[0].title == "first"
        assert row.posts[1].title == "second"

    def test_mutual_cycle_is_pruned(self):
        """A↔B cycle: author→posts→author should be pruned gracefully."""
        row = AuthorRow.model_validate(
            {
                "id": 1,
                "name": "Alice",
                "posts": [
                    {
                        "id": 10,
                        "title": "p1",
                        "author": {
                            "id": 1,
                            "name": "Alice",
                            "posts": [
                                {
                                    "id": 10,
                                    "title": "p1",
                                    "author": {
                                        "id": 1,
                                        "name": "Alice",
                                        # keep nesting to trigger recursion
                                        "posts": [
                                            {
                                                "id": 10,
                                                "title": "p1",
                                                "author": {"id": 1, "name": "Alice"},
                                            }
                                        ],
                                    },
                                }
                            ],
                        },
                    }
                ],
            }
        )
        # The model should still load — cyclic parts get pruned
        assert row.id == 1
        assert len(row.posts) >= 1
        assert row.posts[0].title == "p1"
