from llmops_studio.core.engine import DAGEngine
from llmops_studio.registry.evaluation_nodes import (
    PromptComparisonNode,
    RAGConfigBenchmarkNode,
    SchemaValidationNode,
    FaithfulnessRelevanceScorerNode
)
from llmops_studio.registry.agentic_nodes import CodeReviewNode, ConversationalMemoryNode

def populate_node_registry(engine: DAGEngine) -> DAGEngine:
    """Registers all standalone lab evaluation nodes into the central DAG Engine."""
    engine.register_node("prompt_comparison", PromptComparisonNode)
    engine.register_node("rag_benchmark", RAGConfigBenchmarkNode)
    engine.register_node("schema_validation", SchemaValidationNode)
    engine.register_node("llm_judge_scorer", FaithfulnessRelevanceScorerNode)
    engine.register_node("code_review", CodeReviewNode)
    engine.register_node("conversational_memory", ConversationalMemoryNode)
    return engine