from typing import Any

from jinja2 import Environment, FileSystemLoader


def load_templates(template_dir: str) -> dict[str, Any]:
    env = Environment(loader=FileSystemLoader(template_dir))
    templates = {
        "model": env.get_template("model.jinja2"),
        "schema": env.get_template("schema.jinja2"),
        "init": env.get_template("init.jinja2"),
    }
    return templates


def render_model(template_name: str, context: dict[str, Any]) -> str:
    templates = load_templates("src/sqlalchemy_pydantic_codegen/templates")
    return templates[template_name].render(context)


def render_schema(template_name: str, context: dict[str, Any]) -> str:
    templates = load_templates("src/sqlalchemy_pydantic_codegen/templates")
    return templates[template_name].render(context)
