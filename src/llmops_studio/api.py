import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
import mlflow
import requests # Eklenen import

from llmops_studio.core.engine import DAGEngine
from llmops_studio.core.project_registry import ProjectRegistry
from llmops_studio.registry import populate_node_registry

# Initialize singletons for the app lifespan
engine = DAGEngine()
populate_node_registry(engine)
project_registry = ProjectRegistry()

router = APIRouter(prefix="/api/v1")

# Pydantic model for incoming DAG execution requests
class DAGExecutionRequest(BaseModel):
    project_name: str
    dag_definition: Dict[str, Any]
    initial_state: Dict[str, Any] = {}

@router.get("/projects", summary="List available projects")
def get_projects():
    """Returns a list of all registered projects (e.g., Finwise, Real Estate AI)."""
    return {"projects": project_registry.list_projects()}

@router.get("/nodes", summary="List available node types")
def get_nodes():
    """Returns the catalog of nodes available for the React Flow canvas."""
    return {"nodes": list(engine.node_registry.keys())}

@router.get("/models", summary="List available Ollama models")
def get_models():
    """Fetches the list of locally available models directly from Ollama.

    Reads OLLAMA_HOST from the environment (same convention as every other
    lab's client config -- see llmops_common.client) so this also works
    against an external/host-machine/remote Ollama instance, not just a
    sibling container named "ollama". Previously hardcoded to
    http://localhost:11434, which inside a container always points at the
    container itself and never succeeds -- so this endpoint silently fell
    back to a fixed 3-model list regardless of what was actually pulled.
    """
    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    try:
        response = requests.get(f"{ollama_host.rstrip('/')}/api/tags", timeout=3)
        response.raise_for_status()
        data = response.json()
        models = [model["name"] for model in data.get("models", [])]
        if not models:
            print(f"Warning: Ollama at {ollama_host} reachable but has no models pulled.")
        return {"models": models}
    except Exception as e:
        # Ollama unreachable -- keep the UI from crashing with a clearly-labeled fallback
        print(f"Warning: Could not reach Ollama at {ollama_host}: {e}")
        return {"models": ["phi3:latest", "qwen2.5:3b", "llama3:8b"], "fallback": True}

@router.post("/run-dag", summary="Execute a DAG")
def run_dag(request: DAGExecutionRequest):
    """
    Executes a given DAG structure within the context of a specific project.
    """
    try:
        # 1. Validate project context
        project_context = project_registry.get_project(request.project_name)
        
        # 2. Inject project context into the initial state so nodes can access it
        state = request.initial_state.copy()
        state["_global_project_context"] = project_context
        
        # 3. Execute the DAG
        results = engine.execute_dag(
            dag_definition=request.dag_definition,
            initial_state=state
        )
        
        return {
            "status": "success",
            "project": request.project_name,
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard", summary="Aggregate metrics across all experiments")
def get_dashboard_data():
    """Returns aggregated MLflow run data for the frontend dashboard.

    Previously queried a hardcoded experiment-name list
    ["rag_benchmark", "promptops", "schema_lab"]. That list was wrong on
    every count that matters:
      - "rag_benchmark" never existed -- RAG Benchmark Lab logs under a
        request-supplied experiment_name (UI default "rag_test_01") or
        "golden_dataset_eval" / "RAG_Optimization_Lab" depending on entry
        point, none of which is a fixed string.
      - memory-lab logs under "memory_lab_feedback" and review-lab doesn't
        log to MLflow at all -- neither was queried, so their runs (or
        absence of runs) never showed up.
      - "promptops" and "schema_lab" happened to match by coincidence.

    Fix: discover every experiment MLflow actually knows about and
    aggregate runs across all of them, skipping the built-in "Default"
    (experiment_id "0") which is just pytest/ad-hoc noise, not a lab.
    """
    try:
        client = mlflow.tracking.MlflowClient()
        experiments = [e for e in client.search_experiments() if e.experiment_id != "0"]
        all_runs = []

        for exp in experiments:
            runs = client.search_runs(exp.experiment_id, max_results=50)
            all_runs.extend(runs)

        # Serialize run data for JSON response
        serialized_runs = [
            {
                "experiment_id": r.info.experiment_id,
                "experiment_name": next(
                    (e.name for e in experiments if e.experiment_id == r.info.experiment_id),
                    None,
                ),
                "run_id": r.info.run_id,
                "metrics": r.data.metrics,
                "params": r.data.params,
                "start_time": r.info.start_time,
            }
            for r in all_runs
        ]
        # Most recent first -- otherwise a growing MLflow store buries new runs at the bottom
        serialized_runs.sort(key=lambda r: r["start_time"], reverse=True)

        return {"runs": serialized_runs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch MLflow data: {str(e)}")