import pytest
from sqlalchemy_pydantic_codegen.core.cleaner import clean_models
from pathlib import Path

def test_clean_models():
    raw_model_path = Path("tests/fixtures/sample_models.py")
    cleaned_model_path = Path("tests/fixtures/cleaned_models.py")
    
    # Run the cleaning function
    clean_models(raw_model_path, cleaned_model_path)
    
    # Check if the cleaned model file exists
    assert cleaned_model_path.exists()
    
    # Read the cleaned model content
    cleaned_content = cleaned_model_path.read_text()
    
    # Add assertions to verify the content of the cleaned model
    assert "Base" not in cleaned_content  # Ensure Base class is removed
    assert "created_at" not in cleaned_content  # Ensure timestamp fields are removed
    # Add more assertions as necessary to validate the cleaned content

    # Clean up the generated file after the test
    cleaned_model_path.unlink()  # Remove the cleaned model file after the test