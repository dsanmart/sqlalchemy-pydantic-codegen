import argparse
import importlib.util
import logging
from pathlib import Path

from dotenv import load_dotenv

from sqlalchemy_pydantic_codegen.core.cleaner import clean_models, clean_schemas
from sqlalchemy_pydantic_codegen.core.generator import ModelGenerator, load_models


def load_config_from_path(
    config_path_str: str,
) -> tuple[dict[str, object], dict[str, str]]:
    """Loads configuration variables from a Python file."""
    config_path = Path(config_path_str).resolve()
    if not config_path.is_file():
        logging.error(f"Config file not found: {config_path}")
        return {}, {}

    spec = importlib.util.spec_from_file_location("config", config_path)
    if not spec or not spec.loader:
        logging.error(f"Could not load spec for config file: {config_path}")
        return {}, {}

    config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_module)

    custom_jsonb_models = getattr(config_module, "CUSTOM_JSONB_MODELS", {})
    custom_imports = getattr(config_module, "CUSTOM_IMPORTS", {})

    return custom_jsonb_models, custom_imports


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="SQLAlchemy-Pydantic Codegen CLI")
    parser.add_argument(
        "--models-path",
        type=str,
        required=True,
        help="Dotted path to the module containing SQLAlchemy models (e.g., 'my_app.db.models').",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="src/schemas",
        help="Output directory for generated Pydantic schemas.",
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to a Python configuration file for custom model mappings.",
    )
    parser.add_argument(
        "--raw-models",
        type=str,
        help=(
            "Optional path to a raw sqlacodegen output file. When provided, "
            "the file is cleaned (Base/timestamp drops, NullType column "
            "rewrites) and written to the file backing --models-path before "
            "schema generation."
        ),
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if args.raw_models:
        spec = importlib.util.find_spec(args.models_path)
        if not spec or not spec.origin:
            raise RuntimeError(
                f"Cannot resolve a file path for module '{args.models_path}'; "
                "--raw-models requires --models-path to point at an importable "
                "module backed by a .py file."
            )
        target = Path(spec.origin)
        logging.info(f"Cleaning {args.raw_models} -> {target}...")
        clean_models(Path(args.raw_models), target)

    logging.info("Generating schemas...")

    # Assume templates are in a standard location within the package
    package_root = Path(__file__).parent.parent
    template_dir = package_root / "sqlalchemy_pydantic_codegen" / "templates"
    output_dir = Path(args.output_dir)

    mappers = load_models(args.models_path)
    generator = ModelGenerator(output_dir, template_dir)
    generator.generate_models(mappers)

    logging.info("Cleaning schemas...")
    if args.config:
        logging.info(f"Using custom configuration from: {args.config}")
        custom_jsonb_models, custom_imports = load_config_from_path(args.config)
        clean_schemas(output_dir, custom_jsonb_models, custom_imports)
    else:
        clean_schemas(output_dir)

    logging.info("Schema generation complete.")


if __name__ == "__main__":
    main()
