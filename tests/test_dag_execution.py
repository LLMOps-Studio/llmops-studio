import pytest
from unittest.mock import patch, MagicMock

from llmops_studio.core.engine import DAGEngine
from llmops_studio.registry import populate_node_registry

# Düğümlerin (Node) içindeki gerçek LLM ve Veriseti süreçlerini engelliyoruz
@patch("llmops_studio.registry.evaluation_nodes.PromptEvaluatorPipeline")
@patch("llmops_studio.registry.evaluation_nodes.CVExtractionAgent")
def test_evaluation_dag_flow(mock_cv_agent_class, mock_pipeline_class):
    
    # 1. Mock Ayarları: LLM'in döneceği sahte ama başarılı yanıtları tanımlıyoruz
    mock_pipeline_instance = MagicMock()
    mock_pipeline_instance.evaluate_version.return_value = {
        "avg_faithfulness": 0.95, 
        "avg_relevance": 0.92
    }
    mock_pipeline_class.return_value = mock_pipeline_instance
    
    mock_cv_agent_instance = MagicMock()
    mock_cv_result = MagicMock()
    mock_cv_result.model_dump.return_value = {"name": "Muhammet Ali Varlik", "skills": ["Python"]}
    # dict() fallback'i için
    mock_cv_result.dict.return_value = {"name": "Muhammet Ali Varlik", "skills": ["Python"]}
    mock_cv_agent_instance.extract.return_value = mock_cv_result
    mock_cv_agent_class.return_value = mock_cv_agent_instance

    # 2. Motoru ve Registry'i Başlat
    engine = DAGEngine()
    populate_node_registry(engine)
    
    # 3. Test DAG Yapısı (React Flow'dan gelecek JSON'ın simülasyonu)
    mock_dag = {
        "nodes": [
            {
                "id": "node_prompt_v2",
                "type": "prompt_comparison",
                "config": {"prompt_version": "v2"}
            },
            {
                "id": "node_schema_check",
                "type": "schema_validation",
                "config": {"raw_text": "Sample text for validation structure"}
            }
        ],
        "edges": []
    }
    
    # 4. Çalıştır
    final_state = engine.execute_dag(mock_dag)
    
    # 5. Doğrulamalar (Assertions)
    assert "node_prompt_v2" in final_state
    assert final_state["node_prompt_v2"]["metrics"]["avg_faithfulness"] == 0.95
    
    assert "node_schema_check" in final_state
    assert final_state["node_schema_check"]["extracted_data"]["name"] == "Muhammet Ali Varlik"
    
    print("\nDAG Execution Verification Passed Successfully!")