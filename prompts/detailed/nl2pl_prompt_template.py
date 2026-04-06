def generate_base_prompt(nl_statement):
    """Generate the base prompt for any approach."""
    return f"""You are a teacher who is proficient in propositional logic.
In propositional logic, you have two elements: propositional variables and logical connectives/operators.

Logical connectives/operators in propositional logic include:
logical AND or conjunction (represented as &&),
logical OR or disjunction (represented as ||),
logical Not or negation (represented as !),
logical implication or entailment (represented as ->),
logical equivalence or bi-implication (represented as <-->).

Here is a BNF grammar for the syntax of a propositional logic formula.

<formula> ::= <ap> | "true" | "false" | <formula> "&&" <formula> | <formula> "||" <formula> |
"!" <formula> | "(" <formula> ")" | <formula> "->" <formula> | <formula> "<-->" <formula>

<ap> ::= It is the set of propositional logic formula which should start with
any letters (small or capital) followed by an alphanumeric string.
Simply put, <ap> ::= [a-zA-Z][a-zA-Z0-9]* in regular expression.

Note that <formula> and <ap> are non-terminals in the BNF grammar whereas anything
inside double quotation marks ("") is a terminal.

"true" and "false" represent logical true and false, respectively.

The negation unary operator ! has the highest precedence. (right associative)
The conjunction binary operator && has the next highest precedence. (left associative)
The disjunction binary operator || has the next highest precedence. (left associative)
The implication binary operator -> has the next highest precedence. (right associative)
The equivalence binary operator <--> has the lowest precedence. (right associative)

A well-formed propositional logic formula is the one that can be constructed using
the above grammar.

The semantics of the propositional logic formula is defined
with respect to a substitution (a mapping from propositional
variables to either true or false) is as follows.
In the following semantics, a is a propositional variable whereas
p and q are propositional logic formulas.

(1) true is always true
(2) false is always false
(3) a is true if and only if the current substitution satisfies a
(4) p && q is true if and only if both p and q are true
(5) p || q is true if and only if one of p or q are true
(6) !p is true if and only if p is false
(7) p -> q is true if and only if when p is true then q is true
(8) p <--> q is true if and only if both p and q are both true or p and q are both false

You are now trying to convert a natural language English text into a propositional logic formula.

You will follow the principle of maximal revelation during this task. According to this
principle, you will try to reveal as much of the logical structure of the
underlying text as possible when converting it into a propositional logic formula.

Now for the following text, please convert it to a propositional logic formula.
In addition to giving the original formula, also provide the mapping of sentence
fragments to the selected propositional variable.

{nl_statement}

When generating the answer for the above text, stop providing additional explanations. 
Your output should be formatted in the following way:

<formula>

<propositional variable name used in the formula> : "mapped english text" """


def handle_self_refinement(base_prompt, sentence, initial_response):
    """Handle the self-refinement process separately."""
    return f"""{base_prompt}

You previously converted the following sentence to propositional logic:

Original sentence: {sentence}

Your previous response was:
{initial_response}

Please review your previous response and refine it if needed. Consider:
1. Does the formula correctly capture the logical structure?
2. Are the propositional variables appropriately defined?
3. Does it follow the principle of maximal revelation?
4. Is the syntax correct according to the BNF grammar?

Provide your refined conversion below:

<formula>

<propositional variable name used in the formula> : "mapped english text" """


def generate_prompt(nl_statement, approach, initial_response=None):
    """Main function to generate prompts based on the approach."""
    base_prompt = generate_base_prompt(nl_statement)
    
    if approach == "zero_shot":
        return base_prompt
    
    elif approach == "zero_shot_self_refine":
        if initial_response is None:
            # First run: generate initial answer (same as zero_shot)
            return base_prompt
        else:
            # Refinement step: use the refinement prompt
            return handle_self_refinement(generate_base_prompt(nl_statement), nl_statement, initial_response)
    
    elif approach == "few_shot":
        # Add few-shot examples to the base prompt
        few_shot_examples = """
Example 1:
Natural Language: Robin likes to dance and sing.
Predicted Formula: d && s
Predicted Atomic Propositions: d : "Robin likes to dance"<br>s : "Robin likes to sing"

Example 2:
Natural Language: John and Janice are dancing.
Predicted Formula: d
Predicted Atomic Propositions: d : "John and Janice are dancing"

Example 3:
Natural Language: Omar did not eat the cake.
Predicted Formula: !e
Predicted Atomic Propositions: e : "Omar ate the cake"

Example 4:
Natural Language: We did not say jd && jnd where (jd is "John is dancing" and jnd is "Janice is dancing")
Explanation: This was not used because it fails to capture that John and Janice are dancing together.
"""
        # Insert examples before the current sentence but after the base instruction
        base = generate_base_prompt(nl_statement)
        # Find where to insert examples (before "Now for the following text...")
        insertion_point = base.find("Now for the following text")
        if insertion_point != -1:
            return base[:insertion_point] + few_shot_examples + "\n" + base[insertion_point:]
        else:
            # Fallback: just append examples before the base prompt's task
            return base.replace("Now for the following text", few_shot_examples + "\nNow for the following text")
    
    else:
        raise ValueError(f"Unknown approach: {approach}")
