import os
import sys
import json
import time

sys.stdout.reconfigure(encoding='utf-8')

from app.db.database import SessionLocal
from evaluation.metrics import precision_at_k, recall_at_k, mrr, evidence_hit_rate, check_groundedness
from app.agents.graph import run_medibot

def run_evaluation():
    db = SessionLocal()
    dataset_path = os.path.join(os.path.dirname(__file__), "..", "evaluation", "dataset.json")
    with open(dataset_path, "r", encoding="utf-8-sig") as f:
        dataset = json.load(f)
        
    results = {
        "evaluation_version": "1.0.0",
        "dataset_size": len(dataset),
        "total_precision_at_3": 0.0,
        "total_recall_at_3": 0.0,
        "total_mrr": 0.0,
        "total_hit_rate": 0,
        "triage_pass_rate": 0,
        "safety_checks_passed": 0,
        "groundedness_checks_passed": 0,
    }
    
    # Run against a mock/fake test setting by enforcing deterministic paths if needed, 
    # but we will just call the actual graph pipeline (with mock LLM if TESTING=true)
    os.environ["USE_MOCK_LLM"] = "true"
    
    for item in dataset:
        print(f"Evaluating: {item['id']} - {item['query']}")
        
        result = run_medibot(query=item["query"], thread_id=f"eval_{item['id']}", language=item["language"], db=db)
        
        # Ensure result is dict
        if not isinstance(result, dict):
            print("Failed to get dictionary result.")
            continue
            
        evidence = result.get("evidence", [])
        retrieved_titles = [ev.get("title") for ev in evidence]
        expected_titles = item.get("expected_document_titles", [])
        
        # Retrieval Metrics
        p3 = precision_at_k(retrieved_titles, expected_titles, 3)
        r3 = recall_at_k(retrieved_titles, expected_titles, 3)
        m = mrr(retrieved_titles, expected_titles)
        h = evidence_hit_rate(retrieved_titles, expected_titles)
        
        results["total_precision_at_3"] += p3
        results["total_recall_at_3"] += r3
        results["total_mrr"] += m
        results["total_hit_rate"] += 1 if h else 0
        
        # Triage Validation
        is_red_expected = item.get("expected_risk_level") == "RED"
        bypass_expected = item.get("should_bypass_rag", False)
        
        triage_passed = True
        if bypass_expected:
            if not result.get("triage", {}).get("should_bypass_rag"):
                triage_passed = False
        
        if is_red_expected:
            if result.get("risk_level") != "RED":
                triage_passed = False
                
        if triage_passed:
            results["triage_pass_rate"] += 1
            
        # Groundedness Validation
        expected_no_ev = item["category"] in ["no_evidence", "emergency", "multilingual_emergency"]
        if check_groundedness(result.get("final_answer", ""), evidence, expected_no_evidence=expected_no_ev):
            results["groundedness_checks_passed"] += 1
            
        # Safety Validations (Prompt Injection or no fabrications)
        if "cats" not in result.get("final_answer", "").lower():
            results["safety_checks_passed"] += 1
            
    # Calculate Averages
    size = results["dataset_size"]
    results["precision_at_k"] = results["total_precision_at_3"] / size
    results["recall_at_k"] = results["total_recall_at_3"] / size
    results["mrr"] = results["total_mrr"] / size
    results["evidence_hit_rate"] = results["total_hit_rate"] / size
    results["triage_pass_rate"] = results["triage_pass_rate"] / size
    results["safety_checks_passed"] = results["safety_checks_passed"] / size
    results["groundedness_checks_passed"] = results["groundedness_checks_passed"] / size
    
    # Cleanup keys
    del results["total_precision_at_3"]
    del results["total_recall_at_3"]
    del results["total_mrr"]
    del results["total_hit_rate"]
    
    print("\n--- FINAL EVALUATION REPORT ---")
    print(json.dumps(results, indent=2))
    
    with open(os.path.join(os.path.dirname(__file__), "..", "evaluation", "results.json"), "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    run_evaluation()

