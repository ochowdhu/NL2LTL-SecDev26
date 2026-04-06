def generate_base_prompt(ltl_formula):
    """Generate the base prompt for any approach."""
    return (
       "You are an assistant who understands Linear Temporal Logic (LTL). "
        "Your task is to specify whether a given LTL formula is a well-formed formula or not. "
        "Indicate 'Yes' if well-formed and 'No' if otherwise.\n\n"
        f"LTL Formula: {ltl_formula}\n"
    )

def handle_self_refinement(base_prompt, initial_response):
    """Handle the self-refinement process separately."""
    return (
        base_prompt +
        f"Your initial response was: {initial_response}\n"
        "Now, refine your answer.\n\n"
        "Indicate 'Yes' if well-formed and 'No' if otherwise.\n"

    )

def generate_prompt(ltl_formula, approach, initial_response=None):
    """Main function to generate prompts based on the approach."""
    base_prompt = generate_base_prompt(ltl_formula)
    
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
            "LTL Formula: G(a -> Fb)\n"
            "Response: Yes\n\n"
            "LTL Formula: a & (Fb\n"
            "Response: No\n\n"
            "LTL Formula: G(hjaksldoew -> F(kjdkfperb))\n"
            "Response: Yes\n\n"
            "LTL Formula: aerewevewq & (F(bpoqowjknd)\n"
            "Response: No\n\n"
            "Now, specify whether the given LTL formula is well-formed:"
        )
        return base_prompt + few_shot_examples
    
    else:
        raise ValueError(f"Unknown approach: {approach}")
