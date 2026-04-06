def generate_base_prompt(ltl_formula, trace):
    """
    Generate the base prompt for LTL trace characterization with semantics and evaluation instructions.
    
    Args:
        ltl_formula (str): The LTL formula to evaluate
        trace (str): The trace to characterize
    
    Returns:
        str: Complete base prompt with LTL semantics and trace characterization instructions
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

Your task is to determine whether the given trace SATISFIES (positive trace) or FALSIFIES (negative trace) the given LTL formula when evaluated at position 0.

LTL Formula: {formula}
Trace: {trace}

Evaluate the formula at position 0 of the trace using the LTL semantics provided above.

Answer with either:
POSITIVE (if the trace satisfies the formula)
NEGATIVE (if the trace falsifies the formula)

Provide only the answer. No explanation is needed."""

    return base_prompt.format(formula=ltl_formula, trace=trace)



def handle_self_refinement(base_prompt, initial_response):
    """
    Handle self-refinement for trace characterization by asking the model to verify its evaluation.
    
    Args:
        base_prompt (str): The original base prompt
        initial_response (str): The initial response (POSITIVE or NEGATIVE)
        ltl_formula (str): The LTL formula being evaluated
        trace (str): The trace being characterized
    
    Returns:
        str: Self-refinement prompt for trace characterization verification
    """
    refinement_prompt = f"""{base_prompt}

Your initial answer was: {initial_response}

Now, please carefully verify your answer by step-by-step evaluation:

1. Parse the trace and identify each state with its variable assignments
2. Start evaluation at position 0 of the trace
3. Break down the given formula
4. Apply the LTL semantics rules systematically:
   - For temporal operators (F, G, X, Y, U, S, O, H), check the required positions
   - For logical operators (&, |, !, ->, <->), evaluate according to their definitions
   - For propositional variables, check their truth values at the relevant positions

5. Determine if the formula evaluates to TRUE or FALSE at position 0

6. Based on the evaluation:
   - If TRUE → answer should be POSITIVE
   - If FALSE → answer should be NEGATIVE

If your initial answer was incorrect, provide the corrected answer.
If your initial answer was correct, confirm it.

Answer with either:
POSITIVE (if the trace satisfies the formula)
NEGATIVE (if the trace falsifies the formula)

Provide only the final answer."""

    return refinement_prompt

def generate_prompt(ltl_formula, trace, approach, initial_response=None):
    """
    Generate prompts for different approaches: zero-shot, zero-shot self-refine, or few-shot.
    
    Args:
        ltl_formula (str): The LTL formula to evaluate
        trace (str): The trace to characterize
        approach (str): The approach type ('zero_shot', 'zero_shot_refine', 'few_shot')
        initial_response (str, optional): Initial response for self-refinement
    
    Returns:
        str: Generated prompt based on the specified approach
    """
    
    if approach == "zero_shot":
        return generate_base_prompt(ltl_formula, trace)
    
    elif approach == "zero_shot_self_refine":
        if initial_response is None:
            raise ValueError("Initial response is required for zero-shot self-refinement")
        return handle_self_refinement(
    generate_base_prompt(ltl_formula, trace), 
    initial_response
)

    elif approach == "few_shot":
        # Few-shot examples for trace characterization
        examples = """Here are some examples:

Example 1:
LTL Formula: F(x1)
Trace: [x1 = FALSE];[x1 = FALSE];[x1 = TRUE];[x1 = TRUE]
Answer: POSITIVE

Example 2:
LTL Formula: F(x1)
Trace: [x1 = FALSE];[x1 = FALSE];[x1 = FALSE];[x1 = FALSE]
Answer: NEGATIVE

Example 3:
LTL Formula: G(x1 -> x2)
Trace: [x1 = FALSE, x2 = FALSE];[x1 = FALSE, x2 = TRUE];[x1 = TRUE, x2 = TRUE];[x1 = TRUE, x2 = TRUE]
Answer: POSITIVE

Example 4:
LTL Formula: G(x1 -> x2)
Trace: [x1 = TRUE, x2 = FALSE];[x1 = FALSE, x2 = TRUE];[x1 = FALSE, x2 = TRUE];[x1 = FALSE, x2 = TRUE]
Answer: NEGATIVE

Example 5:
LTL Formula: X(x1)
Trace: [x1 = FALSE];[x1 = TRUE];[x1 = FALSE];[x1 = FALSE]
Answer: POSITIVE

Example 6:
LTL Formula: X(x1)
Trace: [x1 = TRUE];[x1 = FALSE];[x1 = TRUE];[x1 = TRUE]
Answer: NEGATIVE

Example 7:
LTL Formula: x1 U x2
Trace: [x1 = TRUE, x2 = FALSE];[x1 = TRUE, x2 = FALSE];[x1 = FALSE, x2 = TRUE];[x1 = FALSE, x2 = FALSE]
Answer: POSITIVE

Example 8:
LTL Formula: x1 U x2
Trace: [x1 = TRUE, x2 = FALSE];[x1 = FALSE, x2 = FALSE];[x1 = FALSE, x2 = FALSE];[x1 = FALSE, x2 = FALSE]
Answer: NEGATIVE

Now solve this:
"""
        base_prompt = generate_base_prompt(ltl_formula, trace)
        # Insert examples before the task
        prompt_parts = base_prompt.split("Your task is to determine")
        few_shot_prompt = prompt_parts[0] + examples + "Your task is to determine" + prompt_parts[1]
        return few_shot_prompt
    
    else:
        raise ValueError(f"Unknown approach: {approach}")
