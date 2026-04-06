import re
import time
import threading
from handle_keys import anthropic_client, openai_client
import os
from dotenv import load_dotenv
from google import genai
load_dotenv()
from tenacity import retry, stop_after_attempt, wait_exponential

LEARNING_APPROACHES = ["zero_shot", "zero_shot_self_refine", "few_shot"]

MODEL_SETS = {
    "claude-sonnet": {
        "model_string": "claude-sonnet-4-5-20250929",
        "delay": 0.1
    },
    "gemini-2.5-flash": {
        "model_string": "gemini-2.5-flash",
        "delay": 0.1
    },
    "gemini-2.5-pro": {
        "model_string": "gemini-2.5-pro",
        "delay": 1.0
    },
    "gpt-4.1": {
        "model_string": "gpt-4.1",
        "delay": 0.4
    },
    "gpt-4o": {
        "model_string": "gpt-4o",
        "delay": 0.4
    },
}

# Rate limiter
class RateLimiter:
    def __init__(self):
        self.locks = {m: threading.Lock() for m in MODEL_SETS}
        self.last_request = {m: 0 for m in MODEL_SETS}

    def wait(self, model):
        with self.locks[model]:
            delay = MODEL_SETS[model]["delay"]
            elapsed = time.time() - self.last_request[model]
            if elapsed < delay:
                time.sleep(delay - elapsed)
            self.last_request[model] = time.time()

