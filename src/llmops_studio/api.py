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

# 🟢 YENİ EKLENEN ENDPOINT: Ollama Model Keşfi
@router.get("/models", summary="List available Ollama models")
def get_models():
    """Fetches the list of locally available models directly from Ollama."""
    try:
        # Ollama varsayılan portu üzerinden /api/tags uç noktasına istek atıyoruz
        response = requests.get("http://localhost:11434/api/tags", timeout=3)
        response.raise_for_status()
        data = response.json()
        models = [model["name"] for model in data.get("models", [])]
        return {"models": models}
    except Exception as e:
        # Ollama kapalıysa UI'ın çökmesini engellemek için varsayılan fallback
        print(f"Warning: Could not connect to Ollama auto-discovery: {e}")
        return {"models": ["phi3:latest", "qwen2.5:3b", "llama3:8b"]}

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
    """Returns aggregated MLflow run data for the frontend dashboard."""
    try:
        client = mlflow.tracking.MlflowClient()
        # Explicitly define known experimental domains
        experiments = ["rag_benchmark", "promptops", "schema_lab"] 
        all_runs = []
        
        for exp_name in experiments:
            exp = client.get_experiment_by_name(exp_name)
            if exp:
                runs = client.search_runs(exp.experiment_id, max_results=50)
                all_runs.extend(runs)
        
        # Serialize run data for JSON response
        serialized_runs = [
            {
                "experiment_id": r.info.experiment_id,
                "run_id": r.info.run_id,
                "metrics": r.data.metrics,
                "params": r.data.params,
                "start_time": r.info.start_time
            }
            for r in all_runs
        ]
        
        return {"runs": serialized_runs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch MLflow data: {str(e)}")