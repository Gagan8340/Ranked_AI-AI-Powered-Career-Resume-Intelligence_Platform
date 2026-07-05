import logging
import json
from utils.telemetry import increment_metric

import time

def safe_gemini_call(func, *args, **kwargs):
    """
    Executes a Gemini API call with retry logic and securely catches any 429/503 errors.
    Returns a deterministic fallback JSON flag on failure.
    Retries:
      Attempt 1 -> wait 2 seconds
      Attempt 2 -> wait 4 seconds
      Attempt 3 -> fail
    """
    max_attempts = 5
    for attempt in range(1, max_attempts + 1):
        try:
            res = func(*args, **kwargs)
            # If the result is a dict (json parsed), ensure fallback=False
            if isinstance(res, dict):
                res['fallback_mode'] = False
            increment_metric("gemini_success_count")
            return res
        except Exception as e:
            error_msg = str(e).upper()
            logging.error(f"Gemini API Failure (Attempt {attempt}): {str(e)}")
            
            if attempt < max_attempts:
                wait_time = 2 ** attempt
                time.sleep(wait_time)
                continue
            
            # Max attempts reached
            increment_metric("gemini_fallback_count")
            
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                return {
                    "status": "quota_limited",
                    "fallback_mode": True
                }
                
            if "503" in error_msg or "UNAVAILABLE" in error_msg:
                return {
                    "status": "service_unavailable",
                    "fallback_mode": True
                }
                
            return {
                "status": "failed",
                "fallback_mode": True,
                "message": str(e)
            }
