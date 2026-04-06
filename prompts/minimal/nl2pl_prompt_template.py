def generate_base_prompt(nl_statement):
    """Generate the base prompt for any approach."""
    return (
        # "You are an assistant who understands Propositional Logic (PL). "
        # "Your task is to identify the atomic phrases in the given Natural Language (NL) statement. "
        # "You must then tell the corresponding atomic variable that will be used in the LTL for each of these phrases. "
        # "Give your answer as this format \"phrase\": atomic propositional variable.\n\n"
        # f"NL statement: {nl_statement}\n"

        "You are an assistant who understands Propositional Logic (PL)."
        "Your task is to identify the atomic phrases in the given Natural Language (NL) statement. "
        "For each phrase, provide the corresponding atomic propositional variable to be used in the LTL. "
        "If there are multiple atomic phrases, separate each phrase and variable pair with a semicolon (;). "
        "Provide your answer in the following format:"
        "\"phrase\": atomic propositional variable; \"phrase\": atomic propositional variable; ..."

        f"NL statement: {nl_statement}\n"

    )

def handle_self_refinement(base_prompt, initial_response):
    """Handle the self-refinement process separately."""
    return (
        base_prompt +
        f"Your initial response was: {initial_response}\n"
        "Now, refine your answer.\n\n"
        "Give your answer as this format \"phrase\": atomic propositional variable.\n\n"
        "If there are multiple atomic phrases, separate each phrase and variable pair with a semicolon (;). "


    )

def generate_prompt(nl_statement, approach, initial_response=None):
    """Main function to generate prompts based on the approach."""
    base_prompt = generate_base_prompt(nl_statement)
    
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
            "If the sensor detects motion, then the alarm will sound.\n"
            "\"sensor detects motion\": p; \"alarm will sound\": q\n\n"
            "The light turns green when the button is pressed.\n"
            "\"light turns green\": r; \"button is pressed\": s\n\n"
            "Now, identify the atomic propositions for the given NL statement:"
        )
        return base_prompt + few_shot_examples
    
    else:
        raise ValueError(f"Unknown approach: {approach}")



# def generate_prompt(nl_statement, approach):
#     base_prompt = (
#         "You are an assistant who understands Propositional Logic (PL). "
#         "Your task is to identify the atomic phrases in the given Natural Language (NL) statement. "
#         "You must then tell the corresponding atomic variable that will be used in the LTL for each of these phrases. "
#         "Give your answer as this format \"phrase\": atomic propositional variable.\n\n"
#         f"NL statement: {nl_statement}\n"
#     )
    
#     if approach == "zero_shot":
#         return base_prompt + " Generate the answer only without any thinking or explanation."
#     # elif approach == "zero_shot_CoT":
#     #     return base_prompt + "\nLet's approach this step-by-step:"
#     elif approach == "zero_shot_self_refine":
#         return base_prompt + "\n Generate the initial answer only without any thinking or explanation, then refine your answer"
#     elif approach == "few_shot":
#         return base_prompt + "\nHere are a few examples:\n" \
#                "NL: If the sensor detects motion, then the alarm will sound.\n" \
#                "Atomic propositions: \"sensor detects motion\": p, \"alarm will sound\": q\n\n" \
#                "NL: The light turns green when the button is pressed.\n" \
#                "Atomic propositions: \"light turns green\": r, \"button is pressed\": s\n\n" \
#                "Now, identify the atomic propositions for the given NL statement:"
#     else:
#         raise ValueError(f"Unknown approach: {approach}")
