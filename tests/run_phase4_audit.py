import json
import traceback
from utils.gemini_helper import generate_learning_roadmap
from utils.ats_engine import calculate_career_intelligence_score

def run_audit():
    results = {}
    
    # 1. Career Intelligence Score consistency
    print("Testing Career Intelligence Score bounds...")
    try:
        # Low everything
        s1 = calculate_career_intelligence_score("poor resume", "high requirements", 10)
        # High everything
        s2 = calculate_career_intelligence_score("python java docker kubernetes aws", "python java docker kubernetes aws", 95)
        # Mixed
        s3 = calculate_career_intelligence_score("python", "python java docker", 50)
        
        results['score_consistency'] = {
            "low_profile_score": s1,
            "high_profile_score": s2,
            "mixed_profile_score": s3,
            "status": "PASS" if s1 < 40 and s2 > 80 else "FAIL"
        }
    except Exception as e:
        results['score_consistency'] = {"status": "FAIL", "error": str(e)}

    # 2. Roadmap Quality Tests
    print("Testing Roadmap Quality...")
    try:
        r1 = generate_learning_roadmap(["Docker", "AWS", "Kubernetes", "CI/CD"])
        r2 = generate_learning_roadmap(["Python", "Pandas", "NumPy", "Scikit-learn"])
        r3 = generate_learning_roadmap(["React", "JavaScript", "TypeScript", "Tailwind"])
        
        # We just want to check if they are identical or vastly different
        if r1.get('week_1', {}).get('title') == r2.get('week_1', {}).get('title'):
            results['roadmap_quality'] = {"status": "FAIL", "reason": "Roadmaps are too generic/identical"}
        else:
            results['roadmap_quality'] = {"status": "PASS"}
            
    except Exception as e:
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            results['roadmap_quality'] = {"status": "WARNING", "reason": "429 Quota Exceeded. Could not verify."}
        else:
            results['roadmap_quality'] = {"status": "FAIL", "error": str(e)}

    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    run_audit()
