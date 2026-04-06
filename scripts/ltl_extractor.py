import re

def extract_ltl_formula(response_text):
    """
    Extract LTL formula from model response for standard (non-AST) experiments.
    """
    if not response_text or response_text.strip() == "Error":
        return "No LTL formula extracted"
    
    response = response_text.strip()
    
    # Split response into lines and look for LTL formulas
    lines = response.split('\n')
    
    # Look for the final/refined formula (usually appears last)
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
            
        # Skip common non-formula lines
        if any(skip_phrase in line.lower() for skip_phrase in [
            'this refined formula', 'better captures', 'requirements:',
            'if client', 'then client', 'if anyone', 'then no one'
        ]):
            continue
            
        # Check if line contains LTL operators and looks like a formula
        if is_valid_ltl_formula(line):
            return clean_ltl_formula(line)
    
    # If no good formula found in reverse, try forward pass with patterns
    patterns = [
        r'LTL Formula:\s*(.+?)(?:\n|$)',
        r'Formula:\s*(.+?)(?:\n|$)',
        r'Answer:\s*(.+?)(?:\n|$)',
        r'Result:\s*(.+?)(?:\n|$)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, response, re.IGNORECASE | re.MULTILINE)
        if match:
            formula = match.group(1).strip()
            formula = clean_ltl_formula(formula)
            if is_valid_ltl_formula(formula):
                return formula
    
    # Last resort: look for any line that looks like an LTL formula
    for line in lines:
        line = line.strip()
        if is_valid_ltl_formula(line):
            return clean_ltl_formula(line)
    
    return "No LTL formula extracted"

def clean_ltl_formula(formula):
    """
    Clean and normalize LTL formula.
    """
    if not formula:
        return ""
    
    # Remove common prefixes
    prefixes_to_remove = [
        "LTL Formula:", "Formula:", "Answer:", "Result:", "The LTL formula is:",
        "LTL:", "Output:", "Solution:", "The formula is:"
    ]
    
    for prefix in prefixes_to_remove:
        if formula.upper().startswith(prefix.upper()):
            formula = formula[len(prefix):].strip()
    
    # Remove trailing punctuation and explanatory text
    formula = formula.rstrip('.!?')
    
    # Replace common Unicode symbols with ASCII equivalents
    replacements = {
        '→': '->',
        '∧': '&',
        '∨': '|',
        '¬': '!',
        '◇': 'F',  # Eventually (future)
        '□': 'G',  # Always (future)
        '○': 'X',  # Next (future)
        '◆': 'O',  # Once (past)
        '■': 'H',  # Historically (past)
        '●': 'Y',  # Yesterday (past)
    }
    
    for unicode_char, ascii_char in replacements.items():
        formula = formula.replace(unicode_char, ascii_char)
    
    return formula.strip()

def is_valid_ltl_formula(formula):
    """
    Check if the formula looks like a valid LTL formula.
    """
    if not formula or len(formula.strip()) < 2:
        return False
    
    formula = formula.strip()
    
    # Must contain LTL operators (including past-time operators)
    ltl_operators = ['G(', 'F(', 'X(', 'U', 'S', 'Y(', 'H(', 'O(', '->', '&', '|', '!']
    has_operator = any(op in formula for op in ltl_operators)
    
    if not has_operator:
        return False
    
    # Should contain atomic propositions (x1, x2, etc.)
    has_atomic = bool(re.search(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', formula))
    if not has_atomic:
        return False
    
    # Check for balanced parentheses
    try:
        paren_count = 0
        for char in formula:
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
                if paren_count < 0:
                    return False
        balanced_parens = paren_count == 0
    except:
        balanced_parens = False
    
    # Should not contain explanatory text
    explanatory_phrases = [
        'if client', 'then client', 'captures', 'requirements',
        'better', 'this formula', 'anyone is reading'
    ]
    
    has_explanation = any(phrase in formula.lower() for phrase in explanatory_phrases)
    
    return balanced_parens and not has_explanation

# Keep the AST-specific functions for python experiments
def extract_python_ast(response_text):
    """
    Extract Python AST formula from model response.
    """
    response = response_text.strip()
    
    # Look for Python code blocks
    patterns = [
        r'```python\s*\n(.*?)\n```',
        r'```\s*\n(.*?)\n```',
        r'formulaToFind\s*=\s*(.+?)(?:\n|$)',
        r'Formula:\s*(.+?)(?:\n|$)',
        r'Result:\s*(.+?)(?:\n|$)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)
        for match in matches:
            match = match.strip()
            if is_valid_python_ast_pattern(match):
                return clean_python_ast(match)
    
    # Try to find AST pattern in the entire response
    ast_pattern = r'(Eventually|Always|Next|AtomicProposition|LImplies|LAnd|LOr|LNot)\s*\('
    if re.search(ast_pattern, response):
        cleaned_response = clean_python_ast(response)
        if is_valid_python_ast_pattern(cleaned_response):
            return cleaned_response
    
    return "No Python AST extracted"

def clean_python_ast(ast_string):
    """
    Clean and normalize Python AST string.
    """
    if not ast_string:
        return ""
    
    # Remove formulaToFind = if present
    if 'formulaToFind' in ast_string:
        ast_string = re.sub(r'formulaToFind\s*=\s*', '', ast_string)
    
    # Remove extra whitespace and newlines
    ast_string = ' '.join(ast_string.split())
    
    return ast_string.strip()

def is_valid_python_ast_pattern(ast_string):
    """
    Check if the string looks like a valid Python AST.
    """
    if not ast_string:
        return False
    
    # Check for AST function names (including past-time operators)
    ast_functions = ['Eventually', 'Always', 'Next', 'AtomicProposition', 
                    'LImplies', 'LAnd', 'LOr', 'LNot', 'Until', 'LEquiv',
                    'Since', 'Once', 'Historically', 'Yesterday']
    
    has_ast_function = any(func in ast_string for func in ast_functions)
    
    # Check for balanced parentheses
    try:
        paren_count = 0
        for char in ast_string:
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
                if paren_count < 0:
                    return False
        balanced_parens = paren_count == 0
    except:
        balanced_parens = False
    
    return has_ast_function and balanced_parens
def convert_python_ast_to_ltl(python_ast):
    if not python_ast or python_ast == "No Python AST extracted":
        return "Error in AST conversion"
    try:
        ltl = python_ast
        # Strip formulaToFind =
        ltl = re.sub(r'formulaToFind\s*=\s*', '', ltl)
        # Atomic propositions first
        ltl = re.sub(r'AtomicProposition\s*\(\s*["\']([^"\']+)["\']\s*\)', r'\1', ltl)
        # Unary temporal
        ltl = re.sub(r'Eventually\s*\(', 'F(', ltl)
        ltl = re.sub(r'Always\s*\(', 'G(', ltl)
        ltl = re.sub(r'Next\s*\(', 'X(', ltl)
        ltl = re.sub(r'LNot\s*\(', '!(', ltl)
        ltl = re.sub(r'Once\s*\(', 'O(', ltl)
        ltl = re.sub(r'Historically\s*\(', 'H(', ltl)
        ltl = re.sub(r'Yesterday\s*\(', 'Y(', ltl)
        # Binary operators - replace function name+open paren, add infix op before closing
        # Use a helper to find matching paren pairs
        ltl = _replace_binary_op(ltl, 'LImplies', '->')
        ltl = _replace_binary_op(ltl, 'LAnd', '&')
        ltl = _replace_binary_op(ltl, 'LOr', '|')
        ltl = _replace_binary_op(ltl, 'LEquiv', '<->')
        ltl = _replace_binary_op(ltl, 'Until', 'U')
        ltl = _replace_binary_op(ltl, 'Since', 'S')
        ltl = re.sub(r'\s+', ' ', ltl).strip()
        return ltl
    except Exception as e:
        return f"Error in AST conversion: {str(e)}"

def _replace_binary_op(formula, func_name, op_symbol):
    """Replace FuncName(a, b) with (a OP b), handling nesting correctly."""
    result = formula
    while func_name + '(' in result:
        idx = result.find(func_name + '(')
        start = idx + len(func_name) + 1  # position after '('
        # Find the matching closing paren
        depth = 1
        i = start
        while i < len(result) and depth > 0:
            if result[i] == '(':
                depth += 1
            elif result[i] == ')':
                depth -= 1
            i += 1
        inner = result[start:i-1]  # content between outer parens
        # Split on the first top-level comma
        split_idx = _find_top_level_comma(inner)
        if split_idx == -1:
            break  # malformed, skip
        arg1 = inner[:split_idx].strip()
        arg2 = inner[split_idx+1:].strip()
        replacement = f'({arg1} {op_symbol} {arg2})'
        result = result[:idx] + replacement + result[i:]
    return result

def _find_top_level_comma(s):
    """Find index of first comma not inside parentheses."""
    depth = 0
    for i, c in enumerate(s):
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
        elif c == ',' and depth == 0:
            return i
    return -1

def convert_ast_ground_truth_to_ltl(ast_ground_truth):
    """
    Convert AST ground truth from CSV to standard LTL for comparison.
    This is used to convert the AST column to standard LTL format.
    """
    return convert_python_ast_to_ltl(ast_ground_truth)

# Factory function to choose the right extraction method
def extract_ltl_formula_by_type(response_text, experiment_type="standard"):
    """
    Choose the appropriate extraction method based on experiment type.
    """
    if experiment_type == "python":
        # For python experiments, extract AST and convert to LTL
        python_ast = extract_python_ast(response_text)
        if python_ast == "No Python AST extracted":
            return python_ast
        return convert_python_ast_to_ltl(python_ast)
    else:
        # For standard experiments, extract LTL directly
        return extract_ltl_formula(response_text)

# For backward compatibility - default to the standard LTL extraction
# unless the experiment type is explicitly "python"
def get_appropriate_extractor(experiment_type):
    # treat python_no_ap same as python
    if experiment_type in ("python", "python_no_ap"):
        def python_extractor(response_text):
            return extract_ltl_formula_by_type(response_text, "python")
        return python_extractor
    else:
        def standard_extractor(response_text):
            return extract_ltl_formula_by_type(response_text, "standard")
        return standard_extractor
    
def extract_ap_from_response(response_text):
    """
    Extract ATOMIC_PROPOSITIONS block from two-part no-AP response.
    Handles format:  var : "description"
    Returns string:  'description: var, description: var'
    """
    if not response_text or str(response_text).strip() in ("nan", "Error", ""):
        return ""
    
    text = str(response_text)
    
    # isolate everything before formulaToFind
    ap_section = re.split(r'formulaToFind', text, maxsplit=1)[0]
    
    parts = []
    for line in re.split(r'[\n;]', ap_section):
        line = line.strip().strip('*').strip('#')
        if not line or ':' not in line:
            continue
        if any(line.startswith(x) for x in ('```', '##', '//', 'PART', 'Text', 'Your')):
            continue
        left, right = line.split(':', 1)
        left  = left.strip().strip('"').strip("'")
        right = right.strip().strip('"').strip("'").lower()
        # var : "description" format — left is the variable
        if re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', left):
            parts.append(f"{right}: {left}")  # flip to desc: var
    
    return ", ".join(parts)

def extract_python_ast_no_ap(response_text):
    """
    Extract formulaToFind from the two-part no-AP response.
    Same as extract_python_ast but works on the full two-part response.
    """
    return extract_python_ast(response_text)