from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseNode(ABC):
    """
    Abstract base class for all nodes in the LLMOps Studio DAG.
    Every lab component (Evaluation, Agentic, Training) must implement this.
    """
    
    def __init__(self, node_id: str, config: Dict[str, Any]):
        self.node_id = node_id
        self.config = config

    @abstractmethod
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the core logic of the node.

        Args:
            inputs: Outputs from upstream dependency nodes or global DAG context.

        Returns:
            Dict containing the execution results.

        Output Contract:
            Any node whose result may be consumed by a downstream evaluator
            (e.g. FaithfulnessRelevanceScorerNode) MUST include two string
            fields in its returned dict:
              - "context":  the grounding material the node worked from
                            (retrieved chunks, reference doc, input code, ...)
              - "response": the generated/produced output to be scored
            Omitting these silently degrades downstream scoring to empty
            strings rather than raising an error -- this bit two nodes
            (RAGConfigBenchmarkNode, PromptComparisonNode) before the fields
            were added. New nodes should populate both even if only with a
            best-effort placeholder.
        """
        pass