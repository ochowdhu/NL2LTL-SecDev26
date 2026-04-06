def generate_base_prompt(natural_language,atomic_propositions):
    """Generate the base prompt for any approach."""
    return (
        "You are a Linear Temporal Logic (LTL) Parser. Your task is to convert a given Natural Language statement to an LTL formula, "
        "using the provided mapping of natural language phrases to atomic propositions.\n\n"
        "LTL Symbols:\n"
        "- AND: &\n"
        "- OR: |\n"
        "- NOT: !\n"
        "- IMPLIES: ->\n"
        "- BIIMPLICATION: <->\n"
        "- NEXT: X\n"
        "- EVENTUALLY: F\n"
        "- ALWAYS: G\n"
        "- UNTIL: U\n\n"
        f"Natural Language statement: {natural_language}\n"
        f"Atomic Propositions mapping: {atomic_propositions}\n\n"
    )

def handle_self_refinement(base_prompt, initial_response):
    """Handle the self-refinement process separately."""
    return (
        base_prompt +
        f"Your initial response was: {initial_response}\n"
        "Now, refine your answer (only the LTL formula).\n\n"
    )

def generate_prompt(nl_statement,atomic_propositions, approach, initial_response=None):
    """Main function to generate prompts based on the approach."""
    base_prompt = generate_base_prompt(nl_statement,atomic_propositions)
    
    if approach == "zero_shot":
        return base_prompt + "Generate the answer only (the LTL formula), without any thinking or explanation."
    
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
            "Natural Language: It eventually holds that if x1 is true then x2 is true thereafter\n"
            "Atomic Propositions: \"x1 : x1 , x2 : x2\"\n"
            "LTL Formula: F(x1 -> G(x2))\n\n"
            "Natural Language: Parents with high education will always have children who would also pursue education.\n"
            "Atomic Propositions: \"\"Parents with high education\" : x1 , \"children who would also pursue education\": x2\"\n"
            "LTL Formula: G(x1 -> G(x2))\n\n. Now generate the LTL formula only with no explanation:"
        )
        return base_prompt + few_shot_examples
    
    else:
        raise ValueError(f"Unknown approach: {approach}")
    
