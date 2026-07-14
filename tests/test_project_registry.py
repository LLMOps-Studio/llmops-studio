import pytest
import tempfile
import yaml
from pathlib import Path
from llmops_studio.core.project_registry import ProjectRegistry

@pytest.fixture
def temp_projects_yaml():
    """Creates a temporary projects.yaml file for testing."""
    test_data = {
        "projects": [
            {
                "name": "test-finwise",
                "base_model": "llama3",
                "dataset_source": "/fake/path/data.json"
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(test_data, f)
        temp_path = f.name
        
    yield temp_path
    
    # Cleanup
    Path(temp_path).unlink()

def test_project_registry_loads_correctly(temp_projects_yaml):
    # 1. Initialize registry with the fake yaml
    registry = ProjectRegistry(config_path=temp_projects_yaml)
    
    # 2. Verify project listing
    projects = registry.list_projects()
    assert "test-finwise" in projects
    
    # 3. Verify specific project details
    finwise_context = registry.get_project("test-finwise")
    assert finwise_context["base_model"] == "llama3"
    assert finwise_context["dataset_source"] == "/fake/path/data.json"