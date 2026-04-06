def generate_base_prompt(formula):
    """Generate the base prompt for any approach."""
    return (
        "You are an assistant that understands Linear Temporal Logic (LTL). "
        "Your task is to generate a **positive** and **negative** trace for the given formula. "
        "Each trace must follow this format: [a=true,b=false,c=true];[a=false,b=true,c=true];... "
        "with '...' indicating continuous or infinite. Do not include any explanation.\n\n"
        "Use these LTL Symbols:\n"
        "- AND: &\n"
        "- OR: |\n"
        "- NOT: !\n"
        "- IMPLIES: ->\n"
        "- BIIMPLICATION: <->\n"
        "- NEXT: X\n"
        "- EVENTUALLY: F\n"
        "- ALWAYS: G\n"
        "- UNTIL: U\n\n"
        f"LTL Formula: {formula}\n\n"
        "Generate only the traces below:\n"
    )

def handle_self_refinement(base_prompt, initial_response):
    """Handle the self-refinement process separately."""
    return (
        base_prompt +
        f"Your initial response was:\n{initial_response}\n\n"
        "Now refine your answer and generate **only the positive and negative trace**, without any explanation."
    )


def generate_prompt(formula, approach, initial_response=None):
    """Main function to generate prompts based on the approach."""
    base_prompt = generate_base_prompt(formula)
    
    if approach == "zero_shot":
        return base_prompt + "Generate the positive and negative traces only, without explanation."
    
    elif approach == "zero_shot_self_refine":
        if initial_response is None:
            # First run: generate initial answer
            return base_prompt + "Generate the initial positive and negative traces only, without explanation."
        else:
            # Refinement step: reuse the base prompt and add refinement instructions
            return handle_self_refinement(base_prompt, initial_response)
    
    elif approach == "few_shot":
        # Few-shot examples with clear instructions to avoid explanations
        few_shot_examples = (
            "Below are examples of positive and negative traces for different LTL formulas. "
            "Generate only the positive and negative traces for the given formula, "
            "strictly in the format [a=true,b=false];[a=false,b=true];..., without any explanation or additional text.\n\n"
            
            "Example 1:\n"
            "LTL Formula: G(a -> Fb)\n"
            "Positive trace: [a=false,b=false];[a=true,b=false];[a=false,b=true];[a=false,b=false];...\n"
            "Negative trace: [a=true,b=false];[a=true,b=false];[a=true,b=false];...\n\n"
            
            "Example 2:\n"
            "LTL Formula: F(a & b)\n"
            "Positive trace: [a=false,b=true];[a=true,b=false];[a=true,b=true];[a=false,b=false];...\n"
            "Negative trace: [a=false,b=true];[a=true,b=false];[a=false,b=false];...\n\n"
            
            "Now, generate the positive and negative traces for the following formula:\n"
        )
        return few_shot_examples + base_prompt
    
    else:
        raise ValueError(f"Unknown approach: {approach}")

# def create_prompt(approach, formula):
#   base_prompt = ( "You are an assistant that understands Linear Temporal Logic (LTL). Your task is, given an LTL formula, to generate a positive and negative trace for the formula in this format [a=true,b=false,c=true];[a=false,b=true,c=true];... with '...' indicating continuous or infinite."
#   "Use these LTL Symbols:\n"
#           "- AND: &\n"
#           "- OR: |\n"
#           "- NOT: !\n"
#           "- IMPLIES: ->\n"
#           "- BIIMPLICATION: <->\n"
#           "- NEXT: X\n"
#           "- EVENTUALLY: F\n"
#           "- ALWAYS: G\n"
#           "- UNTIL: U\n\n"
#           f"LTL formula: {formula}\n\n"
#       )


#   if approach == "zero_shot":
#       return base_prompt + "Given the LTL formula generate a Positive and Negative trace. Generate the answer only without any thinking or explanation."
# #   elif approach == "zero_shot_CoT":
# #       return base_prompt + "\n\nLet's approach this step-by-step."
#   elif approach == "zero_shot_self_refine":
#       return base_prompt + "\n\n Generate the initial answer only without any thinking or explanation, then refine your answer"
#   elif approach == "few_shot":
#       return base_prompt + ("Here are a few examples to guide you:\n\n"
#       "Example 1:"
#       "LTL Formula: G(a -> Fb)"
#       "Positive trace: [a=false,b=false];[a=true,b=false];[a=false,b=true];[a=false,b=false];..."
#       "Negative trace: [a=true,b=false];[a=true,b=false];[a=true,b=false];..."

#       "Example 2:"
#       "LTL Formula: F(a & b)"
#       "Positive trace: [a=false,b=true];[a=true,b=false];[a=true,b=true];[a=false,b=false];..."
#       "Negative trace: [a=false,b=true];[a=true,b=false];[a=false,b=false];..."

#       "Now, generate traces for the following:")

#   else:
#       raise ValueError(f"Unknown approach: {approach}")