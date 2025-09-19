import logging
import re
import subprocess
from importlib import import_module
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import ColumnProperty, Mapper

from ..utils.type_mapping import (
    get_default_value,
    is_nullable,
    map_sqlalchemy_type_to_pydantic,
)


def to_snake(name: str) -> str:
    """Converts CamelCase to snake_case."""
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


class ModelGenerator:
    def __init__(self, output_dir: Path, template_dir: Path):
        self.output_dir = output_dir
        self.template_dir = template_dir
        self.env = Environment(
            loader=FileSystemLoader(template_dir), trim_blocks=True, lstrip_blocks=True
        )

    def format_file(self, file_path: Path):
        """Formats a file using ruff."""
        try:
            subprocess.run(
                ["ruff", "format", str(file_path)],
                check=True,
                capture_output=True,
                text=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            error_message = (
                e.stderr if isinstance(e, subprocess.CalledProcessError) else str(e)
            )
            logging.warning(
                f"Could not format {file_path}. Is 'ruff' installed and in your PATH?\n{error_message}"
            )

    def generate_models(self, mappers: list[Mapper[Any]]):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        schema_names: list[dict[str, str]] = []

        for mapper in mappers:
            schema_name = self.render_model(mapper)
            schema_names.append(
                {
                    "name": schema_name,
                    "snake": to_snake(schema_name.replace("Schema", "")),
                }
            )

        self.render_init_file(schema_names)

    def render_model(self, mapper: Mapper[Any]) -> str:
        cls = mapper.class_
        schema_name = f"{cls.__name__}Schema"
        base_fields, id_type = self.get_fields(mapper)
        rels, imports = self.get_relationships(mapper)

        all_type_hints = [f["type_hint"] for f in base_fields] + [
            r["classname"] for r in rels
        ]
        needs_datetime = any("datetime" in hint for hint in all_type_hints)
        needs_uuid = any("UUID" in hint for hint in all_type_hints)
        needs_any = any("Any" in hint for hint in all_type_hints) or rels

        template = self.env.get_template("model.jinja2")
        context = {
            "schema_name": schema_name,
            "base_fields": base_fields,
            "id_type": id_type,
            "rels": rels,
            "imports": imports,
            "needs_datetime": needs_datetime,
            "needs_uuid": needs_uuid,
            "needs_any": needs_any,
        }
        content = template.render(context)

        output_file = self.output_dir / f"{to_snake(cls.__name__)}.py"
        output_file.write_text(content, encoding="utf-8")
        self.format_file(output_file)
        logging.info(f"Generated model: {output_file}")
        return schema_name

    def get_fields(self, mapper: Mapper[Any]) -> tuple[list[dict[str, Any]], str]:
        fields: list[dict[str, Any]] = []
        id_type = "int"  # Default ID type

        for prop in mapper.iterate_properties:
            if isinstance(prop, ColumnProperty) and prop.columns:
                col = prop.columns[0]
                py_type, field_args_dict = map_sqlalchemy_type_to_pydantic(col.type)
                nullable = is_nullable(col)
                default = get_default_value(col)

                type_hint = py_type if not nullable else f"{py_type} | None"
                default_value = "..." if not nullable and not default else "None"

                if prop.key == "id":
                    id_type = py_type
                    fields.append(
                        {
                            "name": "id",
                            "type_hint": f"{py_type} | None",
                            "default": "None",
                            "field_args": "",
                        }
                    )
                    continue

                nullable = is_nullable(col)
                default = get_default_value(col)

                type_hint = py_type if not nullable else f"{py_type} | None"
                default_value = "..." if not nullable and not default else "None"

                field_args = [
                    f"{k}={v!r}" for k, v in field_args_dict.items() if v is not None
                ]
                if col.comment:
                    field_args.append(f'description="{col.comment}"')

                fields.append(
                    {
                        "name": prop.key,
                        "type_hint": type_hint,
                        "default": default_value,
                        "field_args": ", ".join(field_args),
                    }
                )
        return fields, id_type

    def get_relationships(
        self, mapper: Mapper[Any]
    ) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
        rels: list[dict[str, Any]] = []
        imports: list[dict[str, str]] = []
        for rel in mapper.relationships:
            related_class = rel.mapper.class_
            classname = f"{related_class.__name__}Row"
            rels.append(
                {"name": rel.key, "classname": classname, "uselist": rel.uselist}
            )
            imp = {
                "module": to_snake(related_class.__name__),
                "classname": classname,
            }
            if imp not in imports:
                imports.append(imp)
        return rels, imports

    def render_init_file(self, items: list[dict[str, str]]):
        sorted_items = sorted(items, key=lambda x: x["name"])
        template = self.env.get_template("init.jinja2")
        content = template.render(items=sorted_items)
        output_file = self.output_dir / "__init__.py"
        output_file.write_text(content, encoding="utf-8")
        self.format_file(output_file)
        logging.info(f"Generated __init__.py in {self.output_dir}")


def load_models(module_path: str) -> list[Mapper[Any]]:
    module = import_module(module_path)
    return list(module.Base.registry.mappers)
