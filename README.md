# SQLAlchemy-Pydantic Codegen

A Python library for generating Pydantic models from SQLAlchemy models, providing a seamless integration between SQLAlchemy and Pydantic for data validation and serialization.

## Features

- **Automatic Pydantic model generation** from SQLAlchemy models.
- **Relationship support:** Nested models for SQLAlchemy relationships.
- **Enum reflection:** SQLAlchemy enums become Pydantic enums.
- **Field metadata:** Comments become descriptions, string lengths become `max_length`.
- **Jinja2 templating** for customizable output.
- **CLI** for easy usage, including output directory and config options.
- **Custom JSON/JSONB field mapping** to your own Pydantic models.
- **Post-generation cleaning** to remove or replace fields as needed.
- **Auto-generated `__init__.py`** for schema packages.
- **Ready for formatting tools** (e.g., Black, Ruff).

## Installation

```bash
uv add sqlalchemy-pydantic-codegen
```

or

```bash
pip install sqlalchemy-pydantic-codegen
```

## Preparing Your SQLAlchemy Models

Before using `sqlalchemy-pydantic-codegen`, you may want to generate your SQLAlchemy models from an existing database using [sqlacodegen](https://github.com/agronholm/sqlacodegen). This tool introspects your database and creates SQLAlchemy model classes automatically. To generate models, run:

```bash
sqlacodegen postgresql://user:password@localhost/dbname --outfile src/db/models.py
```

Once your models are generated, you can proceed to use `sqlalchemy-pydantic-codegen` as described below.

## Usage

After installation, use the CLI to generate Pydantic models from your SQLAlchemy models.

### Basic Usage

```bash
sqlalchemy-pydantic-codegen --models-path my_app.db.models --output-dir src/schemas
```
`--models-path`: Dotted path to your SQLAlchemy models module (required).
`--output-dir`: Directory for generated Pydantic schemas (default: src/schemas).

### Custom Configuration
To map JSON/JSONB fields to custom Pydantic models, use the --config option.

Create a config file (e.g., `codegen_config.py`):

```python
# codegen_config.py

# Maps table names to a dictionary of field names and the Pydantic model to use.
CUSTOM_JSONB_MODELS = {
    "my_table": {
        "my_jsonb_field": "MyCustomPydanticModelForJsonbField",
    },
}

# Maps the Pydantic model name to its full import statement.
CUSTOM_IMPORTS = {
    "MyCustomPydanticModelForJsonbField": "from my_app.schemas import MyCustomPydanticModelForJsonbField",
}
```

Then, run the command with the `--config` flag:

```bash
sqlalchemy-pydantic-codegen --models-path my_app.db.models --output-dir src/schemas --config codegen_config.py
```

### Output
- One Pydantic schema file per SQLAlchemy model.
- __init__.py with all exports and forward references.
- Cleaned and ready-to-use Pydantic models.


### Advanced
- Supports nested relationships and cyclic reference handling.
- Enum columns become Pydantic enums.
- Field comments and constraints are preserved as Pydantic metadata.
- Easily extend templates for your own conventions.