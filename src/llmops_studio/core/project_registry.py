import os
import yaml
from pathlib import Path
from typing import Dict, Any

class ProjectRegistry:
    """
    Loads and manages different LLM projects (e.g., Finwise, Real Estate AI).
    Provides context to the DAGEngine so nodes know which datasets and models to use.
    """

    def __init__(self, config_path: str = None):
        # PROJECTS_CONFIG_PATH lets the Docker image (or any deployment) point
        # this at wherever projects.yaml actually landed, instead of assuming
        # it's always sitting next to the current working directory.
        self.config_path = Path(
            config_path or os.getenv("PROJECTS_CONFIG_PATH", "projects.yaml")
        )
        self.projects = self._load_projects()

    def _load_projects(self) -> Dict[str, Dict[str, Any]]:
        if not self.config_path.exists():
            # This used to just warn-and-return-{} here, which is exactly why
            # the Project Context dropdown could go silently empty in Docker
            # (projects.yaml wasn't shipped into the image) with no visible
            # error anywhere -- raise instead so a misconfigured deployment
            # fails at startup, not as a mysteriously empty UI dropdown.
            raise RuntimeError(
                f"Project configuration not found at '{self.config_path.resolve()}'. "
                f"Set PROJECTS_CONFIG_PATH or ensure projects.yaml is present at that path."
            )

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