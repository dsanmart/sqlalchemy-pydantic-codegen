import pytest
from sqlalchemy_pydantic_codegen.core.generator import generate_model
from sqlalchemy_pydantic_codegen.utils.type_mapping import map_type

def test_generate_model():
    # Example input for the model generation
    input_model = {
        'name': 'User',
        'fields': {
            'id': 'Integer',
            'name': 'String',
            'email': 'String',
        }
    }
    
    expected_output = """class User(BaseModel):
    id: int
    name: str
    email: str
"""
    
    output = generate_model(input_model)
    assert output.strip() == expected_output.strip()

def test_map_type():
    assert map_type('Integer') == 'int'
    assert map_type('String') == 'str'
    assert map_type('Boolean') == 'bool'
    assert map_type('DateTime') == 'datetime.datetime'