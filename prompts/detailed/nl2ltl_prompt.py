def generate_base_prompt(nl_statement):
    """Generate the base prompt for LTL conversion."""
    return f"""You are a teacher who is proficient in propositional linear temporal logic.
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

Here is a BNF grammar for the syntax of a propositional linear temporal logic formulas.

<formula> ::= <ap> | "true" | "false" | <formula> "&&" <formula> | <formula> "||" <formula> |
"!" <formula> | "(" <formula> ")" | <formula> "->" <formula> | <formula> "<-->" <formula> |
<formula> "S" <formula> | <formula> "U" <formula> |
"O" <formula> | "F" <formula> | "H" <formula> | "G" <formula> |
"X" <formula> | "Y" <formula>

<ap> ::= It is the set of propositional logic formula which should start with
any letters (small or capital) followed by an alphanumeric string.
Simply put, <ap> ::= [a-zA-Z][a-zA-Z0-9]* in regular expression.

Note that <formula> and <ap> are non-terminals in the BNF grammar whereas anything
inside double quotation mark ("") is a terminal.

"true" and "false" represent logical true and false, respectively.

The negation unary operator ! has the highest precedence. (right associative)
The yesterday and next operators, Y and X, have the next highest precedence (right associative)
The historically, globally, once, eventually, H, G, O, F, have the next highest precedence (right associative)
The since and until, S and U, have the next highest precedence (right associative)
The conjunction binary operator && has the next highest precedence. (left associative)
The disjunction binary operator || has the next highest precedence. (left associative)
The implication binary operator -> has the next highest precedence. (right associative)
The equivalence binary operator <--> has the lowest precedence. (right associative)

A well-formed propositional linear temporal logic formula is the one that can be constructed using
the above grammar.

The semantics of propositional logic formula is defined
with respect to a linear trace and a position in the trace.
Each element of a trace is a substitution (a mapping from propositional
variables to either true or false) is as follows.
In the following semantics, a is a propositional variable whereas
p and q are propositional linear temporal logic formulas.

Given a trace σ, a position i in σ where the temporal
logic formula is being evaluated, we can have the following semantics.

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
(15) In σ and i, p U q is true if and only if there exists a position j >= i such that q is true in σ at position j, and p is true in σ at all positions k where i <= k < j
(16) In σ and i, p S q is true if and only if there exists a position j <= i such that q is true in σ at position j, and p is true in σ at all positions k where j < k <= i

You are now trying to convert a natural language English text into a propositional linear temporal logic formula.

You will follow the principle of maximal revelation during this task. According to this
principle, you will try to reveal as much of the logical structure of the
underlying text as possible when converting it into a propositional linear temporal logic formula.

Now for the following text, please convert it to a propositional linear temporal logic formula.
In addition to giving the original formula, also provide the mapping of sentence
fragments to the selected propositional variable.

{nl_statement}

When generating the answer for the above text, stop providing additional explanations. 
Your output should be formatted in the following way:

<formula>

<propositional variable name used in the formula> => "mapped english text" """


def handle_self_refinement(base_prompt, sentence, initial_response):
    """Handle the self-refinement process for LTL conversion."""
    return f"""{base_prompt}

You previously converted the following sentence to propositional linear temporal logic:

Original sentence: {sentence}

Your previous response was:
{initial_response}

Please review your previous response and refine it if needed. Consider:
1. Does the formula correctly capture the logical and temporal structure?
2. Are the propositional variables appropriately defined?
3. Does it follow the principle of maximal revelation?
4. Is the syntax correct according to the BNF grammar?
5. Are the temporal operators (X, F, G, U, Y, O, H, S) used correctly?
6. Does the formula properly represent the temporal relationships in the natural language?

Provide your refined conversion below:

<formula>

<propositional variable name used in the formula> => "mapped english text" """


def generate_prompt(nl_statement, approach, initial_response=None):
    """Main function to generate LTL prompts based on the approach."""
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
Here are a few examples:

At some time in the future Robin will like to dance and sing.
F(d && s) where d is "Robin will like to dance" and s is "Robin will like to sing".

John and Janice have danced before.
d where d is "John and Janice have danced before".

We did not say O(jd && jnd) where (jd is "John has danced" and jnd is "Janice has danced")
because it fails to capture that John and Janice were dancing together.

Omar did not eat the cake.
!e where e is "Omar ate the cake".

Alice will keep working until she finishes the project.
w U f where w is "Alice is working" and f is "Alice finishes the project".

The system has been running since the last reboot.
r S b where r is "the system is running" and b is "the last reboot happened".

Next week, the meeting will be scheduled.
X m where m is "the meeting is scheduled".

The alarm has always worked properly.
H a where a is "the alarm works properly".
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


# Example usage and testing
if __name__ == "__main__":
    # Test sentence from your document
    test_sentence = "x1 is true sometime after 4 or more transitions"
    
    # Test zero-shot
    print("=== ZERO-SHOT LTL ===")
    zero_shot_prompt = generate_prompt(test_sentence, "zero_shot")
    print(zero_shot_prompt)
    print("\n" + "="*50 + "\n")
    
    # Test few-shot
    print("=== FEW-SHOT LTL ===")
    few_shot_prompt = generate_prompt(test_sentence, "few_shot")
    print(few_shot_prompt)
    print("\n" + "="*50 + "\n")
    
    # Test self-refine (simulate with fake initial response)
    print("=== ZERO-SHOT SELF-REFINE LTL ===")
    fake_initial_response = "F x1 where x1 is 'x1 is true'"
    self_refine_prompt = generate_prompt(test_sentence, "zero_shot_self_refine", fake_initial_response)
    print(self_refine_prompt)