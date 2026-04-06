def generate_base_prompt(ltl_formula):
    """
    Generate the base prompt for LTL trace generation with semantics and trace concepts.
    
    Args:
        ltl_formula (str): The LTL formula to generate traces for
    
    Returns:
        str: Complete base prompt with LTL semantics and trace generation instructions
    """
    base_prompt = """You are a teacher who is proficient in propositional linear temporal logic.

In propositional linear temporal logic, you have three elements:
- propositional variables;
- logical connectives/operators;
- linear temporal connectives/operators.

Logical connectives/operators in propositional linear temporal logic include:
logical AND or conjunction (represented as &&),
logical OR or disjunction (represented as ||),
logical Not or negation (represented as !),
logical implication or entailment (represented as ->),
logical equivalence or bi-implication (represented as <-->).

Linear temporal logic connectives/operators in propositional linear temporal logic include:
Next or tomorrow (represented as X),
Eventually or future (represented as F),
Globally or henceforth (represented as G),
Until (represented as U)
Yesterday or last (represented as Y),
Once (represented as O),
Historically (represented as H),
Since (represented as S)

The semantics of propositional logic formula is defined with respect to a linear trace and a position in the trace.
Each element of a trace is a substitution (a mapping from propositional variables to either true or false).

Given a trace σ, a position i in σ where the temporal logic formula is being evaluated, we can have the following semantics:

(1) σ and i always satisfies true
(2) σ and i always falsifies false
(3) In σ and i, a is true if and only if the current substitution σ[i] satisfies a
(4) In σ and i, p && q is true if and only if both p and q are true in σ and i
(5) In σ and i, p || q is true if and only if one of p or q are true in σ and i
(6) In σ and i, !p is true if and only if p is false in σ and i
(7) In σ and i, p -> q is true if and only if when p is true then q is true in σ and i
(8) In σ and i, p <--> q is true if and only if both p and q are both true or p and q are both false in σ and i
(9) In σ and i, X p is true if and only if p is true in σ at position i + 1
(10) In σ and i, Y p is true if and only if i > 0 and p is true in σ at position i - 1
(11) In σ and i, O p is true if and only if p is true in σ at position i or in σ at any position lower than i
(12) In σ and i, F p is true if and only if p is true in σ at position i or in σ at any position greater than i
(13) In σ and i, H p is true if and only if p is true in σ at position i and in σ at all positions lower than i
(14) In σ and i, G p is true if and only if p is true in σ at position i and in σ at all positions greater than i

A trace is a sequence of states, where each state assigns truth values to propositional variables.
Traces are represented as: [var1 = TRUE/FALSE, var2 = TRUE/FALSE, ...];[var1 = TRUE/FALSE, var2 = TRUE/FALSE, ...];...

For the given LTL formula: {formula}

Generate two traces:
1. A SATISFYING trace (positive trace) - a trace that makes the formula TRUE when evaluated at position 0
2. A FALSIFYING trace (negative trace) - a trace that makes the formula FALSE when evaluated at position 0

Format your answer as:
SATISFYING: [trace here]
FALSIFYING: [trace here]

DO NOT provide any additional explanations or comments.
"""

    return base_prompt.format(formula=ltl_formula)

def handle_trace_self_refinement(base_prompt, initial_response):
    """
    Handle self-refinement for trace generation by asking the model to verify its traces.
    
    Args:
        base_prompt (str): The original base prompt
        initial_response (str): The initial response with generated traces
    
    Returns:
        str: Self-refinement prompt for trace verification
    """
    refinement_prompt = f"""{base_prompt}

Your initial answer was:
{initial_response}

Now, please carefully verify your traces by checking:

1. SATISFYING TRACE verification:
   - Step through each position in the trace
   - Evaluate the formula at position 0 using the LTL semantics
   - Ensure the formula evaluates to TRUE

2. FALSIFYING TRACE verification:
   - Step through each position in the trace
   - Evaluate the formula at position 0 using the LTL semantics
   - Ensure the formula evaluates to FALSE

3. Check that:
   - All propositional variables in the formula are assigned values in each state
   - The trace length is sufficient to demonstrate the temporal behavior
   - The trace format follows: [var1 = TRUE/FALSE, var2 = TRUE/FALSE, ...];[...];...

If any trace is incorrect, provide the corrected version.
If both traces are correct, confirm them.

Format your final answer as:
SATISFYING: [corrected or confirmed trace]
FALSIFYING: [corrected or confirmed trace]
DO NOT provide any additional explanations or comments.

"""

    return refinement_prompt


