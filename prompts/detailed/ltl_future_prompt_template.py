def generate_base_prompt(natural_language, atomic_propositions):
    """Generate the base system prompt for LTL conversion task"""
    return f"""You are a teacher who is proficient in propositional linear temporal logic (LTL).

In propositional linear temporal logic, you have three elements:
- propositional variables;
- logical connectives/operators;
- linear temporal connectives/operators.

Logical connectives/operators in propositional linear temporal logic include:
logical AND or conjunction (represented as &),
logical OR or disjunction (represented as |),
logical Not or negation (represented as !),
logical implication or entailment (represented as ->),
logical equivalence or bi-implication (represented as <->).

Linear temporal logic connectives/operators in propositional linear temporal logic include:
Next or tomorrow (represented as X),
Eventually or future (represented as F),
Globally or henceforth (represented as G),
Until (represented as U)
Yesterday or last (represented as Y),
Once (represented as O),
Historically (represented as H),
Since (represented as S)


Here is a BNF grammar for the syntax of propositional linear temporal logic formulas.

<formula> ::= <ap> | <TRUE> | <FALSE> | <formula> "&" <formula> | <formula> "|" <formula> |
"!" <formula> | "(" <formula> ")" | <formula> "->" <formula> | <formula> "<->" <formula> 
| <formula> "U" <formula> | "F" <formula> | "G" <formula> | "X" <formula> |
<formula> "S" <formula> | "O" <formula> | "H" <formula> | "Y" <formula>

<TRUE> ::= "true" | "True" | "TRUE" 
<FALSE> ::= "false" | "False" | "FALSE"

<ap> ::= It is the set of propositional logic variables which should start with any letters (small or capital) followed by an alphanumeric string.
Simply put, <ap> ::= [a-zA-Z][a-zA-Z0-9]* in regular expression.

The semantics of a propositional linear temporal logic formula are defined with respect to a linear trace σ and a position i in the trace. The position i is a non-negative number (i.e., 0 or any positive whole number).

Each element of a trace is a substitution (a mapping from propositional variables to either true or false).

In short, a trace σ is a sequence of states, where each state assigns truth values to propositional variables.

Given a trace σ, a position i in σ where the temporal logic formula is being evaluated, we can have the following semantics:

(1) σ and i always satisfy true
(2) σ and i falsify false
(3) In σ and i, a proposition a is true if and only if the current substitution σ[i] satisfies a
(4) In σ and i, p & q is true if and only if both p and q are true in σ and i
(5) In σ and i, p | q is true if and only if one of p or q are true in σ and i
(6) In σ and i, !p is true if and only if p is false in σ and i
(7) In σ and i, p -> q is true if and only if when p is true then q is true in σ and i
(8) In σ and i, p <-> q is true if and only if both p and q are both true or p and q are both false in σ and i
(9) In σ and i, X p is true if and only if p is true in σ at position i + 1
(10) In σ and i, Y p is true if and only if i > 0 and p is true in σ at position i - 1
(11) In σ and i, O p is true if and only if p is true in σ at position i or in σ at any position lower than i
(12) In σ and i, F p is true if and only if p is true in σ at position i or in σ at any position greater than i
(13) In σ and i, H p is true if and only if p is true in σ at position i and in σ at all positions lower than i
(14) In σ and i, G p is true if and only if p is true in σ at position i and in σ at all positions greater than i
(15) In σ and i, p S q is true if and only if q is true in σ at position i and p is true in σ at all positions from some position j ≤ i to position i

We say a trace σ satisfies a propositional LTL formula f if and only if σ satisfies f in the 0th position of σ.

You are now trying to convert a natural language English text into a propositional linear temporal logic formula.

The input for this task will have two parts: natural language English sentences followed by natural language to propositional variable mapping.

The input mapping from propositional variables to the natural language fragment having the form (variable_name -> "English sentence fragment") dictates the meaning of the propositional variable.

For this task, you can only use the propositional variable given to you as part of the task input. Do not introduce any new propositional variables other than what is given to you.

When generating the answer for the given natural language text to convert to LTL, stop providing additional explanations. Your output should only contain the formula in a single line.

Now convert the following:

Natural Language: {natural_language}

Proposition Mapping: {atomic_propositions}

When converting the natural language sentences in English to LTL, you cannot use any of the past temporal operators. The LTL formula you should output can only contain the following operators/connectives: &, |, !, ->, <->, X, F, U, G, Y, O, H, S

Very Important Syntax Rules

You must use only the following symbols in your formula:
- & for logical AND
- | for logical OR
- ! for logical NOT
- -> for implication
- <-> for bi-implication
- F, G, X, U for temporal operators

Do **not** use any of these invalid symbols:
- ∧ (instead use &)
- ∨ (instead use |)
- ¬ (instead use !)
- → (instead use ->)
- ⇔ or ↔ (instead use <->)

If any of these invalid symbols appear, the formula is incorrect.

Your output must be a **single-line formula** using only the allowed syntax above, and must strictly follow the BNF grammar provided.
Convert the natural language to LTL formula:

"""


def handle_self_refinement():
    """Generate the self-refinement prompt"""
    return """You must revise your previous LTL formula conversion to comply with the required syntax and semantics.

- ONLY use allowed logical symbols: &, |, !, ->, <->.
- DO NOT use mathematical symbols like ∧, ∨, ¬, →, ⇔, ↔.
- ONLY use temporal operators: F, G, X, U.
- Your formula must follow the provided BNF grammar.
- Do NOT restate your original formula. Always regenerate a fresh version that strictly adheres to the allowed syntax.

Your output should contain only the corrected LTL formula on a single line."""



def generate_prompt(nl_statement, atomic_propositions, approach, initial_response=None):
    """Main function to generate prompts based on the approach."""
    base_prompt = generate_base_prompt(nl_statement, atomic_propositions)
    
    if approach == "zero_shot":
        return base_prompt + "Generate the answer only (the Future-LTL formula), without any thinking or explanation."
    
    elif approach == "zero_shot_self_refine":
        if initial_response is None:
            # First run: generate initial answer
            return base_prompt + "Generate the initial answer only, without any thinking or explanation."
        else:
            # Refinement step
            refinement_prompt = handle_self_refinement()
            return f"""Your previous conversion was:
{initial_response}

{refinement_prompt}

Original Natural Language: {nl_statement}
Proposition Mapping: {atomic_propositions}

Refined LTL formula:"""
    
    elif approach == "few_shot":
        # Few-shot examples
        few_shot_examples = (
            "\nHere are a few examples:\n"
            "Natural Language: The door will eventually be closed\n"
            "Atomic Propositions: \"\"door is open\" : x1\"\n"
            "LTL Formula: F(!x1)\n\n"
            "Natural Language: The system will remain secure until shutdown\n"
            "Atomic Propositions: \"\"system is secure\" : x1 , \"system shuts down\": x2\"\n"
            "LTL Formula: x1 U x2\n\n."
            "Natural Language: The alarm will ring next\n"
            "Atomic Propositions: \"\"alarm is ringing\" : x1\"\n"
            "LTL Formula: X(x1)\n\n."

            "Now generate the Future-LTL formula only with no explanation:"
        )
        return base_prompt + few_shot_examples
    
    else:
        raise ValueError(f"Unknown approach: {approach}")
