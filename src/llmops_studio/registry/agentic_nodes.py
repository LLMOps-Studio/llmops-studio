import os
import requests
from typing import Any, Dict
from llmops_studio.core.node import BaseNode

# FIX (Faz 8.1): these were hardcoded to http://localhost:8005 / :8006, which
# only works when studio-core runs natively on the host. Inside the Docker
# network, "localhost" resolves to the studio-core container itself, and the
# lab containers listen on their *internal* port 8000 (not the host-mapped
# 8005/8006 — see docker-compose.yml). Env vars let this work in both native
# and Docker setups: default to the Docker service DNS names, override via
# compose environment or a local .env for native runs.
REVIEW_LAB_URL = os.getenv("REVIEW_LAB_URL", "http://review-lab:8000")
MEMORY_LAB_URL = os.getenv("MEMORY_LAB_URL", "http://memory-lab:8000")


class CodeReviewNode(BaseNode):
    """
    Wraps the Review Lab capabilities into a DAG node for automated static analysis.
    Adheres to the Standard Output Contract for downstream evaluators.
    """
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # 1. Resolve dynamic input from upstream nodes or fallback to static config
        data_key = self.config.get("data_key")
        code_snippet = inputs.get(data_key, "") if data_key else self.config.get("code_snippet", "")
        
        if not code_snippet:
            return {"status": "skipped", "context": "", "response": "No code snippet provided."}

        try:
            # 2. Execute via the independent Review Lab microservice
            response = requests.post(
                f"{REVIEW_LAB_URL}/review",
                json={"code_snippet": code_snippet},
                timeout=120
            )
            response.raise_for_status()
            review_result = response.json()
            
            # 3. Return strictly formatted payload
            return {
                "status": "success",
                "context": code_snippet,
                "response": str(review_result)
            }
        except Exception as e:
            return {
                "status": "error",
                "context": code_snippet,
                "response": f"Review execution failed: {str(e)}"
            }


class ConversationalMemoryNode(BaseNode):
    """
    Wraps the Memory Lab capabilities to test agentic context retention within a pipeline.
    """
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        message = self.config.get("message", "")
        session_id = self.config.get("session_id", "dag_pipeline_session")
        
        # Optionally accept conversational history from upstream nodes
        history = inputs.get("history", [])

        try:
            response = requests.post(
                f"{MEMORY_LAB_URL}/chat",
                json={
                    "session_id": session_id,
                    "message": message,
                    "history": history
                },
                timeout=120
            )
            response.raise_for_status()
            chat_result = response.json().get("response", "")
            
            return {
                "status": "success",
                "context": message,
                "response": chat_result,
                "session_id": session_id
            }
        except Exception as e:
            return {
                "status": "error",
                "context": message,
                "response": f"Memory agent execution failed: {str(e)}"
            }