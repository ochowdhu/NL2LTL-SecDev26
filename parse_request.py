import re
from handle_keys import anthropic_client, openai_client
import time
from concurrent.futures import ThreadPoolExecutor
import threading
from tenacity import retry, stop_after_attempt, wait_exponential

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    print("WARNING: google-genai package not installed. Install with: pip install google-genai")
    GENAI_AVAILABLE = False

MODELS = {
    # Claude models
    "claude-3.5-sonnet": {
        "model_string": "claude-3-5-sonnet-20241022",
        "context_window": 200_000,
        "rpm": 1000,
        "delay": 0.06
    },

    "claude-sonnet-4": {
        "model_string": "claude-sonnet-4-20250514",
        "context_window": 200_000,
        "rpm": 1000,
        "delay": 0.06
    },
    
    # Gemini models - FIXED with correct v1beta model strings
    "gemini-1.5-pro": {
        "model_string": "gemini-1.5-pro-002",  # FIXED: specific version
        "context_window": 2_000_000,
        "rpm": 60,
        "delay": 1.0
    },
    
    "gemini-1.5-flash": {
        "model_string": "gemini-1.5-flash-002",  # FIXED: specific version
        "context_window": 1_000_000,
        "rpm": 1000,
        "delay": 0.06
    },
    
    "gemini-2.0-flash": {
        "model_string": "gemini-2.0-flash-exp",
        "context_window": 1_000_000,
        "rpm": 1500,
        "delay": 0.04
    },
    
    # OpenAI models
    "gpt-4o": {
        "model_string": "gpt-4o",
        "context_window": 128_000,
        "rpm": 500,
        "delay": 0.12
    },
    
    "gpt-4o-mini": {
        "model_string": "gpt-4o-mini",
        "context_window": 128_000,
        "rpm": 500,
        "delay": 0.12
    }
}

class OptimalRateLimiter:
    def __init__(self):
        self.model_locks = {}
        self.last_request_time = {}
        
        for model in MODELS:
            self.model_locks[model] = threading.Lock()
            self.last_request_time[model] = 0
    
    def wait_for_rate_limit(self, model):
        """Optimized rate limiting"""
        with self.model_locks[model]:
            now = time.time()
            delay = MODELS[model]["delay"]
            
            time_since_last = now - self.last_request_time.get(model, 0)
            if time_since_last < delay:
                sleep_time = delay - time_since_last
                time.sleep(sleep_time)
            
            self.last_request_time[model] = time.time()

rate_limiter = OptimalRateLimiter()

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8))
def send_request(prompt, model):
    """
    Optimized send_request with NEW Gemini API
    """
    
    try:
        if model.startswith("claude"):
            rate_limiter.wait_for_rate_limit(model)
            response = anthropic_client.messages.create(
                model=MODELS[model]["model_string"],
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
            
        elif model.startswith("gemini"):
            if not GENAI_AVAILABLE:
                raise RuntimeError("google-genai package not installed")
            
            rate_limiter.wait_for_rate_limit(model)
            
            # Use NEW Google GenAI SDK
            client = genai.Client()
            response = client.models.generate_content(
                model=MODELS[model]["model_string"],
                contents=prompt
            )
            return response.text
        
        elif model.startswith("gpt"):
            rate_limiter.wait_for_rate_limit(model)
            response = openai_client.chat.completions.create(
                model=MODELS[model]["model_string"],
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4000
            )
            return response.choices[0].message.content
            
        else:
            raise ValueError(f"Unsupported model: {model}")
            
    except Exception as e:
        print(f"Error with {model}: {e}")
        raise


def send_requests_parallel(prompt, models_to_use):
    """
    Send requests to multiple models in parallel - MUCH FASTER
    
    Args:
        prompt: The prompt to send
        models_to_use: List of model keys from MODELS dict
        
    Returns:
        Dict mapping model name to response
    """
    results = {}
    
    def process_model(model):
        try:
            return model, send_request(prompt, model)
        except Exception as e:
            print(f"Failed on {model}: {e}")
            return model, None
    
    with ThreadPoolExecutor(max_workers=len(models_to_use)) as executor:
        futures = [executor.submit(process_model, model) for model in models_to_use]
        for future in futures:
            model, response = future.result()
            results[model] = response
    
    return results


# USAGE EXAMPLES
if __name__ == "__main__":
    test_prompt = "What is 2+2?"
    
    # Test with Claude first (most reliable)
    print("Testing Claude...")
    try:
        response = send_request(test_prompt, "claude-sonnet-4")
        print(f"Claude Response: {response}\n")
    except Exception as e:
        print(f"Claude failed: {e}\n")
    
    # Test Gemini with new API
    print("Testing Gemini (new API)...")
    try:
        response = send_request(test_prompt, "gemini-1.5-flash")
        print(f"Gemini Response: {response}\n")
    except Exception as e:
        print(f"Gemini failed: {e}\n")
    
    # Test OpenAI
    print("Testing OpenAI...")
    try:
        response = send_request(test_prompt, "gpt-4o-mini")
        print(f"OpenAI Response: {response}\n")
    except Exception as e:
        print(f"OpenAI failed: {e}\n")
    
    # Parallel test
    print("Testing parallel requests...")
    start = time.time()
    results = send_requests_parallel(
        test_prompt, 
        ["claude-sonnet-4", "gpt-4o-mini"]  # Start with reliable models
    )
    elapsed = time.time() - start
    
    print(f"\nCompleted in {elapsed:.2f}s")
    for model, response in results.items():
        if response:
            print(f"\n{model}: {response[:100]}...")
        else:
            print(f"\n{model}: FAILED")