def generate_prompt(ltl_formula, approach, initial_response=None):
    """
    Generate prompts for different approaches: zero-shot, zero-shot self-refine, or few-shot.
    
    Args:
        ltl_formula (str): The LTL formula to generate traces for
        approach (str): The approach type ('zero_shot', 'zero_shot_refine', 'few_shot')
        initial_response (str, optional): Initial response for self-refinement
    
    Returns:
        str: Generated prompt based on the specified approach
    """
    
    if approach == "zero_shot":
        return generate_base_prompt(ltl_formula)
    
    elif approach == "zero_shot_self_refine":
        if initial_response is None:
            raise ValueError("Initial response is required for zero-shot self-refinement")
        return handle_trace_self_refinement(generate_base_prompt(ltl_formula), initial_response)
    
    elif approach == "few_shot":
        # Few-shot examples for trace generation
        examples = """Here are some examples:

Example 1:
Formula: F(x1)
SATISFYING: [x1 = FALSE];[x1 = FALSE];[x1 = TRUE];[x1 = TRUE]
FALSIFYING: [x1 = FALSE];[x1 = FALSE];[x1 = FALSE];[x1 = FALSE]

Example 2:
Formula: G(x1 -> x2)
SATISFYING: [x1 = FALSE, x2 = FALSE];[x1 = FALSE, x2 = TRUE];[x1 = TRUE, x2 = TRUE];[x1 = TRUE, x2 = TRUE]
FALSIFYING: [x1 = TRUE, x2 = FALSE];[x1 = FALSE, x2 = TRUE];[x1 = FALSE, x2 = TRUE];[x1 = FALSE, x2 = TRUE]

Example 3:
Formula: X(x1)
SATISFYING: [x1 = FALSE];[x1 = TRUE];[x1 = FALSE];[x1 = FALSE]
FALSIFYING: [x1 = TRUE];[x1 = FALSE];[x1 = TRUE];[x1 = TRUE]

Example 4:
Formula: x1 U x2
SATISFYING: [x1 = TRUE, x2 = FALSE];[x1 = TRUE, x2 = FALSE];[x1 = FALSE, x2 = TRUE];[x1 = FALSE, x2 = FALSE]
FALSIFYING: [x1 = TRUE, x2 = FALSE];[x1 = FALSE, x2 = FALSE];[x1 = FALSE, x2 = FALSE];[x1 = FALSE, x2 = FALSE]

Example 5:
Formula: F(x1 -> G(x2))
SATISFYING: [x1 = FALSE, x2 = FALSE];[x1 = TRUE, x2 = TRUE];[x1 = FALSE, x2 = TRUE];[x1 = TRUE, x2 = TRUE]
FALSIFYING: [x1 = TRUE, x2 = TRUE];[x1 = TRUE, x2 = FALSE];[x1 = FALSE, x2 = TRUE];[x1 = FALSE, x2 = FALSE]

Now solve this:
"""
        base_prompt = generate_base_prompt(ltl_formula)
        # Insert examples before the formula
        prompt_parts = base_prompt.split("For the given LTL formula:")
        few_shot_prompt = prompt_parts[0] + examples + "For the given LTL formula:" + prompt_parts[1]
        return few_shot_prompt
    
    else:
        raise ValueError(f"Unknown approach: {approach}")

