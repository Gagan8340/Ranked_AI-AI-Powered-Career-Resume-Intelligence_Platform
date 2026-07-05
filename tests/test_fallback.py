import json
from utils.ai_fallback import safe_gemini_call

def test_mock_gemini(*args, **kwargs):
    raise Exception("429 RESOURCE_EXHAUSTED")

def test_mock_gemini_503(*args, **kwargs):
    raise Exception("503 UNAVAILABLE")

print("Testing 429 Fallback...")
res_429 = safe_gemini_call(test_mock_gemini, "resume", "jd")
print(json.dumps(res_429, indent=2))

print("\nTesting 503 Fallback...")
res_503 = safe_gemini_call(test_mock_gemini_503, "resume", "jd")
print(json.dumps(res_503, indent=2))
