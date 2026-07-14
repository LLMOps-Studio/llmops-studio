from typing import Any, Dict
from pathlib import Path

from llmops_studio.core.node import BaseNode

# In-process imports from our decoupled laboratory libraries
from promptops_lab.evaluation.evaluator_pipeline import PromptEvaluatorPipeline
from rag_benchmark_lab.benchmark import RAGBenchmarkRunner
from schema_lab.extraction.agent import CVExtractionAgent
from llmops_common.eval.evaluator import LLMEvaluator
from llmops_common.client.factory import get_llm_client


class PromptComparisonNode(BaseNode):
    """
    Wraps the PromptOps Lab pipeline to execute prompt regression evaluation.
    Config expects: 
      - 'prompt_version': str (e.g., 'v1', 'v2')
    """
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        prompt_version = self.config.get("prompt_version", "v1")
        
        # Initialize the lab pipeline in-process
        pipeline = PromptEvaluatorPipeline()
        metrics = pipeline.evaluate_version(prompt_version=prompt_version)
        
        # Safely extract raw context and response if provided by the underlying pipeline[cite: 9]
        context = metrics.get("context", prompt_version) if isinstance(metrics, dict) else prompt_version
        response = metrics.get("response", "") if isinstance(metrics, dict) else ""
        
        return {
            "prompt_version": prompt_version,
            "metrics": metrics,
            "context": str(context),
            "response": str(response)
        }


class RAGConfigBenchmarkNode(BaseNode):
    """
    Wraps the RAG Benchmark Lab runner to evaluate grid configurations.
    Config expects:
      - 'experiment_name': str
      - 'params': dict (chunk_size, K, embedding_model, etc.)
    """
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        experiment_name = self.config.get("experiment_name", "rag_experiment")
        params = self.config.get("params", {})
        
        runner = RAGBenchmarkRunner(experiment_name=experiment_name)
        # Assuming run_grid_benchmark runs evaluation over the parameters
        results = runner.run_grid_benchmark(**params)
        
        # Safely extract context and response from the first/best run in the grid search[cite: 9]
        context = ""
        response = ""
        if results and isinstance(results, list) and len(results) > 0:
            first_run = results[0]
            if isinstance(first_run, dict):
                context = first_run.get("context", "")
                response = first_run.get("response", "")
        
        return {
            "experiment_name": experiment_name,
            "results": results,
            "context": str(context),
            "response": str(response)
        }


class SchemaValidationNode(BaseNode):
    """
    Wraps the Schema Lab extraction agent to validate structured data output compliance.
    Config expects:
      - 'data_key': str (pointer to find unstructured text inside inputs context)
    """
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        data_key = self.config.get("data_key")
        
        # Resolve dynamic input from upstream nodes if applicable
        raw_text = inputs.get(data_key, "") if data_key else self.config.get("raw_text", "")
        
        agent = CVExtractionAgent()
        
        try:
            # extract() returns a validated Pydantic model
            validation_result = agent.extract(text=raw_text)
            
            # Use model_dump() for Pydantic v2 or fallback to dict() for v1
            extracted = validation_result.model_dump() if hasattr(validation_result, "model_dump") else validation_result.dict()
            
            return {
                "valid": True,
                "extracted_data": extracted,
                "errors": []
            }
        except Exception as e:
            # Catch LLM schema drift or extraction failures
            return {
                "valid": False,
                "extracted_data": {},
                "errors": [str(e)]
            }


class FaithfulnessRelevanceScorerNode(BaseNode):
    """
    Wraps llmops-common LLMEvaluator to run direct LLM-as-a-Judge grading on upstream outputs.
    Config expects:
      - 'context_node_id': str (ID of the node that outputted the context)
      - 'response_node_id': str (ID of the node that outputted the final response)
      - 'query': str
    """
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        context_node_id = self.config.get("context_node_id")
        response_node_id = self.config.get("response_node_id")
        query = self.config.get("query", "")
        
        # Dynamically harvest upstream state
        context = inputs.get(context_node_id, {}).get("context", "")
        response = inputs.get(response_node_id, {}).get("response", "")
        
        llm_client = get_llm_client()
        evaluator = LLMEvaluator(client=llm_client)
        
        faithfulness_score = evaluator.evaluate_faithfulness(context=context, response=response)
        relevance_score = evaluator.evaluate_relevance(query=query, response=response)
        
        return {
            "faithfulness_score": faithfulness_score,
            "relevance_score": relevance_score
        }