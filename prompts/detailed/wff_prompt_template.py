def generate_base_prompt(ltl_formula):
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

Here is a BNF grammar for the syntax of a propositional linear temporal logic formula.

<formula> ::= <ap> | "true" | "false" | <formula> "&&" <formula> | <formula> "||" <formula> |
"!" <formula> | "(" <formula> ")" | <formula> "->" <formula> | <formula> "<-->" <formula> |
<formula> "S" <formula> | <formula> "U" <formula> |
"O" <formula> | "F" <formula> | "H" <formula> | "G" <formula> |
"X" <formula> | "Y" <formula>

<ap> ::= It is the set of propositional logic variables which should start with
any letters (small or capital) followed by an alphanumeric string.
Simply put, <ap> ::= [a-zA-Z][a-zA-Z0-9]* in regular expression.

Note that <formula> and <ap> are non-terminals in the BNF grammar whereas anything
inside double quotation marks ("") is a terminal.

"true" and "false" represent logical true and false, respectively.

The negation unary operator ! has the highest precedence. (right associative)
The yesterday and next operators, Y and X, have the next highest precedence (right associative)
Historically, globally, once, eventually, H, G, O, F, have the next highest precedence (right associative)
The since and until, S and U, have the next highest precedence (right associative)
The conjunction binary operator && has the next highest precedence. (left associative)
The disjunction binary operator || has the next highest precedence. (left associative)
The implication binary operator -> has the next highest precedence. (right associative)
The equivalence binary operator <--> has the lowest precedence. (right associative)

A well-formed propositional linear temporal logic formula is the one that can be constructed using
the above grammar.

You will now decide whether the following given string is a well-formed propositional linear temporal logic formula.

{formula}

I just need a Yes or No answer. No explanation is needed."""

    return base_prompt.format(formula=ltl_formula)

def handle_self_refinement(base_prompt, initial_response):
    refinement_prompt = f"""{base_prompt}

Your initial answer was: {initial_response}

Now, please carefully reconsider your answer. Think step by step:
1. Check if all parentheses are properly balanced
2. Verify that all operators have the correct number of operands
3. Ensure all propositional variables follow the naming convention [a-zA-Z][a-zA-Z0-9]*
4. Check that temporal operators are used correctly
5. Verify the overall syntactic structure matches the BNF grammar

After this careful analysis, what is your final answer?

I just need a Yes or No answer. No explanation is needed."""

    return refinement_prompt

def generate_prompt(ltl_formula, approach, initial_response=None):
    if approach == "zero_shot":
        return generate_base_prompt(ltl_formula)
    
    elif approach == "zero_shot_self_refine":
        if initial_response is None:
            raise ValueError("Initial response is required for zero-shot self-refinement")
        return handle_self_refinement(generate_base_prompt(ltl_formula), initial_response)
    
    elif approach == "few_shot":
        # Few-shot examples
        examples = """Here are some examples:

Example 1:
Formula: (a && b) -> F(c)
LLM Prediction: Yes

Example 2:
Formula: G(p -> X(q))
LLM Prediction: Yes

Example 3:
Formula: (p U q) && !G(r)
LLM Prediction: Yes

Example 4:
Formula: ((S) |)
LLM Prediction: No

Example 5:
Formula: a && (
LLM Prediction: No

Example 6:
Formula: !true -> false
LLM Prediction: Yes

Example 7:
Formula: X(Y(p)) <-> q
LLM Prediction: Yes

Example 8:
Formula: p S
LLM Prediction: No

Now solve this:
"""
        base_prompt = generate_base_prompt(ltl_formula)
        prompt_parts = base_prompt.split("You will now decide")
        few_shot_prompt = prompt_parts[0] + examples + "You will now decide" + prompt_parts[1]
        return few_shot_prompt
    
    else:
        raise ValueError(f"Unknown approach: {approach}")