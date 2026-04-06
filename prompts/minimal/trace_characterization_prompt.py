def generate_base_prompt(ltl_formula,trace):
    """Generate the base prompt for any approach."""
    return (
       "You are an assistant that understands Linear Temporal Logic (LTL)."
        "Your task is to evaluate an LTL formula against a given trace and determine if the trace is a Positive or Negative trace for the given LTL formula.\n"
        "LTL Formula: A string representing the LTL formula"
        "Trace: A sequence of states in the format [a=true,b=false,c=true];[a=false,b=true,c=true];..."
        "The ';...' indicates that the trace continues infinitely or for a long time.\n"
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
        f"LTL formula: {ltl_formula}\n"
        f"Trace: {trace}\n\n"
        "Given an LTL formula and a trace, specify whether the trace is acceptable with no explanation for the given formula. Indicate 'Positive' for acceptable 'Negative' for not acceptable"
    )

def handle_self_refinement(base_prompt, initial_response):
    """Handle the self-refinement process separately."""
    return (
        base_prompt +
        f"Your initial response was: {initial_response}\n"
        "Now, refine your answer. Indicate 'Positive' for acceptable 'Negative' for not acceptable with no explanation.\n\n"
    )

def generate_prompt(ltl_formula,trace, approach, initial_response=None):
    """Main function to generate prompts based on the approach."""
    base_prompt = generate_base_prompt(ltl_formula, trace)
    
    if approach == "zero_shot":
        return base_prompt + "Generate the answer only, without any thinking or explanation."
    
    elif approach == "zero_shot_self_refine":
        if initial_response is None:
            # First run: generate initial answer
            return base_prompt + "Generate the initial answer only, without any thinking or explanation."
        else:
            # Refinement step: reuse the base prompt and add the refinement
            return handle_self_refinement(base_prompt, initial_response)
    
    elif approach == "few_shot":
        # Few-shot examples
        few_shot_examples = (
            "\nHere are a few examples:\n"
           "Example 1:"
            "LTL Formula: G(a -> (b U c))\n"
            "Trace: [a=true, b=false, c=true]; [a=true, b=true, c=false]\n"
            "Type: Positive\n"
            "Example 2:\n"
            "LTL Formula: G(a -> Fb)\n"
            "Trace: [a=true,b=false];[a=false,b=false];[a=true,b=true];[a=false,b=false];...\n"
            "Type: Positive\n"
            "Example 3:\n"
            "LTL Formula: F(a & b)\n"
            "Trace: [a=true, b=false]; [a=false, b=true]; [a=true, b=true]\n"
            "Type: Negative\n. Now given an LTL formula and a trace, specify whether the trace is acceptable for the given formula:"
        )
        return base_prompt + few_shot_examples
    
    else:
        raise ValueError(f"Unknown approach: {approach}")



# def generate_trace_prompt(approach, ltl_formula, trace):
#     base_prompt = (
#         "You are an assistant that understands Linear Temporal Logic (LTL)."
#         "Your task is to evaluate an LTL formula against a given trace and determine if the trace is a Positive or Negative trace for the given LTL formula.\n"
#         "LTL Formula: A string representing the LTL formula"
#         "Trace: A sequence of states in the format [a=true,b=false,c=true];[a=false,b=true,c=true];..."
#         "The ';...' indicates that the trace continues infinitely or for a long time.\n"
#         "Use these LTL Symbols:\n"
#         "- AND: &\n"
#         "- OR: |\n"
#         "- NOT: !\n"
#         "- IMPLIES: ->\n"
#         "- BIIMPLICATION: <->\n"
#         "- NEXT: X\n"
#         "- EVENTUALLY: F\n"
#         "- ALWAYS: G\n"
#         "- UNTIL: U\n\n"
#         f"LTL formula: {ltl_formula}\n"
#         f"Trace: {trace}\n\n"
#     )
#     # Zero-shot
#     if approach == "zero_shot":
#         return base_prompt + "Given the LTL formula and the trace, classify whether the trace is a Positive or Negative. Generate the answer only without any thinking or explanation."
#     # Zero-shot Chain of Thought (CoT)
#     # elif approach == "zero_shot_CoT":
#     #     return base_prompt + "Think step-by-step and classify whether he trace is a Positive or Negative."
#     # Zero-shot Self-refinement
#     elif approach == "zero_shot_self_refine":
#         return base_prompt + " Generate the initial answer only without any thinking or explanation, then refine your answer"
#     # Few-shot example (with hardcoded few-shot examples)
#     elif approach == "few_shot":
#         return base_prompt + ("Here are a few examples to guide you:\n\n"
#             "Example 1:\n"
#             "LTL Formula: G(a -> (b U c))\n"
#             "Trace: [a=true, b=false, c=true]; [a=true, b=true, c=false]\n"
#             "Type: Positive\n"
#             "Example 2:\n"
#             "LTL Formula: G(a -> Fb)\n"
#             "Trace: [a=true,b=false];[a=false,b=false];[a=true,b=true];[a=false,b=false];...\n"
#             "Type: Positive\n"
#             "Example 3:\n"
#             "LTL Formula: F(a & b)\n"
#             "Trace: [a=true, b=false]; [a=false, b=true]; [a=true, b=true]\n"
#             "Type: Negative\n. Now given an LTL formula and a trace, specify whether the trace is acceptable for the given formula:")
#     else:
#         raise ValueError(f"Unknown approach: {approach}")

