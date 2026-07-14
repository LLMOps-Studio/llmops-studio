import graphlib
from typing import Dict, Any, Type
from llmops_studio.core.node import BaseNode

class DAGEngine:
    """
    Core Execution Engine that resolves node dependencies and 
    runs them in topological order.
    """
    
    def __init__(self):
        self.node_registry: Dict[str, Type[BaseNode]] = {}

    def register_node(self, node_type: str, node_class: Type[BaseNode]):
        """Registers a node implementation to the engine."""
        self.node_registry[node_type] = node_class

    def execute_dag(self, dag_definition: Dict[str, Any], initial_state: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Parses the DAG definition, sorts it topologically, and executes nodes.
        """
        nodes_info = {n["id"]: n for n in dag_definition.get("nodes", [])}
        edges = dag_definition.get("edges", [])

        # Build dependency graph for Topological Sorting
        graph = {node_id: set() for node_id in nodes_info}
        for edge in edges:
            graph[edge["target"]].add(edge["source"])

        # Topologically sort the graph (fails if there are circular dependencies)
        sorter = graphlib.TopologicalSorter(graph)
        execution_order = list(sorter.static_order())

        state = initial_state or {}
        
        for node_id in execution_order:
            node_data = nodes_info[node_id]
            node_type = node_data["type"]
            
            if node_type not in self.node_registry:
                raise ValueError(f"Node type '{node_type}' is not registered in the Engine.")
                
            node_class = self.node_registry[node_type]
            node_instance = node_class(node_id=node_id, config=node_data.get("config", {}))
            
            print(f"Executing Node: {node_id} [{node_type}]")
            output = node_instance.execute(inputs=state)
            
            state[node_id] = output
            
        return state