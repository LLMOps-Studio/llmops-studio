import yaml
from pathlib import Path
from typing import Dict, Any

class ProjectRegistry:
    """
    Loads and manages different LLM projects (e.g., Finwise, Real Estate AI).
    Provides context to the DAGEngine so nodes know which datasets and models to use.
    """
    
    def __init__(self, config_path: str = "projects.yaml"):
        self.config_path = Path(config_path)
        self.projects = self._load_projects()

    def _load_projects(self) -> Dict[str, Dict[str, Any]]:
        if not self.config_path.exists():
            print(f"Warning: Project configuration not found at {self.config_path}")
            return {}
            
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                # Dictionary comprehension to map project 'name' to its config
                return {p["name"]: p for p in data.get("projects", [])}
        except Exception as e:
            raise RuntimeError(f"Failed to load projects from {self.config_path}: {e}")

    def get_project(self, name: str) -> Dict[str, Any]:
        """Returns the configuration for a specific project."""
        if name not in self.projects:
            raise ValueError(f"Project '{name}' is not registered in the platform.")
        return self.projects[name]
        
    def list_projects(self) -> list:
        """Returns a list of all registered project names."""
        return list(self.projects.keys())