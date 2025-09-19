# 🐍🔗 SQLAlchemy-Pydantic Codegen

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/sqlalchemy-pydantic-codegen)](https://pypi.org/project/sqlalchemy-pydantic-codegen/)
[![Python Unit Tests](https://github.com/dsanmart/sqlalchemy-pydantic-codegen/actions/workflows/ci.yml/badge.svg)](https://github.com/dsanmart/sqlalchemy-pydantic-codegen/actions/workflows/ci.yml)

A Python library for generating Pydantic models from SQLAlchemy models, providing a seamless integration between SQLAlchemy and Pydantic for data validation and serialization.

## ✨ Key Features

- **Automatic Pydantic model generation** from SQLAlchemy models.
- **Relationship support:** Nested models for SQLAlchemy relationships.
- **Custom JSON/JSONB field mapping** to your own Pydantic models.
- **Auto-generated `__init__.py`** for schema packages.

## 📦 Installation

```bash
uv add sqlalchemy-pydantic-codegen
```

## 🚀 Usage

> We recommend [sqlacodegen](https://github.com/agronholm/sqlacodegen) to generate your SQLAlchemy models automatically.

Once your SQLAlchemy models are ready, generate Pydantic models with:

```bash
sqlalchemy-pydantic-codegen --models-path my_app.db.models --output-dir src/schemas
```

- `--models-path`: Dotted path to your SQLAlchemy models (required)  
- `--output-dir`: Output directory for generated schemas (default: `src/schemas`)

### 🛠️ Custom Configuration
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

### 📤 Output
- One Pydantic schema file per SQLAlchemy model.
- __init__.py with all exports and forward references.
- Cleaned and ready-to-use Pydantic models.