rate_limiter = RateLimiter()

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def send_request(prompt, model):
    rate_limiter.wait(model)
    model_string = MODEL_SETS[model]["model_string"]

    if model.startswith("claude"):
        response = anthropic_client.messages.create(
            model=model_string,
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text

    elif model.startswith("gemini"):
        client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        
        response = client.models.generate_content(
            model=model_string,
            contents=prompt
        )
        return response.text
    
    elif model.startswith("gpt"):
        response = openai_client.chat.completions.create(
            model=model_string,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000
        )
        return response.choices[0].message.content

    else:
        raise ValueError(f"Unsupported model: {model}")
    
def extract_propositions(response):
    propositions = {}
    patterns = [
        r'(?:Response:|response:|Initial Answer:|Refined Answer:|Refined answer:|Atomic proposition:|Atomic propositions:)?\s*"(.+)":\s*(\w+)',
        r'"(.+)":\s*(\w+)'
    ]
    
    for line in response.split('\n'):
        line = line.strip()
        if line:
            for pattern in patterns:
                match = re.match(pattern, line)
                if match:
                    propositions[match.group(1).strip()] = match.group(2).strip()
                    break
    return propositions

def extract_wff_response(llm_output):
    # Remove leading/trailing whitespace and quotes
    cleaned_output = llm_output.strip().strip('"')
    
    # Search for a direct "Yes" or "No" at the beginning of the response
    match = re.match(r"^(Yes|No)\b", cleaned_output, re.IGNORECASE)
    
    if match:
        return match.group(0).capitalize()
    
    # Search for "Yes" or "No" within the detailed explanation
    yes_match = re.search(r"\bYes\b", cleaned_output, re.IGNORECASE)
    no_match = re.search(r"\bNo\b", cleaned_output, re.IGNORECASE)
    
    if yes_match:
        return "Yes"
    elif no_match:
        return "No"
    
    # Default to returning the cleaned output if no direct answer is found
    return cleaned_output.split('.')[0]




def extract_trace_response(llm_output):
    # Remove leading/trailing whitespace and quotes
    cleaned_output = llm_output.strip().strip('"')
    
    # Search for a direct "Yes" or "No" at the beginning of the response
    match = re.match(r"^(Positive|Negative)\b", cleaned_output, re.IGNORECASE)
    
    if match:
        return match.group(0).capitalize()
    
    # Search for "Yes" or "No" within the detailed explanation
    yes_match = re.search(r"\bPositive\b", cleaned_output, re.IGNORECASE)
    no_match = re.search(r"\bNegative\b", cleaned_output, re.IGNORECASE)
    
    if yes_match:
        return "Positive"
    elif no_match:
        return "Negative"
    # If no evaluation is found, return Unknown
    return 'Unknown'

def extract_ltl_formulas(text):
    # Regular expression to match LTL formulas
    ltl_pattern = r'(?:LTL Formula:|LTL formula:|The LTL formula|The corresponding LTL formula|Final LTL formula:|Final Refined LTL Formula:|final LTL statement)\s*(.*?(?:\(.*?\))*[^"\n]+)'
    
    # Find all matches
    matches = re.findall(ltl_pattern, text, re.DOTALL)
    
    # Clean up the extracted formulas
    formulas = [formula.strip() for formula in matches]
    
    # Remove any remaining quotes and newlines
    formulas = [re.sub(r'["\n]', '', formula) for formula in formulas]
    
    return formulas

def extract_ltl_formula(text):
    # Regular expression to match LTL formulas
    pattern = r'(?:G|F|X|U)\s*\((?:[^()]+|\([^()]*\))*\)|\w+\s*U\s*\w+|\([^()]+(?:->[^()]+)+\)'
    matches = re.findall(pattern, text)
    if matches:
        # Return the first match (assuming it's the most relevant)
        return re.sub(r'\\+', '', matches[0]).strip()
    return ""  # Return empty string if no formula is found

def extract_ltl_formulas_(text):
    # Regular expression pattern to match LTL formulas
    pattern = r"(\w+\s*(?:\&|\|\|\!|\->|U|G|F|X)\s*\w+)+|(\w+)"

    # Find all matches of the pattern in the text
    matches = re.findall(pattern, text)

    # Extract the LTL formulas from the matches
    ltl_formulas = [match[0] if match[0] else match[1] for match in matches]

    return ltl_formulas
def format_x_operators(formula):
    """
    Format LTL formula to ensure each X operator is followed by either a space or parenthesis.
    
    Args:
        formula (str): Input LTL formula
    Returns:
        str: Formatted formula with proper X operator spacing
    """
    result = []
    i = 0
    
    while i < len(formula):
        if formula[i] == 'X':
            # Add the X
            result.append('X')
            
            # Check next character if it exists
            if i + 1 < len(formula):
                next_char = formula[i + 1]
                # If next char isn't a space or paren, add a space
                if next_char != ' ' and next_char != '(':
                    result.append(' ')
        else:
            result.append(formula[i])
        i += 1
    
    return ''.join(result)
def extract_ltl_formula_llm(text):
    lines = text.split('\n')
    for line in lines:
        if ':' in line:
            _, formula = line.split(':', 1)
            return formula.strip()
        elif line.strip() and not line.lower().startswith(('initial', "Refined:", "Refined LTL Formula","Initial LTL formula", 'refined', 'final', 'generated response', 'ltl formula', "LTL Formula")):
            return line.strip()
    return None

def extract_positive_negative_trace(response):
    positive_trace = ''
    negative_trace = ''
    
    # Handle the case with "Initial Response:" and "Refined Response:"
    if "Refined Response:" in response:
        # Extract only the Refined Response part
        refined_part = re.search(r'Refined Response:(.*?)(?:$)', response, re.IGNORECASE | re.DOTALL)
        if refined_part:
            response = refined_part.group(1).strip()
    
    # Extract Positive trace with more flexible pattern matching
    positive_pattern = r'(?:[Pp]ositive\s*[Tt]race:[\s\*]*)(.*?)(?=\s*[Nn]egative\s*[Tt]race:|$)'
    positive_match = re.search(positive_pattern, response, re.IGNORECASE | re.DOTALL)
    
    if positive_match:
        positive_trace = positive_match.group(1).strip()
        # Remove unwanted characters and normalize whitespace
        positive_trace = re.sub(r'\*+', '', positive_trace)  # Remove '*'
        positive_trace = re.sub(r'\s+', ' ', positive_trace)  # Normalize whitespace
        positive_trace = positive_trace.strip()
    
    # Extract Negative trace with more flexible pattern matching
    negative_pattern = r'(?:[Nn]egative\s*[Tt]race:[\s\*]*)(.*?)(?=$)'
    negative_match = re.search(negative_pattern, response, re.IGNORECASE | re.DOTALL)
    
    if negative_match:
        negative_trace = negative_match.group(1).strip()
        # Remove unwanted characters and normalize whitespace
        negative_trace = re.sub(r'\*+', '', negative_trace)  # Remove '*'
        negative_trace = re.sub(r'\s+', ' ', negative_trace)  # Normalize whitespace
        negative_trace = negative_trace.strip()
    
    return positive_trace, negative_trace